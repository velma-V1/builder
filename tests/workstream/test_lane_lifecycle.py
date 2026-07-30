"""PH-6 unit — lane lifecycle SM + isolated checkouts (``01D §3.1/§2.8``)."""

from __future__ import annotations

import pytest

from factory.workstream import WorkstreamError
from factory.workstream.lane import (
    IsolatedCheckoutAssigner,
    Lane,
    LaneMachine,
    LaneState,
    is_legal,
)


def _lane(state: LaneState = LaneState.PROPOSED) -> Lane:
    return Lane("lane-1", "W1", state, checkout_id="wt-1")


def test_legal_transition_chain() -> None:
    machine = LaneMachine()
    lane = _lane()
    for target in (
        LaneState.APPROVED,
        LaneState.READY,
        LaneState.ACTIVE,
        LaneState.VERIFICATION,
        LaneState.HANDOFF,
        LaneState.INTEGRATED,
        LaneState.CLOSED,
    ):
        lane = machine.transition(lane, target, cause="advance", actor="scheduler")
    assert lane.state is LaneState.CLOSED
    assert len(machine.audit()) == 7
    assert machine.audit()[0].seq == 1


def test_illegal_transition_fails_closed_and_audits() -> None:
    machine = LaneMachine()
    with pytest.raises(WorkstreamError) as exc:
        machine.transition(_lane(LaneState.PROPOSED), LaneState.ACTIVE, cause="skip", actor="x")
    assert exc.value.code == "LANE_ILLEGAL_TRANSITION"
    assert machine.audit()[-1].cause.startswith("ILLEGAL:")


def test_lane_cannot_be_active_when_task_blocked() -> None:
    machine = LaneMachine()
    lane = machine.transition(_lane(), LaneState.APPROVED, cause="a", actor="x")
    lane = machine.transition(lane, LaneState.READY, cause="r", actor="x")
    with pytest.raises(WorkstreamError) as exc:
        machine.transition(lane, LaneState.ACTIVE, cause="go", actor="x", task_state="PAUSED")
    assert exc.value.code == "LANE_TASK_INCONSISTENT"


def test_is_legal_helper() -> None:
    assert is_legal(LaneState.READY, LaneState.ACTIVE)
    assert not is_legal(LaneState.CLOSED, LaneState.ACTIVE)


def test_isolated_checkout_assignment() -> None:
    assigner = IsolatedCheckoutAssigner()
    c1 = assigner.assign("lane-1", "repo")
    c2 = assigner.assign("lane-2", "repo")
    assert c1 != c2
    assert assigner.checkout_for("lane-1") == c1
    assert assigner.checkout_for("missing") is None
    assert assigner.is_isolated()
    with pytest.raises(WorkstreamError) as exc:
        assigner.assign("lane-1", "repo")  # double assignment denied
    assert exc.value.code == "CHECKOUT_ALREADY_ASSIGNED"
