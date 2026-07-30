"""Fixtures for the roadmap PH-3 safe file-op service (RPH3-T5) tests."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from factory.approval import ApprovalEngine, apply_security_migrations
from factory.audit import apply_audit_migrations
from factory.fileops import FileOpService
from factory.permission import (
    ActionRequest,
    DecisionKind,
    PermissionClass,
    PermissionEngine,
    PermissionGrant,
    TaskAuthority,
    apply_permission_migrations,
)

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
def project_root(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    (root / "src").mkdir(parents=True)
    (root / "src" / "main.py").write_text("x = 1\n")
    (root / "README.md").write_text("readme\n")
    return root


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
def service(
    permission_engine: PermissionEngine, approval_engine: ApprovalEngine,
    _dbs: tuple[Path, Path], clock: FakeClock,
) -> FileOpService:
    _security, audit = _dbs
    return FileOpService(
        permission_engine=permission_engine, approval_engine=approval_engine,
        audit_database_path=audit, clock=clock,
    )


@pytest.fixture
def authority(project_root: Path) -> TaskAuthority:
    return TaskAuthority(
        task_id="task-1", autonomy_level="L2-supervised",
        allowed_classes=frozenset(
            {PermissionClass.READ, PermissionClass.WRITE, PermissionClass.DELETE}
        ),
        project_root=str(project_root), allowed_paths=("src/**", "README.md"),
        read_only_paths=("README.md",),
    )


@pytest.fixture
def write_grant(
    permission_engine: PermissionEngine, authority: TaskAuthority
) -> Callable[[str], PermissionGrant]:
    def _grant(resource: str) -> PermissionGrant:
        decision = permission_engine.decide(
            ActionRequest(
                task_id="task-1", tool="fs", action="write", permission_class=PermissionClass.WRITE,
                scope="src", purpose="edit", resource=resource,
            ),
            authority,
        )
        assert decision.decision is DecisionKind.ALLOW, decision.cause
        return permission_engine.issue_grant(decision, 100)

    return _grant
