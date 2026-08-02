"""Phase 3A — migration 0005 (task_requests), genuine v4->v5 upgrade + idempotent submission.

Mirrors the rigor established for the v3->v4 test: a real database that only has 0001-0004
applied (not a fixture that saw 0001-0005 applied together), a real pre-existing task row,
upgraded in place via the real migration manager, then real writer calls against the upgraded
schema. project_id/workstream_id remain distinct identities throughout (01L) -- unaffected by
this migration.
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

_FROZEN_MIGRATIONS_0001_TO_0004 = {
    "0001_state.sql": "2fd4ecda34c05265be99de9c8aa36518cc9ac540c4038286c5da9cfb1fbd5f4c",
    "0002_leases.sql": "a3a143e4b225655b68aadb5bc677acae7a99cf99b8c047e6c3113deb34b32ba6",
    "0003_memory.sql": "65e0a4d16b84a49b205b1f2e48c91e11ae6dc48e9c179e318da3026283e10587",
    "0004_workstream_membership.sql": (
        "0274e9f2933b543277a4c50e556f8cc87762a69291e6b882d173c89811c4dc5f"
    ),
}


def _query_one_column(db: Path, sql: str) -> set[object]:
    connection = sqlite3.connect(str(db))
    try:
        return {row[0] for row in connection.execute(sql)}
    finally:
        connection.close()


def _table_column_names(db: Path, table: str) -> set[str]:
    connection = sqlite3.connect(str(db))
    try:
        return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
    finally:
        connection.close()


def test_frozen_migrations_0001_through_0004_are_byte_for_byte_unchanged(
    migrations_root: Path,
) -> None:
    for filename, expected_hash in _FROZEN_MIGRATIONS_0001_TO_0004.items():
        content = (migrations_root / filename).read_bytes()
        assert hashlib.sha256(content).hexdigest() == expected_hash, (
            f"{filename} must remain byte-for-byte frozen"
        )


def test_migration_0005_upgrades_a_genuine_v4_database_with_pre_existing_data(
    migrations_root: Path, tmp_path: Path
) -> None:
    # Genuine v4-only migrations dir: none of 0005.
    v4_migrations = tmp_path / "migrations_v4"
    v4_migrations.mkdir()
    for filename in _FROZEN_MIGRATIONS_0001_TO_0004:
        (v4_migrations / filename).write_bytes((migrations_root / filename).read_bytes())

    db = tmp_path / "runtime.db"
    apply_migrations(db, v4_migrations)

    versions_before = _query_one_column(db, "SELECT version FROM schema_migrations")
    assert versions_before == {1, 2, 3, 4}
    assert 5 not in versions_before
    assert "task_requests" not in _query_one_column(
        db, "SELECT name FROM sqlite_master WHERE type='table'"
    )

    # A real pre-existing task row, inserted using the real (pre-3A) writer -- task_requests
    # does not exist in this database yet.
    writer = _OrchestratorStateWriter(database_path=db)
    writer.create_task(
        task_id="PRE-EXISTING", project_id="PROJ-OLD", contract_version=1, workstream_id="ws-1"
    )

    # Real in-place upgrade, through the real migration manager, using a v5-only migrations dir
    # (0001-0005; isolated from whatever migrations_root grows to later).
    v5_migrations = tmp_path / "migrations_v5"
    v5_migrations.mkdir()
    for filename in (*_FROZEN_MIGRATIONS_0001_TO_0004, "0005_task_requests.sql"):
        (v5_migrations / filename).write_bytes((migrations_root / filename).read_bytes())
    apply_migrations(db, v5_migrations)

    assert "task_requests" in _query_one_column(
        db, "SELECT name FROM sqlite_master WHERE type='table'"
    )
    assert _table_column_names(db, "task_requests") == {
        "task_id",
        "project_ref",
        "workstream_id",
        "description",
        "priority",
        "model_preference",
        "expected_result",
        "submitted_by",
        "submitted_at",
        "idempotency_key",
    }

    # Pre-existing task row survived the upgrade untouched.
    reader = SQLiteOrchestratorStateReader(database_path=db)
    record = reader.get_task("PRE-EXISTING")
    assert record is not None
    assert record.project_id == "PROJ-OLD"
    assert record.workstream_id == "ws-1"
    assert reader.get_task_request("PRE-EXISTING") is None  # no request metadata, never invented

    versions_after = _query_one_column(db, "SELECT version FROM schema_migrations")
    assert versions_after == {1, 2, 3, 4, 5}

    # Rerunning the real migration manager (same v5-only dir) is a safe no-op.
    apply_migrations(db, v5_migrations)
    versions_rerun = _query_one_column(db, "SELECT version FROM schema_migrations")
    assert versions_rerun == {1, 2, 3, 4, 5}

    for filename, expected_hash in _FROZEN_MIGRATIONS_0001_TO_0004.items():
        content = (migrations_root / filename).read_bytes()
        assert hashlib.sha256(content).hexdigest() == expected_hash


def test_migration_hash_pin_registered_for_0005(migrations_root: Path) -> None:
    content = (migrations_root / "0005_task_requests.sql").read_bytes()
    actual = hashlib.sha256(content).hexdigest()
    assert runtime_state._EXPECTED_MIGRATION_HASHES["0005_task_requests.sql"] == actual


def test_idempotency_key_has_a_unique_constraint(migrations_root: Path, tmp_path: Path) -> None:
    db = tmp_path / "runtime.db"
    apply_migrations(db, migrations_root)
    writer = _OrchestratorStateWriter(database_path=db)
    writer.submit_task_request(
        project_ref="proj",
        workstream_id="ws-1",
        description="first",
        priority="normal",
        model_preference=None,
        expected_result=None,
        submitted_by="operator",
        idempotency_key="dup-key",
    )
    # A raw INSERT reusing the same idempotency_key must be rejected at the schema level,
    # independent of the writer's own application-level dedup check above.
    connection = sqlite3.connect(str(db))
    try:
        try:
            connection.execute(
                "INSERT INTO task_requests (task_id, project_ref, workstream_id, description, "
                "priority, model_preference, expected_result, submitted_by, submitted_at, "
                "idempotency_key) VALUES "
                "('OTHER-TASK', 'proj', 'ws-1', 'second', 'normal', NULL, NULL, 'operator', "
                "'2026-01-01T00:00:00Z', 'dup-key')"
            )
            raised = False
        except sqlite3.IntegrityError:
            raised = True
    finally:
        connection.close()
    assert raised, "idempotency_key must be UNIQUE at the schema level"
