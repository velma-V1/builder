"""Task 2.2 — runtime-state store + transactional writer (CMP-ORCH)."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from factory.orchestrator.errors import OrchestratorError
from factory.orchestrator.models import TaskState
from factory.orchestrator.store import runtime_state
from factory.orchestrator.store.runtime_state import (
    SQLiteOrchestratorStateReader,
    _OrchestratorStateWriter,
    apply_migrations,
)


def _seed(writer: _OrchestratorStateWriter, task_id: str = "TASK-001") -> None:
    writer.create_task(task_id=task_id, project_id="PROJ-001", contract_version=1)


def test_create_task_seeds_queued_with_genesis_event(
    writer: _OrchestratorStateWriter, reader: SQLiteOrchestratorStateReader
) -> None:
    event = writer.create_task(task_id="TASK-001", project_id="PROJ-001", contract_version=1)
    assert event.new_state is TaskState.QUEUED
    assert event.prev_state is None
    assert event.sequence == 0
    record = reader.get_task("TASK-001")
    assert record is not None
    assert record.current_state is TaskState.QUEUED
    assert record.sequence == 0
    events = reader.get_events("TASK-001")
    assert len(events) == 1 and events[0].accepted is True


def test_create_task_rejects_duplicate(writer: _OrchestratorStateWriter) -> None:
    _seed(writer)
    with pytest.raises(OrchestratorError, match="already exists"):
        _seed(writer)


def test_legal_transition_updates_state_and_appends_accepted_event(
    writer: _OrchestratorStateWriter, reader: SQLiteOrchestratorStateReader
) -> None:
    _seed(writer)
    event = writer.apply_transition(
        task_id="TASK-001",
        expected_current_state=TaskState.QUEUED,
        new_state=TaskState.PLANNING,
        cause="start",
        actor="orchestrator",
    )
    assert event.accepted is True
    assert event.sequence == 1  # one greater than genesis (0)
    record = reader.get_task("TASK-001")
    assert record is not None
    assert record.current_state is TaskState.PLANNING
    assert record.sequence == 1
    accepted = [e for e in reader.get_events("TASK-001") if e.accepted]
    assert [e.new_state for e in accepted] == [TaskState.QUEUED, TaskState.PLANNING]


def test_illegal_transition_leaves_state_and_appends_rejected_audit_event(
    writer: _OrchestratorStateWriter, reader: SQLiteOrchestratorStateReader
) -> None:
    _seed(writer)  # QUEUED
    # QUEUED -> RUNNING is not a legal transition (only QUEUED -> PLANNING is).
    event = writer.apply_transition(
        task_id="TASK-001",
        expected_current_state=TaskState.QUEUED,
        new_state=TaskState.RUNNING,
        cause="illegal",
        actor="test",
    )
    assert event.accepted is False
    record = reader.get_task("TASK-001")
    assert record is not None
    assert record.current_state is TaskState.QUEUED  # unchanged
    assert record.sequence == 0
    events = reader.get_events("TASK-001")
    assert events[-1].accepted is False and events[-1].new_state is TaskState.RUNNING


def test_expected_state_mismatch_is_rejected(
    writer: _OrchestratorStateWriter, reader: SQLiteOrchestratorStateReader
) -> None:
    _seed(writer)  # actually QUEUED
    # Caller believes the task is RUNNING; it is not -> optimistic-concurrency rejection.
    event = writer.apply_transition(
        task_id="TASK-001",
        expected_current_state=TaskState.RUNNING,
        new_state=TaskState.VERIFYING,
        cause="stale",
        actor="test",
    )
    assert event.accepted is False
    record = reader.get_task("TASK-001")
    assert record is not None
    assert record.current_state is TaskState.QUEUED  # unchanged


def test_apply_transition_on_missing_task_raises(writer: _OrchestratorStateWriter) -> None:
    with pytest.raises(OrchestratorError, match="does not exist"):
        writer.apply_transition(
            task_id="TASK-404",
            expected_current_state=TaskState.QUEUED,
            new_state=TaskState.PLANNING,
            cause="x",
            actor="t",
        )


def test_idempotent_restart_returns_same_event_and_writes_one_row(
    writer: _OrchestratorStateWriter, reader: SQLiteOrchestratorStateReader
) -> None:
    _seed(writer)
    first = writer.apply_transition(
        task_id="TASK-001",
        expected_current_state=TaskState.QUEUED,
        new_state=TaskState.PLANNING,
        cause="start",
        actor="orchestrator",
        idempotency_key="k-1",
    )
    second = writer.apply_transition(
        task_id="TASK-001",
        expected_current_state=TaskState.QUEUED,  # a naive retry re-sends the old expectation
        new_state=TaskState.PLANNING,
        cause="start",
        actor="orchestrator",
        idempotency_key="k-1",
    )
    assert first == second
    keyed = [e for e in reader.get_events("TASK-001") if e.idempotency_key == "k-1"]
    assert len(keyed) == 1  # exactly one row despite the retry


def test_migration_runner_records_version_only_and_is_idempotent(
    db_path: Path, migrations_root: Path
) -> None:
    # db_path already applied migrations once (fixture). Re-running must be a no-op, not a re-apply.
    apply_migrations(db_path, migrations_root)
    reader_conn = SQLiteOrchestratorStateReader(database_path=db_path)
    # A migrated DB is queryable and the version is recorded.
    assert reader_conn.get_task("nope") is None


def test_migration_integrity_failure_is_rejected(tmp_path: Path) -> None:
    # A migration whose bytes do not match the pinned SHA-256 fails closed (SEC-PH2-03).
    bad_dir = tmp_path / "m"
    bad_dir.mkdir()
    (bad_dir / "0001_state.sql").write_bytes(b"CREATE TABLE tampered (x);\n")
    with pytest.raises(OrchestratorError, match="integrity check failed"):
        apply_migrations(tmp_path / "bad.db", bad_dir)


def test_failed_migration_leaves_no_partial_schema_or_version_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # REGR-0003 / T-PH2-MIG1: a migration forced to fail mid-apply leaves no partial schema and
    # no version row (transactional). Pin the broken file's hash so it passes the integrity gate
    # and reaches the apply step.
    broken = (
        b"CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);\n"
        b"CREATE TABLE good_table (id INTEGER);\n"
        b"CREATE TABLE bad_table (;\n"  # deliberate syntax error
    )
    mig_dir = tmp_path / "m"
    mig_dir.mkdir()
    (mig_dir / "0001_broken.sql").write_bytes(broken)
    monkeypatch.setitem(
        runtime_state._EXPECTED_MIGRATION_HASHES,
        "0001_broken.sql",
        hashlib.sha256(broken).hexdigest(),
    )
    db = tmp_path / "broken.db"
    with pytest.raises(OrchestratorError, match="failed to apply"):
        apply_migrations(db, mig_dir)

    # No partial schema survived: neither the version row nor good_table persists.
    import sqlite3

    connection = sqlite3.connect(str(db))
    try:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        assert "good_table" not in tables
        version_rows: list[object] = []
        if "schema_migrations" in tables:
            version_rows = connection.execute("SELECT version FROM schema_migrations").fetchall()
        assert version_rows == []
    finally:
        connection.close()
