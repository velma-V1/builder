from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

import factory.watchdog as public_api
from factory.watchdog import SQLiteInterventionReader, WatchdogError, apply_watchdog_migration


def test_migration_creates_only_the_intervention_journal(
    security_db_path: Path,
) -> None:
    connection = sqlite3.connect(security_db_path)
    try:
        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    finally:
        connection.close()
    assert "watchdog_intervention_journal" in tables
    assert "schema_migrations" in tables


def test_migration_hash_is_pinned_and_tampering_fails_closed(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2] / "migrations" / "security"
    copied = tmp_path / "migrations"
    copied.mkdir()
    source = root / "0004_watchdog.sql"
    target = copied / source.name
    target.write_bytes(source.read_bytes() + b"\n-- tampered\n")
    with pytest.raises(WatchdogError, match="MIGRATION_INTEGRITY"):
        apply_watchdog_migration(tmp_path / "tampered.db", copied)


def test_migration_missing_malformed_and_already_applied(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(WatchdogError, match="MIGRATION_MISSING"):
        apply_watchdog_migration(tmp_path / "missing.db", empty)

    malformed = tmp_path / "malformed"
    malformed.mkdir()
    (malformed / "bad.sql").write_text("SELECT 1;")
    with pytest.raises(WatchdogError, match="MIGRATION_MALFORMED"):
        apply_watchdog_migration(tmp_path / "malformed.db", malformed)

    root = Path(__file__).resolve().parents[2] / "migrations" / "security"
    applied = tmp_path / "applied.db"
    apply_watchdog_migration(applied, root)
    apply_watchdog_migration(applied, root)


def test_reader_is_structurally_read_only_and_writer_is_not_exported(
    security_db_path: Path,
) -> None:
    assert not hasattr(public_api, "_InterventionWriter")
    reader = SQLiteInterventionReader(security_db_path)
    assert reader.get("missing") is None
    connection = reader._connect()
    try:
        with pytest.raises(sqlite3.DatabaseError):
            connection.execute(
                "INSERT INTO watchdog_intervention_journal "
                "(op_key, operation_class, domain, target_ref, requested_action, status, "
                "reconciliation_state, request_hash, created_ts, updated_ts) "
                "VALUES ('bad', 1, 'watchdog', 'x', 'x', 'PENDING', 'NONE', 'x', 0, 0)"
            )
    finally:
        connection.close()
