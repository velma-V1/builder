"""Fixtures for the repository-defined Lane A / Lane B RPH3 integration."""

from __future__ import annotations

from pathlib import Path

import pytest

from factory.approval import ApprovalEngine, apply_security_migrations
from factory.audit import AuditValidator, apply_audit_migrations
from factory.orchestrator.models import TaskState
from factory.orchestrator.store.runtime_state import (
    SQLiteOrchestratorStateReader,
    _OrchestratorStateWriter,
    apply_migrations,
)
from factory.permission import PermissionEngine, apply_permission_migrations
from factory.safemode import SafeMode
from factory.tools import ResourceLimits, ToolGateway, ToolRegistry, apply_tool_migrations
from factory.watchdog import (
    RPH3CrossLaneBridge,
    ServiceSupervisor,
    WatchdogControl,
    WatchdogInterventionReceiver,
    apply_watchdog_migration,
)

ROOT = Path(__file__).resolve().parents[2]
SECURITY_MIGRATIONS = ROOT / "migrations" / "security"
AUDIT_MIGRATIONS = ROOT / "migrations" / "audit"
RUNTIME_MIGRATIONS = ROOT / "migrations" / "runtime"
AUTH_PROOF = "cross-lane-test-proof"


class FakeClock:
    def __init__(self, start: int = 1_000_000) -> None:
        self.t = start
        self.mono = float(start)

    def now_ts(self) -> int:
        return self.t

    def now_iso(self) -> str:
        return f"2026-07-30T00:00:{self.t % 60:02d}Z"

    def monotonic(self) -> float:
        return self.mono

    def advance(self, seconds: int) -> None:
        self.t += seconds
        self.mono += seconds


class AllowEmergencyAuthority:
    def authorize(self, _request: object) -> bool:
        return True


class NoHostController:
    def restart(self, _service_id: str) -> bool:
        raise AssertionError("cross-lane tests must not perform host execution")

    def state(self, service_id: str) -> str:
        return f"{service_id}:healthy"


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
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def databases(tmp_path: Path) -> tuple[Path, Path, Path]:
    security = tmp_path / "security.db"
    audit = tmp_path / "audit.db"
    runtime = tmp_path / "runtime.db"
    apply_security_migrations(security, SECURITY_MIGRATIONS)
    apply_permission_migrations(security, SECURITY_MIGRATIONS)
    apply_tool_migrations(security, SECURITY_MIGRATIONS)
    apply_watchdog_migration(security, SECURITY_MIGRATIONS)
    apply_audit_migrations(audit, AUDIT_MIGRATIONS)
    apply_migrations(runtime, RUNTIME_MIGRATIONS)
    return security, audit, runtime


@pytest.fixture
def task_writer(databases: tuple[Path, Path, Path]) -> _OrchestratorStateWriter:
    return _OrchestratorStateWriter(databases[2])


@pytest.fixture
def task_reader(databases: tuple[Path, Path, Path]) -> SQLiteOrchestratorStateReader:
    return SQLiteOrchestratorStateReader(databases[2])


@pytest.fixture
def running_task(
    task_writer: _OrchestratorStateWriter,
    task_reader: SQLiteOrchestratorStateReader,
) -> str:
    task_id = "task-1"
    task_writer.create_task(task_id=task_id, project_id="project-1", contract_version=1)
    task_writer.apply_transition(
        task_id=task_id,
        expected_current_state=TaskState.QUEUED,
        new_state=TaskState.PLANNING,
        cause="integration setup",
        actor="test",
    )
    task_writer.apply_transition(
        task_id=task_id,
        expected_current_state=TaskState.PLANNING,
        new_state=TaskState.RUNNING,
        cause="integration setup",
        actor="test",
    )
    current = task_reader.get_task(task_id)
    assert current is not None and current.current_state is TaskState.RUNNING
    return task_id


@pytest.fixture
def permission_engine(
    databases: tuple[Path, Path, Path], clock: FakeClock
) -> PermissionEngine:
    return PermissionEngine(databases[0], databases[1], clock)


@pytest.fixture
def approval_engine(
    databases: tuple[Path, Path, Path], clock: FakeClock
) -> ApprovalEngine:
    return ApprovalEngine(databases[0], databases[1], clock)


@pytest.fixture
def registry(databases: tuple[Path, Path, Path], clock: FakeClock) -> ToolRegistry:
    return ToolRegistry(databases[0], databases[1], clock)


@pytest.fixture
def gateway(
    registry: ToolRegistry,
    permission_engine: PermissionEngine,
    databases: tuple[Path, Path, Path],
    clock: FakeClock,
) -> ToolGateway:
    return ToolGateway(registry, permission_engine, databases[1], DEFAULT_LIMITS, clock)


@pytest.fixture
def safe_mode(
    databases: tuple[Path, Path, Path],
    permission_engine: PermissionEngine,
    approval_engine: ApprovalEngine,
    clock: FakeClock,
) -> SafeMode:
    return SafeMode(databases[1], permission_engine, approval_engine, clock)


@pytest.fixture
def receiver(
    databases: tuple[Path, Path, Path],
    task_reader: SQLiteOrchestratorStateReader,
    task_writer: _OrchestratorStateWriter,
    clock: FakeClock,
) -> WatchdogInterventionReceiver:
    return WatchdogInterventionReceiver(
        databases[0],
        databases[1],
        task_reader,
        task_writer,
        AllowEmergencyAuthority(),
        ServiceSupervisor(NoHostController()),
        clock,
        supervised_identity="watchdog-1",
        auth_token=AUTH_PROOF,
    )


@pytest.fixture
def bridge(
    receiver: WatchdogInterventionReceiver,
    task_reader: SQLiteOrchestratorStateReader,
    safe_mode: SafeMode,
    databases: tuple[Path, Path, Path],
    clock: FakeClock,
) -> RPH3CrossLaneBridge:
    return RPH3CrossLaneBridge(
        receiver=receiver,
        control=WatchdogControl("watchdog-1", AUTH_PROOF, clock),
        task_reader=task_reader,
        safe_mode=safe_mode,
        audit_validator=AuditValidator(databases[1]),
        clock=clock,
    )
