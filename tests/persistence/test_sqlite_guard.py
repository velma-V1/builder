"""Stage-1 hardening — SQLite engine guard (version floor, hardened connect, busy retry)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from factory.persistence import (
    MIN_SQLITE_VERSION,
    PersistenceError,
    assert_sqlite_supported,
    classify_operational_error,
    connect,
    run_with_busy_retry,
    running_sqlite_version,
)


def test_running_version_is_a_three_tuple() -> None:
    version = running_sqlite_version()
    assert len(version) == 3
    assert all(isinstance(p, int) for p in version)


def test_version_at_or_above_floor_is_supported() -> None:
    assert assert_sqlite_supported(version=(3, 51, 3)) == (3, 51, 3)
    assert assert_sqlite_supported(version=(3, 52, 0)) == (3, 52, 0)


def test_older_version_is_rejected() -> None:
    with pytest.raises(PersistenceError) as exc:
        assert_sqlite_supported(version=(3, 50, 4))
    assert exc.value.code == "SQLITE_ENGINE_UNSUPPORTED"


def test_approved_backport_is_accepted() -> None:
    # An explicitly approved fixed backport is accepted even below the floor — never silently.
    assert assert_sqlite_supported(
        version=(3, 50, 4), approved_backports=frozenset({(3, 50, 4)})
    ) == (3, 50, 4)
    assert MIN_SQLITE_VERSION == (3, 51, 3)


def test_hardened_connection_sets_pragmas(tmp_path: Path) -> None:
    conn = connect(tmp_path / "db.sqlite", busy_timeout_ms=3000)
    try:
        assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == 3000
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
    finally:
        conn.close()


def test_connect_rejects_nonpositive_busy_timeout(tmp_path: Path) -> None:
    with pytest.raises(PersistenceError) as exc:
        connect(tmp_path / "db.sqlite", busy_timeout_ms=0)
    assert exc.value.code == "BUSY_TIMEOUT_INVALID"


def test_classify_operational_error() -> None:
    busy = classify_operational_error(sqlite3.OperationalError("database is locked"))
    other = classify_operational_error(sqlite3.OperationalError("no such table: x"))
    assert busy == "SQLITE_BUSY"
    assert other == "OTHER"


def test_connect_without_wal(tmp_path: Path) -> None:
    conn = connect(tmp_path / "db.sqlite", wal=False)
    try:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() != "wal"
    finally:
        conn.close()


def test_busy_retry_succeeds_first_try() -> None:
    assert run_with_busy_retry(lambda: 42, sleep=lambda _s: None) == 42


def test_busy_retry_recovers_after_transient_lock() -> None:
    calls = {"n": 0}

    def flaky() -> str:
        calls["n"] += 1
        if calls["n"] == 1:
            raise sqlite3.OperationalError("database is locked")
        return "ok"

    assert run_with_busy_retry(flaky, retries=3, sleep=lambda _s: None) == "ok"
    assert calls["n"] == 2


def test_busy_retry_exhausts_and_fails_closed() -> None:
    def always_locked() -> None:
        raise sqlite3.OperationalError("database is locked")

    with pytest.raises(PersistenceError) as exc:
        run_with_busy_retry(always_locked, retries=2, sleep=lambda _s: None)
    assert exc.value.code == "SQLITE_BUSY_EXHAUSTED"


def test_busy_retry_reraises_non_busy_error() -> None:
    def bad_sql() -> None:
        raise sqlite3.OperationalError("no such table: t")

    with pytest.raises(sqlite3.OperationalError):
        run_with_busy_retry(bad_sql, sleep=lambda _s: None)


def test_negative_retries_rejected() -> None:
    with pytest.raises(PersistenceError) as exc:
        run_with_busy_retry(lambda: 1, retries=-1)
    assert exc.value.code == "RETRIES_INVALID"


def test_crash_window_uncommitted_transaction_rolls_back(tmp_path: Path) -> None:
    db = tmp_path / "db.sqlite"
    conn = connect(db)
    conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
    conn.execute("BEGIN")
    conn.execute("INSERT INTO t (id) VALUES (1)")
    conn.close()  # simulated crash before COMMIT

    reopened = connect(db)
    try:
        rows = reopened.execute("SELECT COUNT(*) FROM t").fetchone()[0]
        assert rows == 0  # the uncommitted row did not survive the crash window
    finally:
        reopened.close()


def test_write_contention_is_classified_busy(tmp_path: Path) -> None:
    db = tmp_path / "db.sqlite"
    setup = connect(db)
    setup.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
    setup.close()

    holder = connect(db, busy_timeout_ms=1)
    other = connect(db, busy_timeout_ms=1)
    try:
        holder.execute("BEGIN IMMEDIATE")
        holder.execute("INSERT INTO t (id) VALUES (1)")  # holds the write lock

        def contended_write() -> None:
            other.execute("INSERT INTO t (id) VALUES (2)")

        with pytest.raises(PersistenceError) as exc:
            run_with_busy_retry(contended_write, retries=2, sleep=lambda _s: None)
        assert exc.value.code == "SQLITE_BUSY_EXHAUSTED"
    finally:
        holder.close()
        other.close()


def test_persistence_error_repr() -> None:
    err = PersistenceError("X", "y")
    assert "PersistenceError(code='X'" in repr(err)
    assert str(err) == "X: y"
