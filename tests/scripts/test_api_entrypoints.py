"""Phase 2B, Finding 3 — schema setup is separated from read-only API serving.

``scripts/run_api.py`` must never call ``apply_migrations`` or open a writable database
connection; ``scripts/setup_api_database.py`` is the only place migrations are applied.
Both are plain scripts (not part of the ``factory`` package), so they're loaded directly
from their file paths rather than imported as a package module.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

from factory.orchestrator.store.runtime_state import (
    SQLiteOrchestratorStateReader,
    applied_schema_version,
    apply_migrations,
    latest_migration_version,
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


def _v3_only_migrations(tmp_path: Path) -> Path:
    v3_migrations = tmp_path / "migrations_v3"
    v3_migrations.mkdir()
    for filename in ("0001_state.sql", "0002_leases.sql", "0003_memory.sql"):
        (v3_migrations / filename).write_bytes((MIGRATIONS_ROOT / filename).read_bytes())
    return v3_migrations


# ---- run_api.py never touches the writer or the migration applier -----------------------


def test_run_api_never_imports_apply_migrations(run_api: ModuleType) -> None:
    assert not hasattr(run_api, "apply_migrations")


def test_run_api_never_imports_the_writer(run_api: ModuleType) -> None:
    assert not hasattr(run_api, "_OrchestratorStateWriter")


# ---- startup schema check: missing / outdated / current --------------------------------


def test_startup_fails_clearly_when_database_missing(
    run_api: ModuleType, tmp_path: Path
) -> None:
    missing_db = tmp_path / "does-not-exist.db"
    with pytest.raises(SystemExit) as excinfo:
        run_api._require_current_schema(missing_db, MIGRATIONS_ROOT)
    assert "setup_api_database.py" in str(excinfo.value)


def test_startup_fails_clearly_when_schema_outdated(
    run_api: ModuleType, tmp_path: Path
) -> None:
    v3_migrations = _v3_only_migrations(tmp_path)
    db = tmp_path / "runtime.db"
    apply_migrations(db, v3_migrations)  # only through v3 -- 0004 never applied

    with pytest.raises(SystemExit) as excinfo:
        run_api._require_current_schema(db, MIGRATIONS_ROOT)
    message = str(excinfo.value)
    assert "out of date" in message
    assert "setup_api_database.py" in message


def test_startup_passes_when_schema_current(run_api: ModuleType, tmp_path: Path) -> None:
    db = tmp_path / "runtime.db"
    apply_migrations(db, MIGRATIONS_ROOT)
    run_api._require_current_schema(db, MIGRATIONS_ROOT)  # must not raise


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

    with pytest.raises(SystemExit):
        run_api._require_current_schema(db, MIGRATIONS_ROOT)

    # Still at version 3 -- the failed startup check never applied 0004 itself.
    assert applied_schema_version(db) == 3


# ---- main() wires a reader-only app without ever binding a real server ----------------


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


def test_main_exits_before_ever_starting_a_server_when_schema_outdated(
    run_api: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    v3_migrations = _v3_only_migrations(tmp_path)
    db = tmp_path / "runtime.db"
    apply_migrations(db, v3_migrations)

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


# ---- setup_api_database.py is the only place migrations get applied -------------------


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
    assert applied_schema_version(db) == latest_migration_version(MIGRATIONS_ROOT)
    # Queryable through the real read-only reader -- proves it's a real, usable schema.
    reader = SQLiteOrchestratorStateReader(database_path=db)
    assert reader.get_task("nope") is None
