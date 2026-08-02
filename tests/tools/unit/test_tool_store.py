"""RPH3-T5 unit — tool store: migration idempotency, reader edges, authorizer, audit join."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from factory.audit import AuditEvent, AuditWriter, RecordKind
from factory.tools import SQLiteToolReader, ToolError, apply_tool_migrations, audit_completion_seq
from factory.tools.registry import SystemClock
from factory.tools.store import _tool_writer_authorizer
from factory.tools.writer import _ToolWriter

SECURITY_MIGRATIONS_ROOT = Path(__file__).resolve().parents[3] / "migrations" / "security"


def test_migration_is_idempotent(security_db_path: Path) -> None:
    apply_tool_migrations(security_db_path, SECURITY_MIGRATIONS_ROOT)
    connection = sqlite3.connect(str(security_db_path))
    try:
        versions = sorted(r[0] for r in connection.execute("SELECT version FROM schema_migrations"))
    finally:
        connection.close()
    assert 3 in versions  # tool migration applied; approval 0001 skipped by this runner


def test_reader_absent_returns_none(security_db_path: Path) -> None:
    reader = SQLiteToolReader(database_path=security_db_path)
    assert reader.get_record("ghost", "1") is None
    assert reader.get_declaration("ghost", "1") is None
    assert reader.get_output_schema("ghost", "1") is None
    assert reader.list_pending_intents() == ()


def test_audit_completion_seq_present_and_absent(audit_db_path: Path) -> None:
    assert audit_completion_seq(audit_db_path, "no-op") is None
    AuditWriter(database_path=audit_db_path).append(
        AuditEvent(
            op_key="op-1",
            record_kind=RecordKind.COMPLETION,
            operation_class=1,
            actor="a",
            action_class="tool.register",
            payload_hash="p",
            occurred_at="t",
        )
    )
    assert audit_completion_seq(audit_db_path, "op-1") == 1


def test_writer_authorizer_matrix() -> None:
    def authz(action: int, table: str | None) -> int:
        return _tool_writer_authorizer(action, table, None, None, None)

    assert authz(sqlite3.SQLITE_INSERT, "tool_registry") == sqlite3.SQLITE_OK
    assert authz(sqlite3.SQLITE_UPDATE, "approval_records") == sqlite3.SQLITE_DENY
    assert authz(sqlite3.SQLITE_UPDATE, "permission_grants") == sqlite3.SQLITE_DENY
    assert authz(sqlite3.SQLITE_DROP_TABLE, "tool_registry") == sqlite3.SQLITE_DENY
    assert authz(sqlite3.SQLITE_SELECT, None) == sqlite3.SQLITE_OK


def test_writer_authorizer_denies_ddl(security_db_path: Path) -> None:
    connection = _ToolWriter(database_path=security_db_path)._connect()
    try:
        with pytest.raises(sqlite3.DatabaseError):
            connection.execute("CREATE TABLE sneaky (x)")
    finally:
        connection.close()


def test_system_clock_shapes() -> None:
    clock = SystemClock()
    assert isinstance(clock.now_ts(), int)
    assert clock.now_iso().endswith("Z")


def test_tool_error_str() -> None:
    assert str(ToolError("CODE_X", "message y")) == "CODE_X: message y"
