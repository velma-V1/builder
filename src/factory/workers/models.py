"""Immutable/typed models for the Worker Engine (PH-3, CMP-WORKER).

The worker-slot lifecycle (IDLE→ASSIGNED→RUNNING→DONE, or →DEAD on crash) is local pool
bookkeeping only. It is NOT authoritative task state: every authoritative task-state change is
routed through the PH-2 `_OrchestratorStateWriter` (R1 single-writer). These shapes are the frozen
public interface for PH-3 (change = Change Contract, 01D §3.2).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class WorkerState(StrEnum):
    """Local worker-slot lifecycle. Not authoritative task state."""

    IDLE = "IDLE"
    ASSIGNED = "ASSIGNED"
    RUNNING = "RUNNING"
    DONE = "DONE"
    DEAD = "DEAD"


TERMINAL_WORKER_STATES: frozenset[WorkerState] = frozenset(
    {WorkerState.DONE, WorkerState.DEAD}
)


class ExecutionEventType(StrEnum):
    """Event kinds emitted during a single task execution (spec §Execution Event Stream)."""

    START = "START"
    PROGRESS = "PROGRESS"
    STDOUT = "STDOUT"
    STDERR = "STDERR"
    HEARTBEAT = "HEARTBEAT"
    END = "END"


@dataclass(frozen=True, slots=True)
class WorkerStatus:
    """Read-only snapshot of a worker slot (returned by WorkerPool.get_worker_status)."""

    worker_id: str
    state: WorkerState
    pid: int | None
    task_id: str | None
    process_epoch: str


@dataclass(frozen=True, slots=True)
class ExecutionEvent:
    """One event in a task-execution stream. Append-only; never mutated."""

    task_id: str
    sequence: int
    event_type: ExecutionEventType
    occurred_at: str
    payload: str


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """Terminal outcome of a single task execution. Untrusted worker output, size-bounded.

    ``exit_code`` is None only when the worker never produced an END event (crash/kill).
    ``output_hash`` is a SHA-256 over the captured output bytes (deterministic dedup key).
    """

    task_id: str
    exit_code: int | None
    output_hash: str
    events_captured: int
    truncated: bool
    failure_cause: str | None
