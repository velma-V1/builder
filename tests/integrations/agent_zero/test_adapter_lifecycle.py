"""Adapter execution lifecycle: success, failure, timeout, cancellation, crash recovery, and
module-failure isolation (one bad run never corrupts the adapter for the next)."""

from __future__ import annotations

import pytest
from az_support import model_router, work_order

from factory.integrations.agent_zero.adapter import AgentZeroAdapter
from factory.integrations.agent_zero.errors import AgentZeroError, AgentZeroErrorCode
from factory.integrations.agent_zero.fake_transport import (
    FakeAgentZeroTransport,
    ScriptedRun,
    event,
    full_failure_stream,
    full_success_stream,
)
from factory.integrations.agent_zero.models import AgentZeroEventType, WorkerOutcome
from factory.integrations.agent_zero.transport import TransportFailure, TransportTimeout

pytestmark = pytest.mark.security


def _adapter(transport: FakeAgentZeroTransport) -> AgentZeroAdapter:
    return AgentZeroAdapter(transport=transport, model_router=model_router(), clock=lambda: 42)


def test_success_run_produces_success_result_with_patches_and_evidence() -> None:
    transport = FakeAgentZeroTransport(
        (ScriptedRun("run-1", events=full_success_stream("wo-1")),)
    )
    adapter = _adapter(transport)
    order = work_order(work_order_id="wo-1")
    run_id = adapter.submit(order)
    result = adapter.collect_result(run_id, order)
    assert result.worker_claimed_outcome is WorkerOutcome.SUCCESS
    assert len(result.patches) == 1
    assert not result.evidence.is_empty
    assert not result.incomplete
    assert not result.malformed


def test_failure_run_produces_failure_result() -> None:
    transport = FakeAgentZeroTransport(
        (ScriptedRun("run-1", events=full_failure_stream("wo-1")),)
    )
    adapter = _adapter(transport)
    order = work_order(work_order_id="wo-1")
    run_id = adapter.submit(order)
    result = adapter.collect_result(run_id, order)
    assert result.worker_claimed_outcome is WorkerOutcome.FAILURE
    assert result.reason == "could not apply patch"


def test_timeout_during_submit_is_denied_not_silently_swallowed() -> None:
    transport = FakeAgentZeroTransport(
        (ScriptedRun("run-1", submit_raises=TransportTimeout("no response")),)
    )
    adapter = _adapter(transport)
    with pytest.raises(AgentZeroError) as excinfo:
        adapter.submit(work_order(work_order_id="wo-1"))
    assert excinfo.value.code is AgentZeroErrorCode.TIMED_OUT


def test_timeout_during_poll_yields_incomplete_crashed_result() -> None:
    transport = FakeAgentZeroTransport(
        (ScriptedRun("run-1", poll_raises=TransportTimeout("stalled")),)
    )
    adapter = _adapter(transport)
    order = work_order(work_order_id="wo-1")
    run_id = adapter.submit(order)
    result = adapter.collect_result(run_id, order)
    assert result.worker_claimed_outcome is WorkerOutcome.CRASHED
    assert result.incomplete


def test_cancellation_asks_the_transport_and_is_recorded() -> None:
    transport = FakeAgentZeroTransport((ScriptedRun("run-1", cancel_result=True),))
    adapter = _adapter(transport)
    assert adapter.cancel("run-1") is True
    assert transport.cancelled == ["run-1"]


def test_cancelled_terminal_event_produces_cancelled_outcome() -> None:
    events = (
        event("wo-1", 0, AgentZeroEventType.STARTED),
        event("wo-1", 1, AgentZeroEventType.CANCELLED, reason="operator cancelled"),
    )
    transport = FakeAgentZeroTransport((ScriptedRun("run-1", events=events),))
    adapter = _adapter(transport)
    order = work_order(work_order_id="wo-1")
    run_id = adapter.submit(order)
    result = adapter.collect_result(run_id, order)
    assert result.worker_claimed_outcome is WorkerOutcome.CANCELLED


def test_crash_mid_stream_preserves_partial_patches_and_flags_incomplete() -> None:
    # Worker proposed a patch, then the transport failed (simulated crash) before a terminal event.
    partial = (
        event("wo-1", 0, AgentZeroEventType.STARTED),
        event("wo-1", 1, AgentZeroEventType.PATCH_PROPOSED, target_path="src/x.py",
              content_digest="b" * 64),
    )
    transport = FakeAgentZeroTransport(
        (ScriptedRun("run-1", events=partial, poll_raises=TransportFailure("worker process died"),
                     poll_raises_after_calls=1),)
    )
    adapter = _adapter(transport)
    order = work_order(work_order_id="wo-1")
    run_id = adapter.submit(order)
    result = adapter.collect_result(run_id, order)
    assert result.worker_claimed_outcome is WorkerOutcome.CRASHED
    assert result.incomplete
    assert len(result.patches) == 1
    assert "worker process died" in result.reason


def test_module_failure_isolation_one_crashed_run_does_not_break_the_next() -> None:
    transport = FakeAgentZeroTransport(
        (
            ScriptedRun("run-crash", submit_raises=TransportFailure("boom")),
            ScriptedRun("run-ok", events=full_success_stream("wo-2")),
        )
    )
    adapter = _adapter(transport)
    with pytest.raises(AgentZeroError):
        adapter.submit(work_order(work_order_id="wo-1"))

    # The same adapter instance must still serve the next, unrelated work order cleanly.
    order2 = work_order(work_order_id="wo-2")
    run_id = adapter.submit(order2)
    result = adapter.collect_result(run_id, order2)
    assert result.worker_claimed_outcome is WorkerOutcome.SUCCESS


def test_module_failure_isolation_stream_integrity_violation_yields_typed_result_not_a_crash() -> (
    None
):
    # Sequence gap (missing sequence) reaching collect_result must not raise past the adapter.
    events = (
        event("wo-1", 0, AgentZeroEventType.STARTED),
        event("wo-1", 2, AgentZeroEventType.COMPLETED),  # gap at sequence 1
    )
    transport = FakeAgentZeroTransport((ScriptedRun("run-1", events=events),))
    adapter = _adapter(transport)
    order = work_order(work_order_id="wo-1")
    run_id = adapter.submit(order)
    result = adapter.collect_result(run_id, order)
    assert result.malformed
    assert result.incomplete
    assert result.worker_claimed_outcome is WorkerOutcome.FAILURE
