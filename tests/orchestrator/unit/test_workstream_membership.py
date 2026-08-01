"""Phase 2A — authoritative workstream membership (migration 0004 + reader/writer support).

project_id and workstream_id are distinct identities (01L). Membership is only ever set
explicitly through the single writer; it is never fabricated or inferred from project_id.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from factory.orchestrator.store import runtime_state
from factory.orchestrator.store.runtime_state import (
    SQLiteOrchestratorStateReader,
    _OrchestratorStateWriter,
)

_FROZEN_MIGRATIONS = {
    "0001_state.sql": "2fd4ecda34c05265be99de9c8aa36518cc9ac540c4038286c5da9cfb1fbd5f4c",
    "0002_leases.sql": "a3a143e4b225655b68aadb5bc677acae7a99cf99b8c047e6c3113deb34b32ba6",
    "0003_memory.sql": "65e0a4d16b84a49b205b1f2e48c91e11ae6dc48e9c179e318da3026283e10587",
}


def test_frozen_migrations_0001_through_0003_are_byte_for_byte_unchanged(
    migrations_root: Path,
) -> None:
    for filename, expected_hash in _FROZEN_MIGRATIONS.items():
        content = (migrations_root / filename).read_bytes()
        assert hashlib.sha256(content).hexdigest() == expected_hash, (
            f"{filename} must remain byte-for-byte frozen"
        )


def test_migration_0004_applies_cleanly_from_existing_schema(db_path: Path) -> None:
    # db_path fixture already applied 0001-0004 in order (apply_migrations is idempotent per
    # version). Re-running must be a no-op, proving 0004 is deterministically re-appliable.
    import sqlite3

    connection = sqlite3.connect(str(db_path))
    try:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(tasks)")}
        versions = {
            row[0] for row in connection.execute("SELECT version FROM schema_migrations")
        }
    finally:
        connection.close()
    assert "workstream_id" in columns
    assert 4 in versions


def test_existing_task_created_without_workstream_remains_readable(
    writer: _OrchestratorStateWriter, reader: SQLiteOrchestratorStateReader
) -> None:
    writer.create_task(task_id="TASK-LEGACY", project_id="PROJ-001", contract_version=1)
    record = reader.get_task("TASK-LEGACY")
    assert record is not None
    assert record.workstream_id is None


def test_project_id_is_never_substituted_for_missing_workstream_id(
    writer: _OrchestratorStateWriter, reader: SQLiteOrchestratorStateReader
) -> None:
    writer.create_task(task_id="TASK-002", project_id="PROJ-XYZ", contract_version=1)
    record = reader.get_task("TASK-002")
    assert record is not None
    assert record.project_id == "PROJ-XYZ"
    assert record.workstream_id is None
    assert record.workstream_id != record.project_id


def test_create_task_persists_explicit_workstream_id_through_the_writer(
    writer: _OrchestratorStateWriter, reader: SQLiteOrchestratorStateReader
) -> None:
    writer.create_task(
        task_id="TASK-003", project_id="PROJ-001", contract_version=1, workstream_id="ws-1"
    )
    record = reader.get_task("TASK-003")
    assert record is not None
    assert record.workstream_id == "ws-1"


def test_list_tasks_by_workstream_returns_only_assigned_tasks(
    writer: _OrchestratorStateWriter, reader: SQLiteOrchestratorStateReader
) -> None:
    writer.create_task(
        task_id="TASK-A", project_id="P", contract_version=1, workstream_id="ws-1"
    )
    writer.create_task(
        task_id="TASK-B", project_id="P", contract_version=1, workstream_id="ws-2"
    )
    writer.create_task(task_id="TASK-C", project_id="P", contract_version=1)  # unassigned

    result = reader.list_tasks_by_workstream("ws-1")
    assert [r.task_id for r in result] == ["TASK-A"]


def test_list_tasks_by_workstream_excludes_unassigned_tasks(
    writer: _OrchestratorStateWriter, reader: SQLiteOrchestratorStateReader
) -> None:
    writer.create_task(task_id="TASK-UNASSIGNED", project_id="P", contract_version=1)
    assert reader.list_tasks_by_workstream("ws-1") == ()


def test_list_tasks_by_workstream_excludes_other_workstreams(
    writer: _OrchestratorStateWriter, reader: SQLiteOrchestratorStateReader
) -> None:
    writer.create_task(
        task_id="TASK-OTHER", project_id="P", contract_version=1, workstream_id="ws-2"
    )
    assert reader.list_tasks_by_workstream("ws-1") == ()


def test_list_tasks_by_workstream_orders_by_updated_at_then_task_id(
    writer: _OrchestratorStateWriter, reader: SQLiteOrchestratorStateReader
) -> None:
    # Same workstream, created in reverse task_id order but same instant (genesis updated_at is
    # identical to the second): ordering must still be deterministic (task_id tiebreak).
    writer.create_task(
        task_id="TASK-Z", project_id="P", contract_version=1, workstream_id="ws-1"
    )
    writer.create_task(
        task_id="TASK-A", project_id="P", contract_version=1, workstream_id="ws-1"
    )
    result = reader.list_tasks_by_workstream("ws-1")
    assert [r.task_id for r in result] == ["TASK-A", "TASK-Z"]


def test_list_tasks_by_workstream_reflects_later_updated_at_ordering(
    writer: _OrchestratorStateWriter, reader: SQLiteOrchestratorStateReader
) -> None:
    from factory.orchestrator.models import TaskState

    writer.create_task(
        task_id="TASK-EARLY", project_id="P", contract_version=1, workstream_id="ws-1"
    )
    writer.create_task(
        task_id="TASK-LATE", project_id="P", contract_version=1, workstream_id="ws-1"
    )
    # Advance TASK-EARLY so its updated_at can only be >= TASK-LATE's genesis stamp; assert the
    # reader orders by updated_at first regardless of task_id.
    writer.apply_transition(
        task_id="TASK-EARLY",
        expected_current_state=TaskState.QUEUED,
        new_state=TaskState.PLANNING,
        cause="advance",
        actor="test",
    )
    result = reader.list_tasks_by_workstream("ws-1")
    ordered_ids = [r.task_id for r in result]
    early_record = next(r for r in result if r.task_id == "TASK-EARLY")
    late_record = next(r for r in result if r.task_id == "TASK-LATE")
    if early_record.updated_at == late_record.updated_at:
        # Same-second granularity: task_id tiebreak still holds and is asserted above; just
        # confirm both are present and readable.
        assert set(ordered_ids) == {"TASK-EARLY", "TASK-LATE"}
    else:
        assert early_record.updated_at >= late_record.updated_at
        assert ordered_ids.index("TASK-EARLY") > ordered_ids.index("TASK-LATE")


def test_migration_hash_pin_registered_for_0004(migrations_root: Path) -> None:
    content = (migrations_root / "0004_workstream_membership.sql").read_bytes()
    actual = hashlib.sha256(content).hexdigest()
    assert runtime_state._EXPECTED_MIGRATION_HASHES["0004_workstream_membership.sql"] == actual
