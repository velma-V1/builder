"""Shared fixtures for CMP-WATCH and its internal Watchdog Intervention Receiver."""

from __future__ import annotations

from pathlib import Path

import pytest

from factory.audit import apply_audit_migrations
from factory.orchestrator.store.runtime_state import (
    SQLiteOrchestratorStateReader,
    _OrchestratorStateWriter,
    apply_migrations,
)
from factory.watchdog import apply_watchdog_migration

ROOT = Path(__file__).resolve().parents[2]
SECURITY_MIGRATIONS = ROOT / "migrations" / "security"
AUDIT_MIGRATIONS = ROOT / "migrations" / "audit"
RUNTIME_MIGRATIONS = ROOT / "migrations" / "runtime"
AUTH_PROOF = "test-watchdog-token"


class FakeClock:
    def __init__(self, start: int = 1_000_000) -> None:
        self.wall = start
        self.mono = float(start)

    def now_ts(self) -> int:
        return self.wall

    def now_iso(self) -> str:
        return f"2026-07-30T00:00:{self.wall % 60:02d}Z"

    def monotonic(self) -> float:
        return self.mono

    def advance(self, seconds: int, *, wall_seconds: int | None = None) -> None:
        self.mono += seconds
        self.wall += seconds if wall_seconds is None else wall_seconds


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def security_db_path(tmp_path: Path) -> Path:
    path = tmp_path / "security.db"
    apply_watchdog_migration(path, SECURITY_MIGRATIONS)
    return path


@pytest.fixture
def audit_db_path(tmp_path: Path) -> Path:
    path = tmp_path / "audit.db"
    apply_audit_migrations(path, AUDIT_MIGRATIONS)
    return path


@pytest.fixture
def runtime_db_path(tmp_path: Path) -> Path:
    path = tmp_path / "runtime.db"
    apply_migrations(path, RUNTIME_MIGRATIONS)
    return path


@pytest.fixture
def task_writer(runtime_db_path: Path) -> _OrchestratorStateWriter:
    return _OrchestratorStateWriter(runtime_db_path)


@pytest.fixture
def task_reader(runtime_db_path: Path) -> SQLiteOrchestratorStateReader:
    return SQLiteOrchestratorStateReader(runtime_db_path)
