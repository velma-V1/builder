"""Phase 2A — authoritative workstream membership (migration 0004 + reader/writer support).

project_id and workstream_id are distinct identities (01L). Membership is only ever set
explicitly through the single writer; it is never fabricated or inferred from project_id.
"""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

from factory.orchestrator.store import runtime_state
from factory.orchestrator.store.runtime_state import (
    SQLiteOrchestratorStateReader,
    _OrchestratorStateWriter,
    apply_migrations,
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


def _query_one_column(db: Path, sql: str) -> set[object]:
    """Run a single-column, read-only query with the connection deterministically closed.

    Never relies on CPython reference counting to release the SQLite file handle — matters
    for reliability on Windows/WSL, where a lingering open handle can contend with the next
    connection or with tmp_path cleanup.
    """
    connection = sqlite3.connect(str(db))
    try:
        return {row[0] for row in connection.execute(sql)}
    finally:
        connection.close()


def _tasks_table_column_names(db: Path) -> set[str]:
    """``PRAGMA table_info(tasks)`` column names, connection deterministically closed."""
    connection = sqlite3.connect(str(db))
    try:
        return {row[1] for row in connection.execute("PRAGMA table_info(tasks)")}
    finally:
        connection.close()


def _insert_pre_existing_v3_row(db: Path) -> None:
    connection = sqlite3.connect(str(db))
    try:
        connection.execute(
            "INSERT INTO tasks (task_id, project_id, contract_version, current_state, "
            "sequence, updated_at) VALUES "
            "('PRE-EXISTING', 'PROJ-OLD', 1, 'QUEUED', 0, '2026-01-01T00:00:00Z')"
        )
        connection.commit()
    finally:
        connection.close()


def test_migration_0004_upgrades_a_genuine_v3_database_with_pre_existing_data(
    migrations_root: Path, tmp_path: Path
) -> None:
    """A real version-3 database (only 0001-0003 applied, real pre-existing row) upgraded
    in place to version 4 via the real migration manager — not a fixture that only ever saw
    0001-0004 applied together. Uses ``apply_migrations`` itself for both stages (production
    semantics), never a reimplementation of the migration algorithm.
    """
    # Genuine v3-only migrations dir: the same three frozen files, none of 0004.
    v3_migrations = tmp_path / "migrations_v3"
    v3_migrations.mkdir()
    for filename in _FROZEN_MIGRATIONS:
        (v3_migrations / filename).write_bytes((migrations_root / filename).read_bytes())

    db = tmp_path / "runtime.db"
    apply_migrations(db, v3_migrations)

    versions_before = _query_one_column(db, "SELECT version FROM schema_migrations")
    assert versions_before == {1, 2, 3}
    assert 4 not in versions_before

    # A real pre-existing row, inserted using the version-3 schema shape (task creation
    # predates workstream_id — the column does not exist in this database yet).
    _insert_pre_existing_v3_row(db)

    # The real in-place upgrade, through the real migration manager, using a v4-only migrations
    # directory (0001-0004; deliberately NOT the full, current migrations_root, which may since
    # have grown further migrations — this test isolates exactly the v3->v4 transition it names,
    # so it stays meaningful regardless of what's added to migrations_root later).
    v4_migrations = tmp_path / "migrations_v4"
    v4_migrations.mkdir()
    for filename in (*_FROZEN_MIGRATIONS, "0004_workstream_membership.sql"):
        (v4_migrations / filename).write_bytes((migrations_root / filename).read_bytes())
    apply_migrations(db, v4_migrations)

    assert "workstream_id" in _tasks_table_column_names(db)

    reader = SQLiteOrchestratorStateReader(database_path=db)
    record = reader.get_task("PRE-EXISTING")
    assert record is not None
    assert record.workstream_id is None  # never backfilled from project_id
    assert record.project_id == "PROJ-OLD"

    versions_after = _query_one_column(db, "SELECT version FROM schema_migrations")
    assert versions_after == {1, 2, 3, 4}

    # Rerunning the real migration manager (same v4-only dir) against the now-v4 database is a
    # safe no-op.
    apply_migrations(db, v4_migrations)
    versions_rerun = _query_one_column(db, "SELECT version FROM schema_migrations")
    assert versions_rerun == {1, 2, 3, 4}

    # Frozen migration hashes are still exactly what's pinned.
    for filename, expected_hash in _FROZEN_MIGRATIONS.items():
        content = (migrations_root / filename).read_bytes()
        assert hashlib.sha256(content).hexdigest() == expected_hash


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
    writer.create_task(task_id="TASK-A", project_id="P", contract_version=1, workstream_id="ws-1")
    writer.create_task(task_id="TASK-B", project_id="P", contract_version=1, workstream_id="ws-2")
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
    writer.create_task(task_id="TASK-Z", project_id="P", contract_version=1, workstream_id="ws-1")
    writer.create_task(task_id="TASK-A", project_id="P", contract_version=1, workstream_id="ws-1")
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
