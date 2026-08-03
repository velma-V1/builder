"""Stage-3 — durable schema pinning + idempotency/replay/crash/stale/recovery semantics.

The behaviour tests apply the *template* schema to a throwaway temp database purely to prove its
idempotency/replay/recovery semantics. This is a test fixture, not activation of a durable store:
no live database is created and the SQLite compliance gate still governs real activation.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from factory.livegate.durable_schema import (
    DURABLE_SCHEMA_DIR,
    DURABLE_SCHEMA_MANIFEST,
    validate_manifest,
)

ROOT = Path(__file__).resolve().parents[2]
_SCHEMA_SQL = (ROOT / DURABLE_SCHEMA_DIR / "0001_execution_journal.sql").read_text(encoding="utf-8")


def test_manifest_matches_shipped_files() -> None:
    assert validate_manifest(ROOT) == ()


def test_manifest_detects_tamper(tmp_path: Path) -> None:
    schema_dir = tmp_path / DURABLE_SCHEMA_DIR
    schema_dir.mkdir(parents=True)
    (schema_dir / DURABLE_SCHEMA_MANIFEST[0].filename).write_text("-- tampered\n", encoding="utf-8")
    problems = validate_manifest(tmp_path)
    assert any("hash mismatch" in p for p in problems)


def test_manifest_detects_undeclared(tmp_path: Path) -> None:
    schema_dir = tmp_path / DURABLE_SCHEMA_DIR
    schema_dir.mkdir(parents=True)
    for pin in DURABLE_SCHEMA_MANIFEST:  # copy the real (matching) files first
        (schema_dir / pin.filename).write_text(_SCHEMA_SQL, encoding="utf-8")
    (schema_dir / "0002_rogue.sql").write_text("SELECT 1;\n", encoding="utf-8")
    assert any("undeclared" in p for p in validate_manifest(tmp_path))


@pytest.fixture
def journal(tmp_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(tmp_path / "journal.db"), isolation_level=None)
    conn.executescript(_SCHEMA_SQL)
    return conn


def _insert(conn: sqlite3.Connection, task: str, seq: int, status: str, epoch: int = 0) -> None:
    conn.execute(
        "INSERT INTO execution_journal "
        "(task_id, attempt_seq, route_key, status, process_epoch, created_at_ms, updated_at_ms) "
        "VALUES (?, ?, 'OLLAMA:qwen3:8b', ?, ?, 1, 1) "
        "ON CONFLICT(task_id, attempt_seq) DO NOTHING",
        (task, seq, status, epoch),
    )


def test_idempotent_write_is_a_noop(journal: sqlite3.Connection) -> None:
    _insert(journal, "T1", 1, "RUNNING")
    _insert(journal, "T1", 1, "RUNNING")  # replayed write
    (count,) = journal.execute(
        "SELECT COUNT(*) FROM execution_journal WHERE task_id='T1'"
    ).fetchone()
    assert count == 1


def test_replay_after_terminal_finds_nothing_to_rerun(journal: sqlite3.Connection) -> None:
    _insert(journal, "T1", 1, "SUCCEEDED")
    non_terminal = journal.execute(
        "SELECT COUNT(*) FROM execution_journal WHERE status IN ('RUNNING')"
    ).fetchone()[0]
    assert non_terminal == 0


def test_crash_recovery_marks_stale(journal: sqlite3.Connection) -> None:
    _insert(journal, "T1", 1, "RUNNING", epoch=7)  # crashed mid-flight under epoch 7
    # Restart under a new epoch: recovery query finds the orphaned RUNNING row.
    orphans = journal.execute(
        "SELECT task_id, attempt_seq FROM execution_journal "
        "WHERE status='RUNNING' AND process_epoch != ?",
        (8,),
    ).fetchall()
    assert orphans == [("T1", 1)]
    journal.execute(
        "UPDATE execution_journal SET status='STALE', updated_at_ms=2 "
        "WHERE status='RUNNING' AND process_epoch != ?",
        (8,),
    )
    remaining = journal.execute(
        "SELECT COUNT(*) FROM execution_journal WHERE status='RUNNING'"
    ).fetchone()[0]
    assert remaining == 0


def test_status_check_constraint_rejects_bad_status(journal: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        journal.execute(
            "INSERT INTO execution_journal "
            "(task_id, attempt_seq, route_key, status, created_at_ms, updated_at_ms) "
            "VALUES ('T2', 1, 'r', 'BOGUS', 1, 1)"
        )
