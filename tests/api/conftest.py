"""Shared fixtures for the read-only task-snapshot API tests (Phase 2B, CMP-API)."""

from __future__ import annotations

from pathlib import Path

import pytest
from starlette.applications import Starlette
from starlette.testclient import TestClient

from factory.api import create_app
from factory.orchestrator.store.runtime_state import (
    SQLiteOrchestratorStateReader,
    _OrchestratorStateWriter,
    apply_migrations,
)

MIGRATIONS_ROOT = Path(__file__).resolve().parents[2] / "migrations" / "runtime"


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
def app(reader: SQLiteOrchestratorStateReader) -> Starlette:
    return create_app(task_reader=reader)


@pytest.fixture
def client(app: Starlette) -> TestClient:
    return TestClient(app)
