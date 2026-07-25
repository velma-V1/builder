"""Shared fixtures + fakes for the Worker Engine (PH-3) test suite.

A ``FakeSpawner`` / ``FakeHandle`` pair lets the pool be exercised deterministically without
forking real OS processes: tests drive ``exit_code`` to simulate a running, exited, or crashed
worker, and record terminate/kill calls to assert shutdown semantics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from factory.orchestrator.store.runtime_state import apply_migrations
from factory.workers.pool import WorkerPool
from factory.workers.process import ProcessHandle

MIGRATIONS_ROOT = Path(__file__).resolve().parents[2] / "migrations" / "runtime"


@dataclass(slots=True)
class FakeHandle:
    """Deterministic ProcessHandle. ``exit_code`` None = still running."""

    pid: int
    exit_code: int | None = None
    terminated: bool = False
    killed: bool = False

    def poll(self) -> int | None:
        return self.exit_code

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True

    def crash(self, exit_code: int = 137) -> None:
        """Simulate the process exiting unexpectedly."""
        self.exit_code = exit_code


@dataclass(slots=True)
class FakeSpawner:
    """Records every spawned handle so tests can drive/inspect them."""

    handles: list[FakeHandle] = field(default_factory=list)
    _next_pid: int = 1000

    def spawn(self, worker_id: str) -> ProcessHandle:
        self._next_pid += 1
        handle = FakeHandle(pid=self._next_pid)
        self.handles.append(handle)
        return handle


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
