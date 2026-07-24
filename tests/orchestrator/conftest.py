"""Shared fixtures for the Orchestrator (PH-2) test suite."""

from __future__ import annotations

from pathlib import Path

import pytest

from factory.orchestrator.store.runtime_state import (
    SQLiteOrchestratorStateReader,
    _OrchestratorStateWriter,
    apply_migrations,
)

MIGRATIONS_ROOT = Path(__file__).resolve().parents[2] / "migrations" / "runtime"


@pytest.fixture
def migrations_root() -> Path:
    return MIGRATIONS_ROOT


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
