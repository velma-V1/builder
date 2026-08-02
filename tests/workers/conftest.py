"""Shared fixtures + fakes for the Worker Engine (PH-3) test suite.

A ``FakeSpawner`` / ``FakeHandle`` pair lets the pool be exercised deterministically without
forking real OS processes: tests drive ``exit_code`` to simulate a running, exited, or crashed
worker, and record terminate/kill calls to assert shutdown semantics.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from factory.orchestrator.store.runtime_state import (
    SQLiteOrchestratorStateReader,
    _OrchestratorStateWriter,
    apply_migrations,
)
from factory.workers.pool import WorkerPool
from tests.workers.support import FakeSpawner

MIGRATIONS_ROOT = Path(__file__).resolve().parents[2] / "migrations" / "runtime"


@pytest.fixture
def spawner() -> FakeSpawner:
    return FakeSpawner()


@pytest.fixture
def pool(spawner: FakeSpawner) -> WorkerPool:
    return WorkerPool(spawner=spawner, size=4)


@pytest.fixture
def runtime_db(tmp_path: Path) -> Path:
    path = tmp_path / "runtime.db"
    apply_migrations(path, MIGRATIONS_ROOT)
    return path


@pytest.fixture
def writer(runtime_db: Path) -> _OrchestratorStateWriter:
    return _OrchestratorStateWriter(database_path=runtime_db)


@pytest.fixture
def reader(runtime_db: Path) -> SQLiteOrchestratorStateReader:
    return SQLiteOrchestratorStateReader(database_path=runtime_db)
