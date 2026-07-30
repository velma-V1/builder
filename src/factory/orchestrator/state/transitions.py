"""Legal task/workstream transition policy — authoritative 01L §3.1 table.

`ALLOWED_TRANSITIONS` is a literal transcription of the 01L §3.1 legal-transition table so the
source document and this code can be diffed directly. `TransitionPolicy` is a pure, stateless
decision function; it applies no transition and touches no storage. No client may invent a
transition (01L §3.1) — every writer consults this before applying a state change.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from factory.orchestrator.models import TaskState

ALLOWED_TRANSITIONS: Mapping[TaskState, frozenset[TaskState]] = {
    TaskState.QUEUED: frozenset({TaskState.PLANNING}),
    TaskState.PLANNING: frozenset(
        {
            TaskState.RUNNING,
            TaskState.AWAITING_APPROVAL,
            TaskState.BLOCKED,
            TaskState.FAILED,
            TaskState.STOPPING,
        }
    ),
    TaskState.RUNNING: frozenset(
        {
            TaskState.AWAITING_APPROVAL,
            TaskState.VERIFYING,
            TaskState.BLOCKED,
            TaskState.PAUSED,
            TaskState.FAILED,
            TaskState.QUARANTINED,
            TaskState.STOPPING,
        }
    ),
    TaskState.AWAITING_APPROVAL: frozenset(
        {
            TaskState.RUNNING,
            TaskState.VERIFYING,
            TaskState.BLOCKED,
            TaskState.STOPPING,
        }
    ),
    TaskState.VERIFYING: frozenset(
        {
            TaskState.COMPLETE,
            TaskState.RUNNING,
            TaskState.AWAITING_APPROVAL,
            TaskState.BLOCKED,
            TaskState.FAILED,
            TaskState.QUARANTINED,
            TaskState.STOPPING,
        }
    ),
    TaskState.PAUSED: frozenset({TaskState.RUNNING, TaskState.BLOCKED, TaskState.STOPPING}),
    TaskState.BLOCKED: frozenset(
        {
            TaskState.PLANNING,
            TaskState.RUNNING,
            TaskState.AWAITING_APPROVAL,
            TaskState.FAILED,
            TaskState.STOPPING,
        }
    ),
    TaskState.QUARANTINED: frozenset({TaskState.BLOCKED, TaskState.FAILED, TaskState.STOPPING}),
    TaskState.STOPPING: frozenset({TaskState.CANCELLED}),
    TaskState.COMPLETE: frozenset({TaskState.ROLLED_BACK}),
    TaskState.FAILED: frozenset({TaskState.ROLLED_BACK}),
}


@dataclass(frozen=True, slots=True)
class TransitionPolicy:
    """Pure legality check over the 01L §3.1 table. Holds no state; applies no transition."""

    _allowed: Mapping[TaskState, frozenset[TaskState]] = field(
        default_factory=lambda: ALLOWED_TRANSITIONS
    )

    def is_legal(self, prev: TaskState, new: TaskState) -> bool:
        return new in self._allowed.get(prev, frozenset())
