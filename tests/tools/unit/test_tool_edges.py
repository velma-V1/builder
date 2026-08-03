"""RPH3-T5 unit — edge branches: output validation, in-flight lookup, fail-closed, writer."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path

import pytest

from factory.tools import (
    CommitState,
    OutputSchema,
    ToolDeclaration,
    ToolError,
    ToolGateway,
    ToolRegistry,
    ToolState,
    apply_tool_migrations,
)
from factory.tools.gateway import SystemClock as GatewaySystemClock
from factory.tools.registry import _new_op_key
from factory.tools.writer import _ToolWriter

RegisterTool = Callable[..., ToolDeclaration]

SECURITY_MIGRATIONS_ROOT = Path(__file__).resolve().parents[3] / "migrations" / "security"


def test_gateway_system_clock_shapes() -> None:
    clock = GatewaySystemClock()
    assert isinstance(clock.now_ts(), int)
    assert clock.now_iso().endswith("Z")


def test_validate_output_text_ok(gateway: ToolGateway) -> None:
    out = gateway.validate_output(b"plain text", OutputSchema(kind="text", max_bytes=100))
    assert out.payload == "plain text"


def test_validate_output_rejects_non_utf8(gateway: ToolGateway) -> None:
    from factory.tools.gateway import _OutputInvalid

    with pytest.raises(_OutputInvalid):
        gateway.validate_output(b"\xff\xfe", OutputSchema(kind="text", max_bytes=100))


def test_validate_output_rejects_bad_json(gateway: ToolGateway) -> None:
    from factory.tools.gateway import _OutputInvalid

    with pytest.raises(_OutputInvalid):
        gateway.validate_output(b"not json", OutputSchema(kind="json", max_bytes=100))


def test_validate_output_rejects_non_object_json(gateway: ToolGateway) -> None:
    from factory.tools.gateway import _OutputInvalid

    with pytest.raises(_OutputInvalid):
        gateway.validate_output(b"[1,2,3]", OutputSchema(kind="json", max_bytes=100))


def test_terminate_tree_with_executor_is_noop(gateway: ToolGateway) -> None:
    class _E:
        def run(self, call: object, limits: object) -> bytes:
            return b""

    gateway.terminate_tree(_E())  # no raise when an executor exists


def test_lookup_inflight_record_is_none(registry: ToolRegistry) -> None:
    op_key = _new_op_key("register", "t@1")
    registry._writer.stage_register(
        tool_id="t",
        version="1",
        op_key=op_key,
        declaration_hash="dh",
        provenance_source="s",
        provenance_checksum="c",
        license="MIT",
        declaration_json="{}",
        output_schema_json="{}",
        ts=1_000_000,
    )
    record = registry.reader.get_record("t", "1")
    assert record is not None and record.commit_state is CommitState.PENDING
    assert registry.lookup("t", "1") is None  # non-authoritative ⇒ uncallable


def test_transition_fails_closed_and_restores_prior(
    registry: ToolRegistry, audit_db_path: Path, register_tool: RegisterTool
) -> None:
    register_tool()
    broken = sqlite3.connect(str(audit_db_path))
    broken.execute("DROP TABLE audit_records")
    broken.commit()
    broken.close()
    with pytest.raises(ToolError) as exc:
        registry.quarantine("formatter", "1.0", "x")
    assert exc.value.code == "TOOL_AUDIT_FAILED"
    record = registry.reader.get_record("formatter", "1.0")
    assert record is not None and record.state is ToolState.REGISTERED  # rolled back


def test_writer_stage_register_and_rollback_faults(tmp_path: Path) -> None:
    db = tmp_path / "s.db"
    apply_tool_migrations(db, SECURITY_MIGRATIONS_ROOT)
    broken = sqlite3.connect(str(db))
    broken.execute("DROP TABLE tool_declarations")
    broken.commit()
    broken.close()
    writer = _ToolWriter(database_path=db)
    with pytest.raises(ToolError) as exc:
        writer.stage_register(
            tool_id="t",
            version="1",
            op_key="k",
            declaration_hash="d",
            provenance_source="s",
            provenance_checksum="c",
            license="MIT",
            declaration_json="{}",
            output_schema_json="{}",
            ts=1,
        )
    assert exc.value.code == "TOOL_STAGE_FAILED"


def test_writer_rollback_and_failure_count_faults(tmp_path: Path) -> None:
    db = tmp_path / "s.db"
    apply_tool_migrations(db, SECURITY_MIGRATIONS_ROOT)
    broken = sqlite3.connect(str(db))
    broken.execute("DROP TABLE tool_registry")
    broken.commit()
    broken.close()
    writer = _ToolWriter(database_path=db)
    with pytest.raises(ToolError) as exc:
        writer.rollback_operation(
            tool_id="t", version="1", op_key="k", verb="register", failure_code="F", ts=1
        )
    assert exc.value.code == "TOOL_ROLLBACK_FAILED"
    with pytest.raises(ToolError) as exc2:
        writer.increment_failure(tool_id="t", version="1", ts=1)
    assert exc2.value.code == "TOOL_FAILURE_COUNT_FAILED"
