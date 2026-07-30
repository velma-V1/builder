"""Shared fixtures for the roadmap PH-3 Approval Engine (RPH3-T3) test suite."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from factory.approval import (
    ApprovalEngine,
    ApprovalRequest,
    SQLiteApprovalReader,
    apply_security_migrations,
)
from factory.audit import AuditValidator, apply_audit_migrations

RequestFactory = Callable[..., ApprovalRequest]

_ROOT = Path(__file__).resolve().parents[2]
SECURITY_MIGRATIONS_ROOT = _ROOT / "migrations" / "security"
AUDIT_MIGRATIONS_ROOT = _ROOT / "migrations" / "audit"


class FakeClock:
    """A controllable clock. ``t`` is epoch seconds for expiry; the ISO stamp is derived from it."""

    def __init__(self, start: int = 1_000_000) -> None:
        self.t = start

    def now_ts(self) -> int:
        return self.t

    def now_iso(self) -> str:
        return f"2026-07-26T00:00:{self.t % 60:02d}Z"

    def advance(self, seconds: int) -> None:
        self.t += seconds


@pytest.fixture
def security_migrations_root() -> Path:
    return SECURITY_MIGRATIONS_ROOT


@pytest.fixture
def security_db_path(tmp_path: Path) -> Path:
    path = tmp_path / "security.db"
    apply_security_migrations(path, SECURITY_MIGRATIONS_ROOT)
    return path


@pytest.fixture
def audit_db_path(tmp_path: Path) -> Path:
    path = tmp_path / "audit.db"
    apply_audit_migrations(path, AUDIT_MIGRATIONS_ROOT)
    return path


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def engine(security_db_path: Path, audit_db_path: Path, clock: FakeClock) -> ApprovalEngine:
    return ApprovalEngine(
        security_database_path=security_db_path,
        audit_database_path=audit_db_path,
        clock=clock,
    )


@pytest.fixture
def reader(security_db_path: Path) -> SQLiteApprovalReader:
    return SQLiteApprovalReader(database_path=security_db_path)


@pytest.fixture
def audit_validator(audit_db_path: Path) -> AuditValidator:
    return AuditValidator(database_path=audit_db_path)


def _make_request(
    *,
    task_id: str = "task-1",
    tool: str = "shell",
    action: str = "write_file",
    scope: str = "repo/src",
    purpose: str = "apply an approved edit",
    consequences: str = "modifies a tracked file",
    autonomy_level: str = "L2-supervised",
    ttl_seconds: int = 3600,
    resource: str | None = "repo/src/main.py",
    repetition_limit: int = 1,
    actor: str = "cmp-perm",
    security_violation: bool = False,
    destructive: bool = False,
) -> ApprovalRequest:
    return ApprovalRequest(
        task_id=task_id,
        tool=tool,
        action=action,
        scope=scope,
        purpose=purpose,
        consequences=consequences,
        autonomy_level=autonomy_level,
        ttl_seconds=ttl_seconds,
        resource=resource,
        repetition_limit=repetition_limit,
        actor=actor,
        security_violation=security_violation,
        destructive=destructive,
    )


@pytest.fixture
def make_request() -> RequestFactory:
    """Factory fixture for building ``ApprovalRequest`` values in tests."""
    return _make_request
