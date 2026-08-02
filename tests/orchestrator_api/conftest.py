"""Shared fixtures for the orchestrator write-authorized API tests (Phase 3A, CMP-ORCH-API)."""

from __future__ import annotations

from pathlib import Path

import pytest
from starlette.applications import Starlette
from starlette.testclient import TestClient

from factory.orchestrator.store.runtime_state import (
    SQLiteOrchestratorStateReader,
    _OrchestratorStateWriter,
    apply_migrations,
)
from factory.orchestrator_api import TaskOperatorService, create_app
from tests.worker_engine.support import loopback_unavailable_reason

MIGRATIONS_ROOT = Path(__file__).resolve().parents[2] / "migrations" / "runtime"


@pytest.fixture(autouse=True)
def _require_loopback_capability(request: pytest.FixtureRequest) -> None:
    if request.node.get_closest_marker("loopback") is None:
        return
    reason = loopback_unavailable_reason()
    if reason is not None:
        pytest.skip(reason)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "runtime.db"
    apply_migrations(path, MIGRATIONS_ROOT)
    return path


@pytest.fixture
def writer(db_path: Path) -> _OrchestratorStateWriter:
    return _OrchestratorStateWriter(database_path=db_path)


@pytest.fixture
def reader(db_path: Path) -> SQLiteOrchestratorStateReader:
    return SQLiteOrchestratorStateReader(database_path=db_path)


@pytest.fixture
def service(
    writer: _OrchestratorStateWriter, reader: SQLiteOrchestratorStateReader
) -> TaskOperatorService:
    return TaskOperatorService(writer=writer, reader=reader)


@pytest.fixture
def app(service: TaskOperatorService) -> Starlette:
    return create_app(service=service)


@pytest.fixture
def client(app: Starlette) -> TestClient:
    return TestClient(app)
