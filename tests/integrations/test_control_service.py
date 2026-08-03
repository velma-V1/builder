from __future__ import annotations

import json
from pathlib import Path

import pytest

from factory.audit.models import AuditEvent, RecordKind
from factory.integrations.control import IntegrationControlError, IntegrationControlService
from factory.integrations.migrations import apply_integration_migrations
from factory.integrations.runtime import (
    CommandResult,
    IntegrationName,
    IntegrationRuntime,
    IntegrationState,
    IntegrationStore,
    ManagedServiceSpec,
    OperationState,
)
from factory.integrations.worldmonitor.models import (
    Category,
    Freshness,
    IntelligenceRecord,
    WorldMonitorFreshness,
    WorldMonitorSourceRef,
)
from factory.orchestrator.models import TaskState


class Runner:
    def run(self, command: tuple[str, ...], *, timeout_s: int) -> CommandResult:
        del timeout_s
        if "ps" in command:
            return CommandResult(0, "container-id", "")
        return CommandResult(0, "ok", "")


class WorldClient:
    def refresh_earthquakes(
        self, *, start_ms: int, end_ms: int, limit: int, now_ms: int
    ) -> tuple[IntelligenceRecord, ...]:
        del start_ms, end_ms, limit
        return (
            IntelligenceRecord(
                "quake-1",
                Category.DISASTERS,
                WorldMonitorSourceRef(
                    "USGS via WorldMonitor", "https://earthquake.usgs.gov/x", "q1"
                ),
                "0,0",
                WorldMonitorFreshness(Freshness.FRESH, now_ms, now_ms, 1000),
                "M5 — location",
                "a" * 64,
                "https://earthquake.usgs.gov/x",
            ),
        )


class FailingWorldClient:
    def refresh_earthquakes(
        self, *, start_ms: int, end_ms: int, limit: int, now_ms: int
    ) -> tuple[IntelligenceRecord, ...]:
        del start_ms, end_ms, limit, now_ms
        raise RuntimeError("USGS upstream unavailable")


class Audit:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def append(self, event: AuditEvent) -> object:
        self.events.append(event)
        return object()


def _service(tmp_path: Path) -> tuple[IntegrationControlService, IntegrationStore, Audit]:
    database = tmp_path / "integrations.db"
    apply_integration_migrations(
        database, Path(__file__).resolve().parents[2] / "migrations" / "integrations"
    )
    store = IntegrationStore(database)
    runtime = IntegrationRuntime(store, Runner(), lambda: 100)
    audit = Audit()
    specs = {
        IntegrationName.AGENT_ZERO: ManagedServiceSpec(
            IntegrationName.AGENT_ZERO,
            "v2.7",
            "87e1e591e1ba2e8b1a19d34e134fcae490c8dded",
            Path("agent.yaml"),
            50080,
            "http://127.0.0.1:50080",
            30,
        ),
        IntegrationName.WORLDMONITOR: ManagedServiceSpec(
            IntegrationName.WORLDMONITOR,
            "v2.5.23",
            "e51058e1765ef2f0c83ccb1d08d984bc59d23f10",
            Path("world.yaml"),
            3000,
            "http://127.0.0.1:3000",
            30,
        ),
    }
    return (
        IntegrationControlService(runtime, specs, WorldClient(), audit, lambda: 100),
        store,
        audit,
    )


def test_lifecycle_actions_are_audited_with_intent_and_completion(tmp_path: Path) -> None:
    service, store, audit = _service(tmp_path)

    record = service.start(IntegrationName.AGENT_ZERO, actor="local-operator", operation_id="op-1")

    assert record.state is IntegrationState.READY
    assert [event.record_kind for event in audit.events] == [
        RecordKind.INTENT,
        RecordKind.COMPLETION,
    ]
    assert store.latest(IntegrationName.AGENT_ZERO).state is IntegrationState.READY


def test_worldmonitor_refresh_requires_ready_and_persists_real_records(tmp_path: Path) -> None:
    service, store, _audit = _service(tmp_path)
    store.append(IntegrationName.WORLDMONITOR, IntegrationState.READY, "ready", 1)

    result = service.refresh_worldmonitor(
        "refresh-1", start_ms=1, end_ms=2, limit=25, actor="local-operator"
    )

    payload = json.loads(result.result_json or "{}")
    assert payload["records"][0]["source"]["name"] == "USGS via WorldMonitor"
    assert payload["records"][0]["summary"] == "M5 — location"


def test_worldmonitor_failure_is_durable_degraded_without_records(tmp_path: Path) -> None:
    service, store, _audit = _service(tmp_path)
    service.world_client = FailingWorldClient()
    store.append(IntegrationName.WORLDMONITOR, IntegrationState.READY, "ready", 1)
    result = service.refresh_worldmonitor(
        "refresh-fail", start_ms=1, end_ms=2, limit=25, actor="local-operator"
    )
    assert result.state.value == "FAILED"
    assert result.result_json is None
    assert "USGS upstream unavailable" in (result.reason or "")
    assert store.latest(IntegrationName.WORLDMONITOR).state is IntegrationState.DEGRADED


def test_restart_reconciliation_never_leaves_operations_running(tmp_path: Path) -> None:
    service, store, _audit = _service(tmp_path)
    store.begin_operation(
        "refresh-running", IntegrationName.WORLDMONITOR, "refresh", "{}", "operator", 1
    )
    store.update_operation("refresh-running", OperationState.RUNNING, 2)
    store.begin_operation(
        "agent-running",
        IntegrationName.AGENT_ZERO,
        "agent-task",
        "{}",
        "operator",
        1,
        context_id="ctx-1",
    )
    store.update_operation("agent-running", OperationState.RUNNING, 2)
    results = service.reconcile_operations(lambda _task: TaskState.RUNNING)
    assert {item.operation_id: item.state.value for item in results} == {
        "refresh-running": "INTERRUPTED",
        "agent-running": "RUNNING",
    }


def test_agent_dispatch_is_persisted_before_orchestrator_submission(tmp_path: Path) -> None:
    service, store, audit = _service(tmp_path)
    store.append(IntegrationName.AGENT_ZERO, IntegrationState.READY, "ready", 1)
    observed: list[OperationState] = []

    def submit() -> str:
        operation = store.operation("dispatch-1")
        assert operation is not None
        observed.append(operation.state)
        return "task-123"

    operation = service.dispatch_agent_task(
        "dispatch-1", '{"instructions":"fix tests"}', actor="operator", submit=submit
    )

    assert observed == [OperationState.PENDING]
    assert operation.state is OperationState.RUNNING
    assert operation.context_id == "task-123"
    assert service.latest_operation(IntegrationName.AGENT_ZERO) == operation
    assert [event.record_kind for event in audit.events] == [
        RecordKind.INTENT,
        RecordKind.COMPLETION,
    ]


def test_agent_dispatch_tracks_authoritative_task_lifecycle(tmp_path: Path) -> None:
    service, store, _audit = _service(tmp_path)
    store.append(IntegrationName.AGENT_ZERO, IntegrationState.READY, "ready", 1)
    service.dispatch_agent_task("dispatch-2", "{}", actor="operator", submit=lambda: "task-456")

    running = service.reconcile_agent_task("dispatch-2", lambda _task: TaskState.VERIFYING)
    complete = service.reconcile_agent_task("dispatch-2", lambda _task: TaskState.COMPLETE)

    assert running.state is OperationState.RUNNING
    assert complete.state is OperationState.SUCCEEDED
    assert json.loads(complete.result_json or "{}") == {"task_id": "task-456"}


def test_agent_dispatch_never_reports_recovered_blocked_task_as_running(tmp_path: Path) -> None:
    service, store, _audit = _service(tmp_path)
    store.append(IntegrationName.AGENT_ZERO, IntegrationState.READY, "ready", 1)
    service.dispatch_agent_task("dispatch-blocked", "{}", actor="operator", submit=lambda: "task")

    operation = service.reconcile_agent_task("dispatch-blocked", lambda _task: TaskState.BLOCKED)

    assert operation.state is OperationState.INTERRUPTED
    assert "BLOCKED" in (operation.reason or "")


def test_agent_dispatch_cancellation_uses_builder_task_authority(tmp_path: Path) -> None:
    service, store, _audit = _service(tmp_path)
    store.append(IntegrationName.AGENT_ZERO, IntegrationState.READY, "ready", 1)
    service.dispatch_agent_task("dispatch-3", "{}", actor="operator", submit=lambda: "task-789")
    cancelled: list[str] = []

    operation = service.cancel_agent_task("dispatch-3", lambda task_id: cancelled.append(task_id))

    assert cancelled == ["task-789"]
    assert operation.state is OperationState.CANCELLED


def test_disabled_integration_rejects_operational_access(tmp_path: Path) -> None:
    service, _store, _audit = _service(tmp_path)
    current = service.specs[IntegrationName.AGENT_ZERO]
    service.specs = {
        **service.specs,
        IntegrationName.AGENT_ZERO: ManagedServiceSpec(
            current.name,
            current.release,
            current.commit,
            current.compose_file,
            current.port,
            current.readiness_url,
            current.timeout_s,
            enabled=False,
        ),
    }

    with pytest.raises(IntegrationControlError, match="disabled"):
        service.logs(IntegrationName.AGENT_ZERO)
