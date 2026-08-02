"""Lane lifecycle state machine (CTR-LANE-LIFECYCLE, ``01D §3.1``).

The lane lifecycle is a separate execution dimension that must stay consistent with the
authoritative task/workstream state machine: a lane cannot be ``ACTIVE`` when its owning task is
paused, cancelled, failed, quarantined, or rolled back. Invalid transitions fail closed and audit.
Each
lane holds its own isolated checkout id so concurrent same-repo lanes cannot share one workspace.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from factory.workstream.errors import WorkstreamError


class LaneState(StrEnum):
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    READY = "READY"
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"
    PAUSED = "PAUSED"
    VERIFICATION = "VERIFICATION"
    HANDOFF = "HANDOFF"
    INTEGRATED = "INTEGRATED"
    CLOSED = "CLOSED"
    FAILED = "FAILED"
    QUARANTINED = "QUARANTINED"


_LEGAL: dict[LaneState, frozenset[LaneState]] = {
    LaneState.PROPOSED: frozenset({LaneState.APPROVED}),
    LaneState.APPROVED: frozenset({LaneState.READY}),
    LaneState.READY: frozenset(
        {LaneState.ACTIVE, LaneState.BLOCKED, LaneState.FAILED, LaneState.QUARANTINED}
    ),
    LaneState.ACTIVE: frozenset(
        {
            LaneState.BLOCKED,
            LaneState.PAUSED,
            LaneState.VERIFICATION,
            LaneState.FAILED,
            LaneState.QUARANTINED,
        }
    ),
    LaneState.BLOCKED: frozenset(
        {LaneState.READY, LaneState.ACTIVE, LaneState.FAILED, LaneState.QUARANTINED}
    ),
    LaneState.PAUSED: frozenset(
        {LaneState.READY, LaneState.ACTIVE, LaneState.FAILED, LaneState.QUARANTINED}
    ),
    LaneState.VERIFICATION: frozenset(
        {LaneState.ACTIVE, LaneState.HANDOFF, LaneState.FAILED, LaneState.QUARANTINED}
    ),
    LaneState.HANDOFF: frozenset(
        {LaneState.ACTIVE, LaneState.INTEGRATED, LaneState.FAILED, LaneState.QUARANTINED}
    ),
    LaneState.INTEGRATED: frozenset({LaneState.CLOSED, LaneState.FAILED, LaneState.QUARANTINED}),
    LaneState.FAILED: frozenset({LaneState.READY, LaneState.QUARANTINED, LaneState.CLOSED}),
    LaneState.QUARANTINED: frozenset({LaneState.BLOCKED, LaneState.FAILED, LaneState.CLOSED}),
    LaneState.CLOSED: frozenset(),
}

# Task states under which a lane may not be ACTIVE (``01D §3.1`` consistency rule).
_TASK_BLOCKS_ACTIVE = frozenset({"PAUSED", "CANCELLED", "FAILED", "QUARANTINED", "ROLLED_BACK"})


@dataclass(frozen=True, slots=True)
class Lane:
    lane_id: str
    workstream_id: str
    state: LaneState
    checkout_id: str
    sandbox_id: str = ""
    route_key: str = ""


@dataclass(frozen=True, slots=True)
class LaneTransition:
    lane_id: str
    from_state: LaneState
    to_state: LaneState
    cause: str
    actor: str
    seq: int


def is_legal(from_state: LaneState, to_state: LaneState) -> bool:
    return to_state in _LEGAL[from_state]


class LaneMachine:
    """Applies legal lane transitions and records an ordered audit log."""

    __slots__ = ("_audit", "_seq")

    def __init__(self) -> None:
        self._seq = 0
        self._audit: list[LaneTransition] = []

    def transition(
        self, lane: Lane, to_state: LaneState, *, cause: str, actor: str, task_state: str = "ACTIVE"
    ) -> Lane:
        if not is_legal(lane.state, to_state):
            self._record(lane, lane.state, cause="ILLEGAL:" + cause, actor=actor)
            raise WorkstreamError(
                "LANE_ILLEGAL_TRANSITION", f"{lane.state.value} -> {to_state.value} is illegal"
            )
        if to_state is LaneState.ACTIVE and task_state in _TASK_BLOCKS_ACTIVE:
            self._record(lane, lane.state, cause="TASK_BLOCKS_ACTIVE", actor=actor)
            raise WorkstreamError(
                "LANE_TASK_INCONSISTENT",
                f"lane cannot be ACTIVE while owning task is {task_state}",
            )
        self._record(lane, to_state, cause=cause, actor=actor)
        return replace(lane, state=to_state)

    def _record(self, lane: Lane, to_state: LaneState, *, cause: str, actor: str) -> None:
        self._seq += 1
        self._audit.append(
            LaneTransition(lane.lane_id, lane.state, to_state, cause, actor, self._seq)
        )

    def audit(self) -> tuple[LaneTransition, ...]:
        return tuple(self._audit)
