"""RPH3-T3 unit — Approval Engine lifecycle (enqueue / decide / consume / revoke / expire).

Covers the interface contract of ``approval-spec``: complete cards (01L §3.2), grant issues a bound
record, expiry, repetition, and the ``is_valid`` scope+expiry+repetition predicate.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

import pytest

from factory.approval import (
    ApprovalEngine,
    ApprovalRecord,
    ApprovalRequest,
    ApprovalState,
    CommitState,
    DecisionKind,
    Denial,
    OperatorDecision,
    SQLiteApprovalReader,
    action_fingerprint,
)

RequestFactory = Callable[..., ApprovalRequest]


class ControllableClock(Protocol):
    def now_ts(self) -> int: ...
    def advance(self, seconds: int) -> None: ...


def _grant(engine: ApprovalEngine, request: ApprovalRequest) -> tuple[ApprovalRecord, str]:
    card = engine.enqueue(request)
    record = engine.decide(card.approval_id, OperatorDecision(DecisionKind.GRANT, operator="op"))
    assert isinstance(record, ApprovalRecord)
    fingerprint = action_fingerprint(
        task_id=request.task_id, tool=request.tool, action=request.action,
        resource=request.resource, scope=request.scope,
    )
    return record, fingerprint


def test_enqueue_returns_complete_card(
    engine: ApprovalEngine, make_request: RequestFactory
) -> None:
    card = engine.enqueue(make_request())
    assert card.is_complete()
    assert card.state is ApprovalState.PENDING
    assert card.autonomy_level == "L2-supervised"
    assert card.consequences
    assert card.approval_id.startswith("apr-")


def test_enqueue_adds_committed_pending_to_queue(
    engine: ApprovalEngine, reader: SQLiteApprovalReader, make_request: RequestFactory
) -> None:
    card = engine.enqueue(make_request())
    assert reader.queue_ids() == (card.approval_id,)
    assert [r.approval_id for r in reader.list_committed_pending()] == [card.approval_id]
    stored = reader.get_record(card.approval_id)
    assert stored is not None
    assert stored.commit_state is CommitState.COMMITTED
    assert stored.state is ApprovalState.PENDING


def test_grant_issues_bound_committed_record_and_clears_queue(
    engine: ApprovalEngine, reader: SQLiteApprovalReader, make_request: RequestFactory
) -> None:
    request = make_request()
    record, fingerprint = _grant(engine, request)
    assert record.state is ApprovalState.GRANTED
    assert record.commit_state is CommitState.COMMITTED
    assert record.action_fingerprint == fingerprint
    assert reader.queue_ids() == ()  # decided → dropped from the queue


def test_deny_returns_denial_and_marks_record(
    engine: ApprovalEngine, reader: SQLiteApprovalReader, make_request: RequestFactory
) -> None:
    card = engine.enqueue(make_request())
    outcome = engine.decide(card.approval_id, OperatorDecision(DecisionKind.DENY, operator="op"))
    assert isinstance(outcome, Denial)
    assert outcome.reason_code == "OPERATOR_DENIED"
    stored = reader.get_record(card.approval_id)
    assert stored is not None
    assert stored.state is ApprovalState.DENIED
    assert reader.queue_ids() == ()


def test_consume_happy_path(engine: ApprovalEngine, make_request: RequestFactory) -> None:
    record, fingerprint = _grant(engine, make_request())
    assert engine.consume(record, fingerprint) is True
    refreshed = engine.reader.get_record(record.approval_id)
    assert refreshed is not None
    assert refreshed.state is ApprovalState.CONSUMED  # repetition_limit=1 → exhausted after one use


def test_repetition_limit_consumes_at_most_n_then_invalid(
    engine: ApprovalEngine, make_request: RequestFactory
) -> None:
    record, fingerprint = _grant(engine, make_request(repetition_limit=3))
    assert engine.consume(record, fingerprint) is True
    assert engine.consume(record, fingerprint) is True
    third = engine.reader.get_record(record.approval_id)
    assert third is not None
    assert third.state is ApprovalState.GRANTED  # still usable (2 of 3)
    assert engine.consume(third, fingerprint) is True  # third use → exhausted
    exhausted = engine.reader.get_record(record.approval_id)
    assert exhausted is not None
    assert exhausted.state is ApprovalState.CONSUMED
    assert engine.consume(exhausted, fingerprint) is False  # no fourth use


def test_expiry_auto_and_swept(
    engine: ApprovalEngine, clock: ControllableClock, make_request: RequestFactory
) -> None:
    record, fingerprint = _grant(engine, make_request(ttl_seconds=10))
    clock.advance(11)
    # auto-expiry: is_valid / consume refuse a past-expiry record even before the sweep runs.
    assert engine.is_valid(record, clock.now_ts()) is False
    assert engine.consume(record, fingerprint) is False
    expired = engine.expire()
    assert expired == (record.approval_id,)
    swept = engine.reader.get_record(record.approval_id)
    assert swept is not None
    assert swept.state is ApprovalState.EXPIRED


def test_revoke_makes_record_unusable(
    engine: ApprovalEngine, make_request: RequestFactory
) -> None:
    record, fingerprint = _grant(engine, make_request(repetition_limit=5))
    engine.revoke(record.approval_id)
    revoked = engine.reader.get_record(record.approval_id)
    assert revoked is not None
    assert revoked.state is ApprovalState.REVOKED
    assert engine.consume(record, fingerprint) is False


def test_is_valid_predicate(
    engine: ApprovalEngine, clock: ControllableClock, make_request: RequestFactory
) -> None:
    record, _ = _grant(engine, make_request(ttl_seconds=100))
    assert engine.is_valid(record, clock.now_ts()) is True
    assert engine.is_valid(record, record.expires_at) is False  # boundary: at == expiry is invalid


def test_expire_of_undecided_pending_card(
    engine: ApprovalEngine, clock: ControllableClock, make_request: RequestFactory
) -> None:
    card = engine.enqueue(make_request(ttl_seconds=5))
    clock.advance(10)
    assert engine.expire() == (card.approval_id,)
    assert engine.reader.queue_ids() == ()  # expiring a pending card drops it from the queue


@pytest.mark.parametrize("bad", [{"ttl_seconds": 0}, {"repetition_limit": 0}, {"purpose": ""}])
def test_invalid_request_rejected(
    engine: ApprovalEngine, make_request: RequestFactory, bad: dict[str, object]
) -> None:
    from factory.approval import ApprovalError

    with pytest.raises(ApprovalError) as exc:
        engine.enqueue(make_request(**bad))
    assert exc.value.code == "APPROVAL_INVALID_REQUEST"
