"""Shared fixtures for the roadmap PH-3 Tool Registry + Gateway (RPH3-T5) test suite."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from factory.audit import apply_audit_migrations
from factory.permission import (
    ActionRequest,
    PermissionClass,
    PermissionEngine,
    PermissionGrant,
    TaskAuthority,
    apply_permission_migrations,
)
from factory.tools import (
    OutputSchema,
    Provenance,
    RegistrationRequest,
    ResourceLimits,
    ToolDeclaration,
    ToolGateway,
    ToolRegistry,
    apply_tool_migrations,
)

_ROOT = Path(__file__).resolve().parents[2]
SECURITY_MIGRATIONS_ROOT = _ROOT / "migrations" / "security"
AUDIT_MIGRATIONS_ROOT = _ROOT / "migrations" / "audit"

DeclFactory = Callable[..., ToolDeclaration]


class FakeClock:
    def __init__(self, start: int = 1_000_000) -> None:
        self.t = start

    def now_ts(self) -> int:
        return self.t

    def now_iso(self) -> str:
        return f"2026-07-26T00:00:{self.t % 60:02d}Z"

    def advance(self, seconds: int) -> None:
        self.t += seconds


DEFAULT_LIMITS = ResourceLimits(
    wall_clock_s=60,
    idle_s=10,
    cpu_s=30,
    ram_mb=512,
    storage_mb=100,
    max_processes=4,
    max_files=100,
    max_output_bytes=4096,
    max_download_bytes=0,
)


@pytest.fixture
def security_db_path(tmp_path: Path) -> Path:
    path = tmp_path / "security.db"
    apply_tool_migrations(path, SECURITY_MIGRATIONS_ROOT)
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
def registry(security_db_path: Path, audit_db_path: Path, clock: FakeClock) -> ToolRegistry:
    return ToolRegistry(
        security_database_path=security_db_path, audit_database_path=audit_db_path, clock=clock
    )


@pytest.fixture
def permission_engine(
    security_db_path: Path, audit_db_path: Path, clock: FakeClock
) -> PermissionEngine:
    return PermissionEngine(
        security_database_path=security_db_path, audit_database_path=audit_db_path, clock=clock
    )


@pytest.fixture
def gateway(
    registry: ToolRegistry,
    permission_engine: PermissionEngine,
    audit_db_path: Path,
    clock: FakeClock,
) -> ToolGateway:
    return ToolGateway(
        registry=registry,
        permission_engine=permission_engine,
        audit_database_path=audit_db_path,
        default_limits=DEFAULT_LIMITS,
        clock=clock,
    )


@pytest.fixture
def make_declaration() -> DeclFactory:
    def _make(
        *,
        tool_id: str = "formatter",
        version: str = "1.0",
        capabilities: tuple[str, ...] = ("format",),
        permission_classes: tuple[str, ...] = ("EXECUTE",),
        environment: str = "wsl2",
        resource_profile: str = "light",
        failure_behavior: str = "fail-closed",
    ) -> ToolDeclaration:
        return ToolDeclaration(
            tool_id=tool_id,
            version=version,
            capabilities=capabilities,
            inputs=("file",),
            outputs=("text",),
            side_effects=(),
            permission_classes=permission_classes,
            environment=environment,
            resource_profile=resource_profile,
            failure_behavior=failure_behavior,
        )

    return _make


@pytest.fixture
def register_tool(
    registry: ToolRegistry, make_declaration: DeclFactory
) -> Callable[..., ToolDeclaration]:
    def _register(
        *,
        tool_id: str = "formatter",
        version: str = "1.0",
        output_schema: OutputSchema | None = None,
    ) -> ToolDeclaration:
        declaration = make_declaration(tool_id=tool_id, version=version)
        schema = output_schema or OutputSchema(kind="json", max_bytes=4096, required_keys=("ok",))
        verdict = registry.register(
            RegistrationRequest(
                declaration=declaration,
                provenance=Provenance(source="github", checksum="sha:abc", license="MIT"),
                output_schema=schema,
            )
        )
        assert verdict.approved, verdict.reason
        return declaration

    return _register


@pytest.fixture
def execute_grant(
    permission_engine: PermissionEngine,
) -> Callable[..., PermissionGrant]:
    def _grant(*, task_id: str = "task-1", tool: str = "formatter") -> PermissionGrant:
        authority = TaskAuthority(
            task_id=task_id,
            autonomy_level="L2-supervised",
            allowed_classes=frozenset({PermissionClass.EXECUTE}),
            project_root="sandbox-root",
        )
        decision = permission_engine.decide(
            ActionRequest(
                task_id=task_id,
                tool=tool,
                action="run",
                permission_class=PermissionClass.EXECUTE,
                scope="exec",
                purpose="run a tool",
                resource=None,
            ),
            authority,
        )
        return permission_engine.issue_grant(decision, 100)

    return _grant
