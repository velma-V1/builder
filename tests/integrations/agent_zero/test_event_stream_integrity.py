"""Event-stream sequence integrity: idempotent duplicates, out-of-order rejection, gap
detection."""

from __future__ import annotations

import pytest

from factory.integrations.agent_zero.adapter import AgentZeroAdapter
from factory.integrations.agent_zero.errors import AgentZeroError, AgentZeroErrorCode
from factory.integrations.agent_zero.event_validation import validate_event_stream
from factory.integrations.agent_zero.fake_transport import (
    FakeAgentZeroTransport,
    ScriptedRun,
    event,
)
from factory.integrations.agent_zero.models import AgentZeroEventType

from .az_support import model_router, work_order

pytestmark = pytest.mark.security


def test_exact_duplicate_event_is_idempotent_noop() -> None:
    started = event("wo-1", 0, AgentZeroEventType.STARTED)
    stream = validate_event_stream((started, started))
    assert len(stream.accepted) == 1
    assert stream.duplicates_skipped == 1


def test_conflicting_duplicate_same_sequence_is_rejected() -> None:
    a = event("wo-1", 0, AgentZeroEventType.STARTED)
    b = event("wo-1", 0, AgentZeroEventType.STARTED, detail="different-content")
    with pytest.raises(AgentZeroError) as excinfo:
        validate_event_stream((a, b))
    assert excinfo.value.code is AgentZeroErrorCode.DUPLICATE_EVENT


def test_missing_sequence_gap_is_rejected() -> None:
    events = (
        event("wo-1", 0, AgentZeroEventType.STARTED),
        event("wo-1", 2, AgentZeroEventType.COMPLETED),  # sequence 1 never arrived
    )
    with pytest.raises(AgentZeroError) as excinfo:
        validate_event_stream(events)
    assert excinfo.value.code is AgentZeroErrorCode.MISSING_SEQUENCE


def test_out_of_order_event_is_rejected() -> None:
    events = (
        event("wo-1", 0, AgentZeroEventType.STARTED),
        event("wo-1", 2, AgentZeroEventType.PROGRESS),
        event("wo-1", 1, AgentZeroEventType.PROGRESS),  # arrives after seq 2 was accepted
    )
    with pytest.raises(AgentZeroError) as excinfo:
        validate_event_stream(events)
    assert excinfo.value.code is AgentZeroErrorCode.OUT_OF_ORDER_EVENT


def test_well_ordered_contiguous_stream_is_accepted_in_full() -> None:
    events = tuple(event("wo-1", i, AgentZeroEventType.PROGRESS) for i in range(5))
    stream = validate_event_stream(events)
    assert len(stream.accepted) == 5
    assert stream.duplicates_skipped == 0


def test_transport_delivering_duplicate_events_is_handled_end_to_end_by_the_adapter() -> None:
    started = event("wo-1", 0, AgentZeroEventType.STARTED)
    completed = event("wo-1", 1, AgentZeroEventType.COMPLETED)
    # The fake transport replays the scripted tuple verbatim, including the duplicate.
    transport = FakeAgentZeroTransport(
        (ScriptedRun("run-1", events=(started, started, completed)),)
    )
    adapter = AgentZeroAdapter(transport=transport, model_router=model_router(), clock=lambda: 0)
    order = work_order(work_order_id="wo-1")
    run_id = adapter.submit(order)
    result = adapter.collect_result(run_id, order)
    # Idempotent duplicate must not corrupt the result — this is a legitimate, if wasteful, retry.
    assert not result.malformed
