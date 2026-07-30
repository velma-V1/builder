"""RPH3-T5 integration — XSC-RPH3 Class-1 tool registration across security-spine + audit stores."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path

from factory.audit import AuditValidator, AuditWriter, RecordKind
from factory.tools import CommitState, ToolDeclaration, ToolRegistry

RegisterTool = Callable[..., ToolDeclaration]


def test_class1_register_one_record_one_completion_joined(
    registry: ToolRegistry, audit_db_path: Path, security_db_path: Path, register_tool: RegisterTool
) -> None:
    register_tool()
    record = registry.reader.get_record("formatter", "1.0")
    assert record is not None and record.commit_state is CommitState.COMMITTED

    audit_records = AuditWriter(database_path=audit_db_path).export()
    completions = {r.op_key: r for r in audit_records if r.record_kind is RecordKind.COMPLETION}

    connection = sqlite3.connect(str(security_db_path))
    try:
        rows = [
            (str(r[0]), str(r[1]), int(r[2]))
            for r in connection.execute(
                "SELECT op_key, status, audit_seq FROM tool_registry_intents"
            )
        ]
    finally:
        connection.close()
    assert len(rows) == 1
    op_key, status, audit_seq = rows[0]
    assert status == "COMMITTED"
    assert op_key in completions and completions[op_key].sequence == audit_seq
    assert AuditValidator(database_path=audit_db_path).verify_chain().valid is True


def test_full_lifecycle_chain_valid(
    registry: ToolRegistry, audit_db_path: Path, register_tool: RegisterTool
) -> None:
    register_tool()
    registry.quarantine("formatter", "1.0", "unsafe")
    registry.release("formatter", "1.0", "review-1")
    assert registry.reader.list_pending_intents() == ()
    assert AuditValidator(database_path=audit_db_path).verify_chain().valid is True
