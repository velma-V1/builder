"""Phase 3A — scripts/run_orchestrator.py: reuses the shared schema check, never applies
migrations itself, and only starts Uvicorn once the schema is genuinely current.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

from factory.integrations.migrations import apply_integration_migrations
from factory.orchestrator.store.runtime_state import (
    SQLiteOrchestratorStateReader,
    _OrchestratorStateWriter,
    apply_migrations,
)
from factory.orchestrator_api import TaskOperatorService

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
def run_orchestrator() -> ModuleType:
    return _load_script("run_orchestrator")


def _v3_only_migrations(tmp_path: Path) -> Path:
    subset = tmp_path / "migrations_v3"
    subset.mkdir()
    for filename in ("0001_state.sql", "0002_leases.sql", "0003_memory.sql"):
        (subset / filename).write_bytes((MIGRATIONS_ROOT / filename).read_bytes())
    return subset


def test_run_orchestrator_never_imports_apply_migrations(run_orchestrator: ModuleType) -> None:
    assert not hasattr(run_orchestrator, "apply_migrations")


def test_run_orchestrator_uses_the_shared_schema_check(run_orchestrator: ModuleType) -> None:
    assert run_orchestrator.require_current_schema_or_exit.__module__ == "_schema_check"


def test_main_wires_a_writer_and_reader_backed_service_without_starting_a_real_server(
    run_orchestrator: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = tmp_path / "runtime.db"
    apply_migrations(db, MIGRATIONS_ROOT)

    captured: dict[str, object] = {}

    def _fake_uvicorn_run(app: object, **kwargs: object) -> None:
        captured["app"] = app

    monkeypatch.setattr(run_orchestrator.uvicorn, "run", _fake_uvicorn_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_orchestrator.py",
            "--database-path",
            str(db),
            "--migrations-root",
            str(MIGRATIONS_ROOT),
        ],
    )
    run_orchestrator.main()

    app = captured["app"]
    service = app.state.service  # type: ignore[attr-defined]
    assert isinstance(service, TaskOperatorService)
    assert isinstance(service.writer, _OrchestratorStateWriter)
    assert isinstance(service.reader, SQLiteOrchestratorStateReader)


def test_main_wires_managed_integrations_when_security_runtime_is_enabled(
    run_orchestrator: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = tmp_path / "runtime.db"
    apply_migrations(db, MIGRATIONS_ROOT)
    captured: dict[str, object] = {}
    monkeypatch.setattr(run_orchestrator, "require_current_schema_or_exit", lambda *_args: None)
    monkeypatch.setattr(run_orchestrator, "_build_phase3b", lambda *_args, **_kwargs: (None, None))
    monkeypatch.setattr(
        run_orchestrator.uvicorn,
        "run",
        lambda app, **_kwargs: captured.update(app=app),
    )
    monkeypatch.setenv("BUILDER_OPERATOR_SESSION_TOKEN", "operator-token")
    monkeypatch.setenv("BUILDER_AGENT_ZERO_API_KEY", "agent-token")
    monkeypatch.setenv("BUILDER_MODEL_GATEWAY_TOKEN", "gateway-token")
    apply_integration_migrations(
        tmp_path / "integrations.db", _REPO_ROOT / "migrations" / "integrations"
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_orchestrator.py",
            "--database-path",
            str(db),
            "--security-database-path",
            str(tmp_path / "security.db"),
            "--audit-database-path",
            str(tmp_path / "audit.db"),
            "--integration-state-path",
            str(tmp_path / "integrations.db"),
        ],
    )

    run_orchestrator.main()

    assert captured["app"].state.integration_control is not None  # type: ignore[attr-defined]


def test_main_exits_before_starting_uvicorn_when_schema_is_outdated(
    run_orchestrator: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = tmp_path / "runtime.db"
    apply_migrations(db, _v3_only_migrations(tmp_path))  # only 0001-0003, not current

    called = {"run": False}

    def _fake_uvicorn_run(app: object, **kwargs: object) -> None:
        called["run"] = True

    monkeypatch.setattr(run_orchestrator.uvicorn, "run", _fake_uvicorn_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_orchestrator.py",
            "--database-path",
            str(db),
            "--migrations-root",
            str(MIGRATIONS_ROOT),
        ],
    )
    with pytest.raises(SystemExit):
        run_orchestrator.main()

    assert called["run"] is False


def test_main_exits_before_starting_uvicorn_when_database_missing(
    run_orchestrator: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing_db = tmp_path / "does-not-exist.db"

    called = {"run": False}

    def _fake_uvicorn_run(app: object, **kwargs: object) -> None:
        called["run"] = True

    monkeypatch.setattr(run_orchestrator.uvicorn, "run", _fake_uvicorn_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_orchestrator.py",
            "--database-path",
            str(missing_db),
            "--migrations-root",
            str(MIGRATIONS_ROOT),
        ],
    )
    with pytest.raises(SystemExit):
        run_orchestrator.main()

    assert called["run"] is False
    assert not missing_db.exists()  # never created a database itself
