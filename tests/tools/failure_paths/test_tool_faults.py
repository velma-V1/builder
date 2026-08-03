"""RPH3-T5 failure-path — Class-1 crash windows, fail-closed audit, migration + writer faults."""

from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Callable
from pathlib import Path

import pytest

import factory.tools.store as store_mod
from factory.audit import AuditEvent, RecordKind
from factory.tools import (
    CommitState,
    OutputSchema,
    Provenance,
    RegistrationRequest,
    ToolDeclaration,
    ToolError,
    ToolRegistry,
    ToolState,
    apply_tool_migrations,
)
from factory.tools.registry import _new_op_key
from factory.tools.writer import _ToolWriter

pytestmark = pytest.mark.failure_path

DeclFactory = Callable[..., ToolDeclaration]
RegisterTool = Callable[..., ToolDeclaration]

SECURITY_MIGRATIONS_ROOT = Path(__file__).resolve().parents[3] / "migrations" / "security"


class _FixedClock:
    def now_ts(self) -> int:
        return 1_000_000

    def now_iso(self) -> str:
        return "2026-07-26T00:00:00Z"


def _stage_register(registry: ToolRegistry, tool_id: str, version: str, op_key: str) -> None:
    registry._writer.stage_register(
        tool_id=tool_id,
        version=version,
        op_key=op_key,
        declaration_hash="dh",
        provenance_source="s",
        provenance_checksum="c",
        license="MIT",
        declaration_json="{}",
        output_schema_json="{}",
        ts=1_000_000,
    )


def test_crash_before_audit_rolls_register_back(registry: ToolRegistry) -> None:
    op_key = _new_op_key("register", "t@1")
    _stage_register(registry, "t", "1", op_key)
    assert registry.reader.get_record("t", "1") is not None
    registry.reconcile_startup()
    assert registry.reader.get_record("t", "1") is None  # never authoritative → deleted


def test_crash_after_audit_rolls_register_forward(registry: ToolRegistry) -> None:
    op_key = _new_op_key("register", "t@1")
    _stage_register(registry, "t", "1", op_key)
    registry._audit.append(
        AuditEvent(
            op_key=op_key,
            record_kind=RecordKind.COMPLETION,
            operation_class=1,
            actor="a",
            action_class="tool.register",
            payload_hash="ph",
            occurred_at="t",
        )
    )
    registry.reconcile_startup()
    record = registry.reader.get_record("t", "1")
    assert record is not None and record.commit_state is CommitState.COMMITTED


def test_crash_before_audit_rolls_transition_back(
    registry: ToolRegistry, register_tool: RegisterTool
) -> None:
    register_tool()
    op_key = _new_op_key("quarantine", "formatter@1.0")
    registry._writer.stage_transition(
        tool_id="formatter",
        version="1.0",
        op_key=op_key,
        verb="quarantine",
        new_state=ToolState.QUARANTINED,
        ts=1_000_050,
        detail="x",
    )
    registry.reconcile_startup()
    record = registry.reader.get_record("formatter", "1.0")
    assert record is not None
    assert record.commit_state is CommitState.COMMITTED
    assert record.state is ToolState.REGISTERED  # rolled back to prior


def test_reconcile_is_idempotent(registry: ToolRegistry, register_tool: RegisterTool) -> None:
    register_tool()
    registry.reconcile_startup()
    registry.reconcile_startup()
    assert registry.reader.list_pending_intents() == ()


def test_register_fails_closed_when_audit_unavailable(
    security_db_path: Path, tmp_path: Path, make_declaration: DeclFactory
) -> None:
    empty_audit = tmp_path / "empty.db"
    sqlite3.connect(str(empty_audit)).close()
    registry = ToolRegistry(
        security_database_path=security_db_path,
        audit_database_path=empty_audit,
        clock=_FixedClock(),
    )
    request = RegistrationRequest(
        declaration=make_declaration(),
        provenance=Provenance(source="s", checksum="c", license="MIT"),
        output_schema=OutputSchema(kind="json", max_bytes=10, required_keys=()),
    )
    with pytest.raises(ToolError) as exc:
        registry.register(request)
    assert exc.value.code == "TOOL_AUDIT_FAILED"
    assert registry.reader.get_record("formatter", "1.0") is None


def test_reconcile_refuses_invalid_audit_chain(
    registry: ToolRegistry, audit_db_path: Path, register_tool: RegisterTool
) -> None:
    register_tool()
    tamper = sqlite3.connect(str(audit_db_path))
    tamper.execute("DROP TRIGGER audit_records_no_update")
    tamper.execute("UPDATE audit_records SET actor = 'evil' WHERE sequence = 1")
    tamper.commit()
    tamper.close()
    with pytest.raises(ToolError) as exc:
        registry.reconcile_startup()
    assert exc.value.code == "TOOL_AUDIT_CHAIN_INVALID"


def test_migration_missing_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(ToolError) as exc:
        apply_tool_migrations(tmp_path / "x.db", tmp_path / "empty")
    assert exc.value.code == "MIGRATION_MISSING"


def test_migration_malformed_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "m"
    root.mkdir()
    (root / "bad.sql").write_text("SELECT 1;")
    with pytest.raises(ToolError) as exc:
        apply_tool_migrations(tmp_path / "x.db", root)
    assert exc.value.code == "MIGRATION_MALFORMED"


def test_migration_integrity_mismatch_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "m"
    root.mkdir()
    (root / "0003_tools.sql").write_text("CREATE TABLE tampered (x);")
    with pytest.raises(ToolError) as exc:
        apply_tool_migrations(tmp_path / "x.db", root)
    assert exc.value.code == "MIGRATION_INTEGRITY"


def test_migration_apply_failure_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "m"
    root.mkdir()
    bad = root / "0003_bad.sql"
    bad.write_text("CREATE TABLE ok (x);\nNOT SQL;\n")
    digest = hashlib.sha256(bad.read_bytes()).hexdigest()
    monkeypatch.setattr(store_mod, "_EXPECTED_MIGRATION_HASHES", {"0003_bad.sql": digest})
    with pytest.raises(ToolError) as exc:
        apply_tool_migrations(tmp_path / "x.db", root)
    assert exc.value.code == "MIGRATION_FAILED"


def test_writer_faults_fail_closed(tmp_path: Path) -> None:
    db = tmp_path / "s.db"
    apply_tool_migrations(db, SECURITY_MIGRATIONS_ROOT)
    writer = _ToolWriter(database_path=db)
    with pytest.raises(ToolError) as exc:
        writer.stage_transition(
            tool_id="ghost",
            version="1",
            op_key="k",
            verb="quarantine",
            new_state=ToolState.QUARANTINED,
            ts=1,
        )
    assert exc.value.code == "TOOL_NOT_FOUND"
    broken = sqlite3.connect(str(db))
    broken.execute("DROP TABLE tool_registry")
    broken.commit()
    broken.close()
    with pytest.raises(ToolError) as exc2:
        writer.commit_operation(tool_id="t", version="1", op_key="k", audit_seq=1, ts=1)
    assert exc2.value.code == "TOOL_COMMIT_FAILED"
