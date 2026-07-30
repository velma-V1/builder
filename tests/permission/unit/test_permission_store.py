"""RPH3-T2 unit — permission store: migration idempotency, reader edges, audit join, authz."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from factory.audit import AuditEvent, AuditWriter, RecordKind
from factory.permission import (
    PermissionError,
    SQLitePermissionReader,
    SystemClock,
    apply_permission_migrations,
    audit_completion_seq,
)
from factory.permission.store import _permission_writer_authorizer
from factory.permission.writer import _PermissionWriter

SECURITY_MIGRATIONS_ROOT = Path(__file__).resolve().parents[3] / "migrations" / "security"


def test_migration_is_idempotent(security_db_path: Path) -> None:
    apply_permission_migrations(security_db_path, SECURITY_MIGRATIONS_ROOT)  # second apply
    connection = sqlite3.connect(str(security_db_path))
    try:
        versions = [r[0] for r in connection.execute("SELECT version FROM schema_migrations")]
    finally:
        connection.close()
    assert versions == [2]  # only the permission migration; the approval 0001 is another domain's


def test_reader_absent_returns_none(reader: SQLitePermissionReader) -> None:
    assert reader.get_grant("nope") is None
    assert reader.list_active_for_task("task-x") == ()
    assert reader.list_pending_intents() == ()
    assert reader.list_expirable(2_000_000) == ()


def test_audit_completion_seq_present_and_absent(audit_db_path: Path) -> None:
    assert audit_completion_seq(audit_db_path, "no-op") is None
    AuditWriter(database_path=audit_db_path).append(
        AuditEvent(
            op_key="op-1", record_kind=RecordKind.COMPLETION, operation_class=1, actor="a",
            action_class="permission.issue", payload_hash="p", occurred_at="t",
        )
    )
    assert audit_completion_seq(audit_db_path, "op-1") == 1


def test_writer_authorizer_matrix() -> None:
    def authz(action: int, table: str | None) -> int:
        return _permission_writer_authorizer(action, table, None, None, None)

    assert authz(sqlite3.SQLITE_INSERT, "permission_grants") == sqlite3.SQLITE_OK
    assert authz(sqlite3.SQLITE_UPDATE, "approval_records") == sqlite3.SQLITE_DENY
    assert authz(sqlite3.SQLITE_DROP_TABLE, "permission_grants") == sqlite3.SQLITE_DENY
    assert authz(sqlite3.SQLITE_SELECT, None) == sqlite3.SQLITE_OK


def test_writer_authorizer_denies_ddl(security_db_path: Path) -> None:
    connection = _PermissionWriter(database_path=security_db_path)._connect()
    try:
        with pytest.raises(sqlite3.DatabaseError):
            connection.execute("CREATE TABLE sneaky (x)")
    finally:
        connection.close()


def test_system_clock_shapes() -> None:
    clock = SystemClock()
    assert isinstance(clock.now_ts(), int)
    assert clock.now_iso().endswith("Z")


def test_permission_error_str() -> None:
    assert str(PermissionError("CODE_X", "message y")) == "CODE_X: message y"
