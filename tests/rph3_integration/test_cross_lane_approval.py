from __future__ import annotations

from typing import Protocol

from factory.approval import (
    ApprovalEngine,
    ApprovalRecord,
    ApprovalRequest,
    DecisionKind,
    OperatorDecision,
    action_fingerprint,
)
from factory.watchdog import CrossLaneOutcome, RPH3CrossLaneBridge
from factory.watchdog.models import Clock


class AdvancingClock(Clock, Protocol):
    def advance(self, seconds: int) -> None: ...


def _request(ttl: int = 10) -> ApprovalRequest:
    return ApprovalRequest(
        task_id="task-1",
        tool="fileop",
        action="delete",
        scope="repo",
        purpose="cleanup",
        consequences="deletes a file",
        autonomy_level="L2-supervised",
        ttl_seconds=ttl,
        resource="old.txt",
        destructive=True,
    )


def test_real_approval_required_expired_and_replay_results_propagate(
    bridge: RPH3CrossLaneBridge,
    approval_engine: ApprovalEngine,
    clock: AdvancingClock,
) -> None:
    pending_card = approval_engine.enqueue(_request())
    pending = approval_engine.reader.get_record(pending_card.approval_id)
    assert pending is not None
    assert (
        bridge.from_approval(pending, "op-approval-pending").outcome
        is CrossLaneOutcome.APPROVAL_REQUIRED
    )

    granted = approval_engine.decide(
        pending.approval_id,
        OperatorDecision(DecisionKind.GRANT, "operator", confirmed_destructive=True),
    )
    assert isinstance(granted, ApprovalRecord)
    assert bridge.from_approval(granted, "op-approval-granted").outcome is CrossLaneOutcome.HEALTHY
    clock.advance(11)
    expired = bridge.from_approval(granted, "op-approval-expired")
    assert expired.outcome is CrossLaneOutcome.DENIED
    assert "expired" in expired.detail

    card = approval_engine.enqueue(_request(ttl=100))
    replay_record = approval_engine.decide(
        card.approval_id,
        OperatorDecision(DecisionKind.GRANT, "operator", confirmed_destructive=True),
    )
    assert isinstance(replay_record, ApprovalRecord)
    fingerprint = action_fingerprint(
        task_id="task-1",
        tool="fileop",
        action="delete",
        resource="old.txt",
        scope="repo",
    )
    assert approval_engine.consume(replay_record, fingerprint)
    consumed = approval_engine.reader.get_record(replay_record.approval_id)
    assert consumed is not None
    replay = bridge.from_approval(consumed, "op-approval-replay")
    assert replay.outcome is CrossLaneOutcome.DENIED
    assert "consumed" in replay.detail
