"""Fixtures for the roadmap PH-3 Diagnostic Safe Mode (RPH3-T5) tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from factory.approval import ApprovalEngine, apply_security_migrations
from factory.audit import apply_audit_migrations
from factory.permission import PermissionEngine, apply_permission_migrations
from factory.safemode import SafeMode

_ROOT = Path(__file__).resolve().parents[2]
SECURITY_MIGRATIONS_ROOT = _ROOT / "migrations" / "security"
AUDIT_MIGRATIONS_ROOT = _ROOT / "migrations" / "audit"


class FakeClock:
    def __init__(self, start: int = 1_000_000) -> None:
        self.t = start

    def now_ts(self) -> int:
        return self.t

    def now_iso(self) -> str:
        return f"2026-07-26T00:00:{self.t % 60:02d}Z"


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def _dbs(tmp_path: Path) -> tuple[Path, Path]:
    security = tmp_path / "security.db"
    audit = tmp_path / "audit.db"
    apply_security_migrations(security, SECURITY_MIGRATIONS_ROOT)
    apply_permission_migrations(security, SECURITY_MIGRATIONS_ROOT)
    apply_audit_migrations(audit, AUDIT_MIGRATIONS_ROOT)
    return security, audit


@pytest.fixture
def permission_engine(_dbs: tuple[Path, Path], clock: FakeClock) -> PermissionEngine:
    security, audit = _dbs
    return PermissionEngine(
        security_database_path=security, audit_database_path=audit, clock=clock
    )


@pytest.fixture
def approval_engine(_dbs: tuple[Path, Path], clock: FakeClock) -> ApprovalEngine:
    security, audit = _dbs
    return ApprovalEngine(security_database_path=security, audit_database_path=audit, clock=clock)


@pytest.fixture
def safe_mode(
    permission_engine: PermissionEngine, approval_engine: ApprovalEngine,
    _dbs: tuple[Path, Path], clock: FakeClock,
) -> SafeMode:
    _security, audit = _dbs
    return SafeMode(
        audit_database_path=audit, permission_engine=permission_engine,
        approval_engine=approval_engine, clock=clock,
    )
