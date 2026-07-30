"""RPH3-T3 unit — security-spine store: migration idempotency, reader edges, audit join, authz."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from factory.approval import (
    ApprovalError,
    SQLiteApprovalReader,
    SystemClock,
    apply_security_migrations,
    audit_completion_seq,
)
from factory.approval.store import _approval_writer_authorizer
from factory.approval.writer import _ApprovalWriter
from factory.audit import AuditEvent, AuditWriter, RecordKind

SECURITY_MIGRATIONS_ROOT = Path(__file__).resolve().parents[3] / "migrations" / "security"


def test_migration_is_idempotent(security_db_path: Path) -> None:
    # security_db_path is already migrated; a second apply must skip the applied version (no error).
    apply_security_migrations(security_db_path, SECURITY_MIGRATIONS_ROOT)
    connection = sqlite3.connect(str(security_db_path))
    try:
        versions = [r[0] for r in connection.execute("SELECT version FROM schema_migrations")]
    finally:
        connection.close()
    assert versions == [1]  # not double-inserted


def test_reader_get_record_absent_returns_none(reader: SQLiteApprovalReader) -> None:
    assert reader.get_record("nope") is None
    assert reader.list_committed_pending() == ()
    assert reader.list_pending_intents() == ()
    assert reader.queue_ids() == ()
    assert reader.list_expirable(2_000_000) == ()


def test_audit_completion_seq_present_and_absent(audit_db_path: Path) -> None:
    assert audit_completion_seq(audit_db_path, "no-such-op") is None
    AuditWriter(database_path=audit_db_path).append(
        AuditEvent(
            op_key="op-1", record_kind=RecordKind.COMPLETION, operation_class=1, actor="a",
            action_class="approval.enqueue", payload_hash="p", occurred_at="t",
        )
    )
    assert audit_completion_seq(audit_db_path, "op-1") == 1


def test_writer_authorizer_denies_ddl(security_db_path: Path) -> None:
    connection = _ApprovalWriter(database_path=security_db_path)._connect()
    try:
        with pytest.raises(sqlite3.DatabaseError):
            connection.execute("CREATE TABLE sneaky (x)")  # DDL denied by the writer authorizer
    finally:
        connection.close()


def test_writer_authorizer_unit_matrix() -> None:
    # DML on an approval table is allowed; DML elsewhere and DDL are denied; reads are allowed.
    def authz(action: int, table: str | None) -> int:
        return _approval_writer_authorizer(action, table, None, None, None)

    assert authz(sqlite3.SQLITE_INSERT, "approval_records") == sqlite3.SQLITE_OK
    assert authz(sqlite3.SQLITE_UPDATE, "schema_migrations") == sqlite3.SQLITE_DENY
    assert authz(sqlite3.SQLITE_DROP_TABLE, "approval_records") == sqlite3.SQLITE_DENY
    assert authz(sqlite3.SQLITE_SELECT, None) == sqlite3.SQLITE_OK


def test_system_clock_shapes() -> None:
    clock = SystemClock()
    assert isinstance(clock.now_ts(), int)
    assert clock.now_iso().endswith("Z")


def test_approval_error_str() -> None:
    assert str(ApprovalError("CODE_X", "message y")) == "CODE_X: message y"
