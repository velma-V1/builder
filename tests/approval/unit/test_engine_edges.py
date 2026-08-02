"""RPH3-T3 unit — engine guard branches (illegal transitions, replay, revoke, fail-closed)."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path

import pytest

from factory.approval import (
    ApprovalEngine,
    ApprovalError,
    ApprovalRecord,
    ApprovalRequest,
    DecisionKind,
    OperatorDecision,
    action_fingerprint,
)

RequestFactory = Callable[..., ApprovalRequest]


class _FixedClock:
    def now_ts(self) -> int:
        return 1_000_000

    def now_iso(self) -> str:
        return "2026-07-26T00:00:00Z"


def _grant(engine: ApprovalEngine, request: ApprovalRequest) -> ApprovalRecord:
    card = engine.enqueue(request)
    record = engine.decide(card.approval_id, OperatorDecision(DecisionKind.GRANT, operator="op"))
    assert isinstance(record, ApprovalRecord)
    return record


def test_decide_unknown_card_raises(engine: ApprovalEngine) -> None:
    with pytest.raises(ApprovalError) as exc:
        engine.decide("apr-missing", OperatorDecision(DecisionKind.GRANT, operator="op"))
    assert exc.value.code == "APPROVAL_NOT_FOUND"


def test_replayed_decision_rejected(engine: ApprovalEngine, make_request: RequestFactory) -> None:
    card = engine.enqueue(make_request())
    engine.decide(card.approval_id, OperatorDecision(DecisionKind.GRANT, operator="op"))
    # a second decision on the now-decided card is not awaiting a decision → rejected (replay guard)
    with pytest.raises(ApprovalError) as exc:
        engine.decide(card.approval_id, OperatorDecision(DecisionKind.DENY, operator="op"))
    assert exc.value.code == "APPROVAL_NOT_PENDING"


def test_consume_of_deleted_record_returns_false(
    engine: ApprovalEngine, make_request: RequestFactory
) -> None:
    record = _grant(engine, make_request())
    fingerprint = action_fingerprint(
        task_id=record.task_id,
        tool=record.tool,
        action=record.action,
        resource=record.resource,
        scope=record.scope,
    )
    # delete the row out-of-band (simulate a vanished record) → consume denies, does not crash
    raw = sqlite3.connect(str(engine.security_database_path))
    raw.execute("DELETE FROM approval_records WHERE approval_id = ?", (record.approval_id,))
    raw.commit()
    raw.close()
    assert engine.consume(record, fingerprint) is False


def test_revoke_unknown_record_raises(engine: ApprovalEngine) -> None:
    with pytest.raises(ApprovalError) as exc:
        engine.revoke("apr-missing")
    assert exc.value.code == "APPROVAL_NOT_FOUND"


def test_revoke_inflight_record_raises(
    engine: ApprovalEngine, make_request: RequestFactory
) -> None:
    card = engine.enqueue(make_request())
    # force the record into a non-authoritative (PENDING commit_state) state out-of-band
    raw = sqlite3.connect(str(engine.security_database_path))
    raw.execute(
        "UPDATE approval_records SET commit_state = 'PENDING' WHERE approval_id = ?",
        (card.approval_id,),
    )
    raw.commit()
    raw.close()
    with pytest.raises(ApprovalError) as exc:
        engine.revoke(card.approval_id)
    assert exc.value.code == "APPROVAL_INFLIGHT"


def test_revoke_terminal_record_raises(
    engine: ApprovalEngine, make_request: RequestFactory
) -> None:
    record = _grant(engine, make_request())
    engine.revoke(record.approval_id)  # → REVOKED (terminal)
    with pytest.raises(ApprovalError) as exc:
        engine.revoke(record.approval_id)  # revoking a terminal record is refused
    assert exc.value.code == "APPROVAL_NOT_REVOCABLE"


def test_security_violation_fails_closed_when_audit_unavailable(
    security_db_path: Path, tmp_path: Path, make_request: RequestFactory
) -> None:
    empty_audit = tmp_path / "empty.db"
    sqlite3.connect(str(empty_audit)).close()  # unmigrated → the denial audit itself fails
    engine = ApprovalEngine(
        security_database_path=security_db_path,
        audit_database_path=empty_audit,
        clock=_FixedClock(),
    )
    with pytest.raises(ApprovalError) as exc:
        engine.enqueue(make_request(security_violation=True))
    # still denied (fails closed either way), and nothing queued
    assert exc.value.code == "APPROVAL_SECURITY_VIOLATION"
    assert engine.reader.queue_ids() == ()
