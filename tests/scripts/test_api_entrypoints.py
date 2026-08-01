"""Phase 2B, Findings 1-3 (re-review round 2) — schema setup is separated from read-only API
serving, and startup validates the COMPLETE applied migration-version set against the
complete expected set, not just a maximum.

``scripts/run_api.py`` must never call ``apply_migrations`` or open a writable database
connection; ``scripts/setup_api_database.py`` is the only place migrations are applied.
Both are plain scripts (not part of the ``factory`` package), so they're loaded directly
from their file paths rather than imported as a package module.
"""

from __future__ import annotations

import importlib.util
import sqlite3
import sys
from pathlib import Path
from types import ModuleType

import pytest

from factory.orchestrator.store.runtime_state import (
    SQLiteOrchestratorStateReader,
    applied_migration_versions,
    apply_migrations,
    expected_migration_versions,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_ROOT = _REPO_ROOT / "migrations" / "runtime"


def _load_script(name: str) -> ModuleType:
    path = _REPO_ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def run_api() -> ModuleType:
    return _load_script("run_api")


@pytest.fixture
def setup_api_database() -> ModuleType:
    return _load_script("setup_api_database")


def _migrations_subset(tmp_path: Path, *filenames: str) -> Path:
    subset = tmp_path / f"migrations_{'_'.join(f[:4] for f in filenames)}"
    subset.mkdir()
    for filename in filenames:
        (subset / filename).write_bytes((MIGRATIONS_ROOT / filename).read_bytes())
    return subset


def _v3_only_migrations(tmp_path: Path) -> Path:
    return _migrations_subset(
        tmp_path, "0001_state.sql", "0002_leases.sql", "0003_memory.sql"
    )


def _gapped_1_2_4_migrations(tmp_path: Path) -> Path:
    """A migrations directory missing 0003 entirely -- {1, 2, 4} once applied."""
    return _migrations_subset(
        tmp_path, "0001_state.sql", "0002_leases.sql", "0004_workstream_membership.sql"
    )


def _db_with_recorded_versions(tmp_path: Path, *versions: int) -> Path:
    """A fully-migrated (1,2,3,4) database with extra version rows appended directly via raw
    SQL, simulating an unexpected/future applied migration this codebase doesn't recognize
    (e.g. version 5) -- without needing a real, hash-pinned 0005 migration file to exist."""
    db = tmp_path / "runtime.db"
    apply_migrations(db, MIGRATIONS_ROOT)
    connection = sqlite3.connect(str(db))
    try:
        for version in versions:
            connection.execute(
                "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                (version, "2026-01-01T00:00:00Z"),
            )
        connection.commit()
    finally:
        connection.close()
    return db


def _empty_sqlite_file(tmp_path: Path) -> Path:
    """An existing, valid, but completely unmigrated SQLite file (no schema_migrations table)."""
    db = tmp_path / "empty.db"
    connection = sqlite3.connect(str(db))
    connection.close()
    return db


# ---- run_api.py never touches the writer or the migration applier -----------------------


def test_run_api_never_imports_apply_migrations(run_api: ModuleType) -> None:
    assert not hasattr(run_api, "apply_migrations")


def test_run_api_never_imports_the_writer(run_api: ModuleType) -> None:
    assert not hasattr(run_api, "_OrchestratorStateWriter")


# ---- expected_migration_versions / applied_migration_versions: full-set semantics --------


def test_expected_versions_are_the_complete_ascending_set() -> None:
    assert expected_migration_versions(MIGRATIONS_ROOT) == (1, 2, 3, 4)


def test_gapped_history_does_not_equal_expected(tmp_path: Path) -> None:
    gapped = _gapped_1_2_4_migrations(tmp_path)
    db = tmp_path / "runtime.db"
    apply_migrations(db, gapped)

    assert applied_migration_versions(db) == (1, 2, 4)
    assert applied_migration_versions(db) != expected_migration_versions(MIGRATIONS_ROOT)


def test_future_version_history_does_not_equal_expected(tmp_path: Path) -> None:
    db = _db_with_recorded_versions(tmp_path, 5)
    assert applied_migration_versions(db) == (1, 2, 3, 4, 5)
    assert applied_migration_versions(db) != expected_migration_versions(MIGRATIONS_ROOT)


def test_complete_history_equals_expected(tmp_path: Path) -> None:
    db = tmp_path / "runtime.db"
    apply_migrations(db, MIGRATIONS_ROOT)
    assert applied_migration_versions(db) == expected_migration_versions(MIGRATIONS_ROOT)


# ---- startup schema check: gapped / future / current / missing-table / missing-file ------


def test_startup_rejects_gapped_history_1_2_4(run_api: ModuleType, tmp_path: Path) -> None:
    gapped = _gapped_1_2_4_migrations(tmp_path)
    db = tmp_path / "runtime.db"
    apply_migrations(db, gapped)

    with pytest.raises(SystemExit) as excinfo:
        run_api._require_current_schema(db, MIGRATIONS_ROOT)
    message = str(excinfo.value)
    assert "does not match" in message
    assert "1,2,4" in message
    assert "1,2,3,4" in message
    assert "setup_api_database.py" in message


def test_startup_rejects_unexpected_future_version_1_2_3_4_5(
    run_api: ModuleType, tmp_path: Path
) -> None:
    db = _db_with_recorded_versions(tmp_path, 5)

    with pytest.raises(SystemExit) as excinfo:
        run_api._require_current_schema(db, MIGRATIONS_ROOT)
    message = str(excinfo.value)
    assert "does not match" in message
    assert "1,2,3,4,5" in message
    assert "setup_api_database.py" in message


def test_startup_accepts_complete_history_1_2_3_4(run_api: ModuleType, tmp_path: Path) -> None:
    db = tmp_path / "runtime.db"
    apply_migrations(db, MIGRATIONS_ROOT)
    run_api._require_current_schema(db, MIGRATIONS_ROOT)  # must not raise


def test_startup_rejects_existing_database_with_no_migration_table(
    run_api: ModuleType, tmp_path: Path
) -> None:
    db = _empty_sqlite_file(tmp_path)

    with pytest.raises(SystemExit) as excinfo:
        run_api._require_current_schema(db, MIGRATIONS_ROOT)
    message = str(excinfo.value)
    assert "does not match" in message
    assert "(none)" in message
    assert "1,2,3,4" in message


def test_startup_fails_clearly_when_database_missing(
    run_api: ModuleType, tmp_path: Path
) -> None:
    missing_db = tmp_path / "does-not-exist.db"
    with pytest.raises(SystemExit) as excinfo:
        run_api._require_current_schema(missing_db, MIGRATIONS_ROOT)
    assert "setup_api_database.py" in str(excinfo.value)


def test_startup_fails_clearly_on_malformed_migration_filename(
    run_api: ModuleType, tmp_path: Path
) -> None:
    clean_dir = tmp_path / "clean"
    clean_dir.mkdir()
    db = tmp_path / "runtime.db"
    apply_migrations(db, _v3_only_migrations(clean_dir))  # a real, valid v3 db, separate dir

    bad_migrations = _v3_only_migrations(tmp_path)
    (bad_migrations / "corrupted.sql").write_text("SELECT 1;")

    with pytest.raises(SystemExit) as excinfo:
        run_api._require_current_schema(db, bad_migrations)
    message = str(excinfo.value)
    assert "invalid" in message.lower()
    assert "corrupted.sql" in message
    # Never leaks a raw traceback -- the message is our own bounded text.
    assert "Traceback" not in message


# ---- the schema check never mutates anything, regardless of outcome ---------------------


def test_startup_check_does_not_mutate_the_database(
    run_api: ModuleType, tmp_path: Path
) -> None:
    db = tmp_path / "runtime.db"
    apply_migrations(db, MIGRATIONS_ROOT)
    before = db.read_bytes()

    run_api._require_current_schema(db, MIGRATIONS_ROOT)

    assert db.read_bytes() == before


def test_startup_check_does_not_add_missing_migrations(
    run_api: ModuleType, tmp_path: Path
) -> None:
    v3_migrations = _v3_only_migrations(tmp_path)
    db = tmp_path / "runtime.db"
    apply_migrations(db, v3_migrations)
    before = db.read_bytes()

    with pytest.raises(SystemExit):
        run_api._require_current_schema(db, MIGRATIONS_ROOT)

    # Byte-for-byte unchanged -- the failed startup check never applied anything itself.
    assert db.read_bytes() == before
    assert applied_migration_versions(db) == (1, 2, 3)


def test_gapped_database_is_unchanged_after_refused_startup(
    run_api: ModuleType, tmp_path: Path
) -> None:
    gapped = _gapped_1_2_4_migrations(tmp_path)
    db = tmp_path / "runtime.db"
    apply_migrations(db, gapped)
    before = db.read_bytes()

    with pytest.raises(SystemExit):
        run_api._require_current_schema(db, MIGRATIONS_ROOT)

    assert db.read_bytes() == before
    assert applied_migration_versions(db) == (1, 2, 4)


# ---- main() wires a reader-only app without ever binding a real server ------------------


def test_main_wires_a_reader_only_app_and_never_starts_a_real_server(
    run_api: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = tmp_path / "runtime.db"
    apply_migrations(db, MIGRATIONS_ROOT)

    captured: dict[str, object] = {}

    def _fake_uvicorn_run(app: object, **kwargs: object) -> None:
        captured["app"] = app

    monkeypatch.setattr(run_api.uvicorn, "run", _fake_uvicorn_run)
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_api.py", "--database-path", str(db), "--migrations-root", str(MIGRATIONS_ROOT)],
    )
    run_api.main()

    app = captured["app"]
    assert isinstance(app.state.task_reader, SQLiteOrchestratorStateReader)  # type: ignore[attr-defined]
    assert not hasattr(app.state, "task_writer")  # type: ignore[attr-defined]
    assert not hasattr(app.state, "writer")  # type: ignore[attr-defined]


def _v3_only_db(tmp_path: Path) -> Path:
    db = tmp_path / "runtime.db"
    apply_migrations(db, _v3_only_migrations(tmp_path))
    return db


def _gapped_1_2_4_db(tmp_path: Path) -> Path:
    db = tmp_path / "runtime.db"
    apply_migrations(db, _gapped_1_2_4_migrations(tmp_path))
    return db


def _future_version_db(tmp_path: Path) -> Path:
    return _db_with_recorded_versions(tmp_path, 5)


@pytest.mark.parametrize("make_db", [_v3_only_db, _gapped_1_2_4_db, _future_version_db])
def test_main_never_starts_uvicorn_for_any_non_current_schema(
    run_api: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    make_db: object,
) -> None:
    db = make_db(tmp_path)  # type: ignore[operator]

    called = {"run": False}

    def _fake_uvicorn_run(app: object, **kwargs: object) -> None:
        called["run"] = True

    monkeypatch.setattr(run_api.uvicorn, "run", _fake_uvicorn_run)
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_api.py", "--database-path", str(db), "--migrations-root", str(MIGRATIONS_ROOT)],
    )
    with pytest.raises(SystemExit):
        run_api.main()

    assert called["run"] is False


# ---- setup_api_database.py is the only place migrations get applied, and is idempotent --


def test_setup_api_database_applies_migrations_correctly(
    setup_api_database: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = tmp_path / "runtime.db"
    assert not db.exists()

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "setup_api_database.py",
            "--database-path",
            str(db),
            "--migrations-root",
            str(MIGRATIONS_ROOT),
        ],
    )
    setup_api_database.main()

    assert db.exists()
    assert applied_migration_versions(db) == expected_migration_versions(MIGRATIONS_ROOT)
    # Queryable through the real read-only reader -- proves it's a real, usable schema.
    reader = SQLiteOrchestratorStateReader(database_path=db)
    assert reader.get_task("nope") is None


def test_setup_api_database_is_idempotent(
    setup_api_database: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = tmp_path / "runtime.db"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "setup_api_database.py",
            "--database-path",
            str(db),
            "--migrations-root",
            str(MIGRATIONS_ROOT),
        ],
    )
    setup_api_database.main()
    first_versions = applied_migration_versions(db)

    setup_api_database.main()
    second_versions = applied_migration_versions(db)

    assert first_versions == second_versions == expected_migration_versions(MIGRATIONS_ROOT)
