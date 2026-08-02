"""Shared fixtures for the roadmap PH-3 Permission Enforcement (RPH3-T2) test suite."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from factory.audit import AuditValidator, apply_audit_migrations
from factory.permission import (
    ActionRequest,
    PermissionClass,
    PermissionEngine,
    SQLitePermissionReader,
    TaskAuthority,
    apply_permission_migrations,
)

RequestFactory = Callable[..., ActionRequest]
AuthorityFactory = Callable[..., TaskAuthority]

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
def project_root(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    (root / "src").mkdir(parents=True)
    (root / "src" / "main.py").write_text("x = 1\n")
    (root / "README.md").write_text("readme\n")
    return root


@pytest.fixture
def security_db_path(tmp_path: Path) -> Path:
    path = tmp_path / "security.db"
    apply_permission_migrations(path, SECURITY_MIGRATIONS_ROOT)
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
def engine(security_db_path: Path, audit_db_path: Path, clock: FakeClock) -> PermissionEngine:
    return PermissionEngine(
        security_database_path=security_db_path,
        audit_database_path=audit_db_path,
        clock=clock,
    )


@pytest.fixture
def reader(security_db_path: Path) -> SQLitePermissionReader:
    return SQLitePermissionReader(database_path=security_db_path)


@pytest.fixture
def audit_validator(audit_db_path: Path) -> AuditValidator:
    return AuditValidator(database_path=audit_db_path)


@pytest.fixture
def make_authority(project_root: Path) -> AuthorityFactory:
    def _make(
        *,
        task_id: str = "task-1",
        autonomy_level: str = "L2-supervised",
        allowed_classes: frozenset[PermissionClass] = frozenset(
            {
                PermissionClass.READ,
                PermissionClass.WRITE,
                PermissionClass.EXECUTE,
                PermissionClass.DELETE,
            }
        ),
        allowed_paths: tuple[str, ...] = ("src/**", "README.md"),
        forbidden_paths: tuple[str, ...] = (),
        read_only_paths: tuple[str, ...] = (),
        exclusive_paths: tuple[str, ...] = (),
    ) -> TaskAuthority:
        return TaskAuthority(
            task_id=task_id,
            autonomy_level=autonomy_level,
            allowed_classes=allowed_classes,
            project_root=str(project_root),
            allowed_paths=allowed_paths,
            forbidden_paths=forbidden_paths,
            read_only_paths=read_only_paths,
            exclusive_paths=exclusive_paths,
        )

    return _make


@pytest.fixture
def make_request() -> RequestFactory:
    def _make(
        *,
        task_id: str = "task-1",
        tool: str = "shell",
        action: str = "write_file",
        permission_class: PermissionClass = PermissionClass.WRITE,
        scope: str = "src",
        purpose: str = "apply an approved edit",
        resource: str | None = "src/main.py",
        actor: str = "cmp-perm",
    ) -> ActionRequest:
        return ActionRequest(
            task_id=task_id,
            tool=tool,
            action=action,
            permission_class=permission_class,
            scope=scope,
            purpose=purpose,
            resource=resource,
            actor=actor,
        )

    return _make
