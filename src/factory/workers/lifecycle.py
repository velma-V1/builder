"""Worker-slot lifecycle transition policy (PH-3, CMP-WORKER, Task 3.1).

Pure function, no side effects (mirrors PH-2 `TransitionPolicy`). Guards the local worker-slot
state machine so the pool cannot advance a slot through an illegal path (e.g. IDLE→RUNNING
skipping ASSIGNED, or resurrecting a DEAD slot in place).
"""

from __future__ import annotations

from factory.workers.models import WorkerState

# worker-slot legal transitions. DEAD/DONE are reclaimed by allocating a fresh slot, never by an
# in-place transition back to IDLE — a crashed process handle must not be silently reused.
_ALLOWED: frozenset[tuple[WorkerState, WorkerState]] = frozenset(
    {
        (WorkerState.IDLE, WorkerState.ASSIGNED),
        (WorkerState.ASSIGNED, WorkerState.RUNNING),
        (WorkerState.ASSIGNED, WorkerState.DEAD),
        (WorkerState.RUNNING, WorkerState.DONE),
        (WorkerState.RUNNING, WorkerState.DEAD),
    }
)


def is_legal(current: WorkerState, new: WorkerState) -> bool:
    """True iff advancing a worker slot ``current → new`` is permitted."""
    return (current, new) in _ALLOWED
