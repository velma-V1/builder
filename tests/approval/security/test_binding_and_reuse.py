"""RPH3-T3 security — scope binding, non-reuse (01K-AC-03), security-violation denial, isolation.

These are the adversarial controls of ``approval-spec``: an approval is bound and single-use per its
repetition budget; a security violation is never offered as a card (denied + audited); and the
domain writer/reader are structurally confined (DEP-RPH3 §4A).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

import pytest

import factory.approval as approval_pkg
from factory.approval import (
    ApprovalEngine,
    ApprovalError,
    ApprovalRecord,
    ApprovalRequest,
    ApprovalState,
    DecisionKind,
    Denial,
    OperatorDecision,
    SQLiteApprovalReader,
    action_fingerprint,
)
from factory.approval.writer import _ApprovalWriter
from factory.audit import AuditWriter

pytestmark = pytest.mark.security

RequestFactory = Callable[..., ApprovalRequest]


class ControllableClock(Protocol):
    def now_ts(self) -> int: ...
    def advance(self, seconds: int) -> None: ...


def _grant(engine: ApprovalEngine, request: ApprovalRequest) -> tuple[ApprovalRecord, str]:
    card = engine.enqueue(request)
    record = engine.decide(card.approval_id, OperatorDecision(DecisionKind.GRANT, operator="op"))
    assert isinstance(record, ApprovalRecord)
    fingerprint = action_fingerprint(
        task_id=request.task_id,
        tool=request.tool,
        action=request.action,
        resource=request.resource,
        scope=request.scope,
    )
    return record, fingerprint


def test_scope_binding_rejects_other_action(
    engine: ApprovalEngine, make_request: RequestFactory
) -> None:
    record, _ = _grant(engine, make_request())
    other = action_fingerprint(
        task_id="task-1",
        tool="shell",
        action="DELETE_everything",
        resource="repo/src/main.py",
        scope="repo/src",
    )
    assert engine.consume(record, other) is False  # bound to (task, action, path, scope)


def test_consumed_record_cannot_be_reused(
    engine: ApprovalEngine, make_request: RequestFactory
) -> None:
    record, fingerprint = _grant(engine, make_request(repetition_limit=1))
    assert engine.consume(record, fingerprint) is True
    stale = engine.reader.get_record(record.approval_id)
    assert stale is not None and stale.state is ApprovalState.CONSUMED
    assert engine.consume(stale, fingerprint) is False  # 01K-AC-03: no reuse


def test_revoked_record_cannot_be_reused(
    engine: ApprovalEngine, make_request: RequestFactory
) -> None:
    record, fingerprint = _grant(engine, make_request(repetition_limit=5))
    engine.revoke(record.approval_id)
    assert engine.consume(record, fingerprint) is False


def test_expired_record_cannot_be_reused(
    engine: ApprovalEngine, clock: ControllableClock, make_request: RequestFactory
) -> None:
    record, fingerprint = _grant(engine, make_request(ttl_seconds=5))
    clock.advance(6)
    engine.expire()
    assert engine.consume(record, fingerprint) is False


def test_security_violation_denied_audited_never_queued(
    engine: ApprovalEngine,
    reader: SQLiteApprovalReader,
    audit_db_path: Path,
    make_request: RequestFactory,
) -> None:
    with pytest.raises(ApprovalError) as exc:
        engine.enqueue(make_request(action="disable_watchdog", security_violation=True))
    assert exc.value.code == "APPROVAL_SECURITY_VIOLATION"
    # never queued, no record created
    assert reader.queue_ids() == ()
    assert reader.list_committed_pending() == ()
    # but it IS audited (denied + audited)
    audit_records = AuditWriter(database_path=audit_db_path).export()
    assert any(r.action_class == "approval.security_violation_denied" for r in audit_records)


def test_destructive_grant_requires_separate_confirmation(
    engine: ApprovalEngine, make_request: RequestFactory
) -> None:
    card = engine.enqueue(make_request(action="delete_tree", destructive=True))
    assert card.requires_separate_confirmation is True
    unconfirmed = engine.decide(
        card.approval_id, OperatorDecision(DecisionKind.GRANT, operator="op")
    )
    assert isinstance(unconfirmed, Denial)
    assert unconfirmed.reason_code == "CONFIRMATION_REQUIRED"
    confirmed = engine.decide(
        card.approval_id,
        OperatorDecision(DecisionKind.GRANT, operator="op", confirmed_destructive=True),
    )
    assert isinstance(confirmed, ApprovalRecord)
    assert confirmed.state is ApprovalState.GRANTED


# --- structural isolation (DEP-RPH3 §4A) ---------------------------------------------------------


def test_writer_denied_writes_outside_approval_tables(security_db_path: Path) -> None:
    connection = _ApprovalWriter(database_path=security_db_path)._connect()
    try:
        with pytest.raises(sqlite3.DatabaseError):
            connection.execute(
                "INSERT INTO schema_migrations (version, applied_at) VALUES (99, 'x')"
            )
    finally:
        connection.close()


def test_reader_connection_denies_every_write(security_db_path: Path) -> None:
    connection = SQLiteApprovalReader(database_path=security_db_path)._connect()
    try:
        with pytest.raises(sqlite3.DatabaseError):
            connection.execute("UPDATE approval_records SET state = 'X'")
    finally:
        connection.close()


def test_writer_is_not_publicly_exported() -> None:
    # The writable connection lives inside a private, un-exported writer (no raw connection).
    assert "_ApprovalWriter" not in approval_pkg.__all__
    assert not hasattr(approval_pkg, "_ApprovalWriter")
