"""Deterministic fixtures + fake transport for Agent Zero tests.

No process is spawned, no container is started, no network call is made. Every scenario (success,
failure, timeout, cancellation, crash mid-stream, duplicate/out-of-order/missing-sequence events,
malformed/incomplete results) is expressed as a :class:`ScriptedRun` — plain data the fake replays
verbatim, so the event-stream pathologies the validator must catch are constructed directly rather
than simulated through timing or randomness.
"""

from __future__ import annotations

from dataclasses import dataclass

from factory.integrations.agent_zero.models import (
    AgentZeroEvent,
    AgentZeroEventType,
    ResourceEnvelope,
    WorkOrder,
)
from factory.integrations.agent_zero.transport import TransportFailure, TransportTimeout


@dataclass(frozen=True, slots=True)
class ScriptedRun:
    """One scripted worker run. ``events`` is replayed verbatim — including any deliberately
    pathological ordering, gaps, or duplicates a test wants the validator to catch."""

    run_id: str
    events: tuple[AgentZeroEvent, ...] = ()
    submit_raises: Exception | None = None
    poll_raises: Exception | None = None
    #: If set (>0), ``poll_raises`` only takes effect starting at this 1-indexed poll call — lets a
    #: run behave normally for N polls then crash, for crash-recovery tests.
    poll_raises_after_calls: int = 0
    cancel_result: bool = True


class FakeAgentZeroTransport:
    """Deterministic, offline transport. Serves scripted runs; records what it saw.

    Performs NO real process/container/network I/O. Submitting more work orders than scripted runs
    fails closed (``TransportFailure``) so a test can never accidentally reach a live worker.
    """

    __slots__ = ("_next_run_index", "_poll_counts", "_run_order", "_runs", "cancelled", "submitted")

    def __init__(self, runs: tuple[ScriptedRun, ...]) -> None:
        self._runs = {r.run_id: r for r in runs}
        self._run_order = [r.run_id for r in runs]
        self._next_run_index = 0
        self._poll_counts: dict[str, int] = {}
        self.submitted: list[WorkOrder] = []
        self.cancelled: list[str] = []

    def submit(self, work_order: WorkOrder) -> str:
        self.submitted.append(work_order)
        if self._next_run_index >= len(self._run_order):
            raise TransportFailure(f"no scripted run for submission #{len(self.submitted)}")
        run_id = self._run_order[self._next_run_index]
        self._next_run_index += 1
        run = self._runs[run_id]
        if run.submit_raises is not None:
            raise run.submit_raises
        return run_id

    def poll_events(self, run_id: str, *, after_sequence: int) -> tuple[AgentZeroEvent, ...]:
        run = self._runs.get(run_id)
        if run is None:
            raise TransportFailure(f"unknown run_id {run_id!r}")
        self._poll_counts[run_id] = self._poll_counts.get(run_id, 0) + 1
        calls = self._poll_counts[run_id]
        if run.poll_raises is not None and (
            run.poll_raises_after_calls == 0 or calls > run.poll_raises_after_calls
        ):
            raise run.poll_raises
        return tuple(e for e in run.events if e.sequence > after_sequence)

    def cancel(self, run_id: str) -> bool:
        self.cancelled.append(run_id)
        run = self._runs.get(run_id)
        if run is None:
            return False
        return run.cancel_result


_RESOURCES = ResourceEnvelope(cpu_millis=1000, memory_mb=512, disk_mb=256, wall_clock_s=300)


def sample_work_order(**over: object) -> WorkOrder:
    base: dict[str, object] = dict(
        work_order_id="wo-1",
        task_id="task-1",
        workstream_id="ws-1",
        branch_ref="feature/agent-zero-sample",
        instructions="Implement the requested change.",
        granted_tools=frozenset({"read_file", "write_patch"}),
        allowed_path_globs=("src/**",),
        resources=_RESOURCES,
        timeout_s=300,
    )
    base.update(over)
    return WorkOrder(**base)  # type: ignore[arg-type]


def event(
    work_order_id: str, sequence: int, event_type: AgentZeroEventType, **payload: str
) -> AgentZeroEvent:
    return AgentZeroEvent(
        work_order_id=work_order_id,
        sequence=sequence,
        event_type=event_type,
        occurred_at=1000 + sequence,
        payload=payload,
    )


def full_success_stream(work_order_id: str = "wo-1") -> tuple[AgentZeroEvent, ...]:
    return (
        event(work_order_id, 0, AgentZeroEventType.STARTED),
        event(work_order_id, 1, AgentZeroEventType.PROGRESS, detail="scanning"),
        event(
            work_order_id,
            2,
            AgentZeroEventType.PATCH_PROPOSED,
            target_path="src/example.py",
            content_digest="a" * 64,
        ),
        event(
            work_order_id,
            3,
            AgentZeroEventType.EVIDENCE_ATTACHED,
            kind="test_run",
            detail="pytest passed",
        ),
        event(work_order_id, 4, AgentZeroEventType.COMPLETED),
    )


def full_failure_stream(work_order_id: str = "wo-1") -> tuple[AgentZeroEvent, ...]:
    return (
        event(work_order_id, 0, AgentZeroEventType.STARTED),
        event(work_order_id, 1, AgentZeroEventType.PROGRESS, detail="scanning"),
        event(work_order_id, 2, AgentZeroEventType.FAILED, reason="could not apply patch"),
    )


__all__ = [
    "FakeAgentZeroTransport",
    "ScriptedRun",
    "TransportFailure",
    "TransportTimeout",
    "event",
    "full_failure_stream",
    "full_success_stream",
    "sample_work_order",
]
