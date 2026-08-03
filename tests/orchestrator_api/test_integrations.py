from __future__ import annotations

from pathlib import Path

import pytest
from starlette.testclient import TestClient

from factory.integrations.runtime import (
    IntegrationName,
    IntegrationOperation,
    IntegrationRecord,
    IntegrationState,
    OperationState,
)
from factory.orchestrator.store.runtime_state import (
    SQLiteOrchestratorStateReader,
    _OrchestratorStateWriter,
    apply_migrations,
)
from factory.orchestrator_api import OperatorSession, TaskOperatorService, create_app

pytestmark = pytest.mark.loopback


class Integrations:
    def __init__(self) -> None:
        self.actors: list[str] = []
        self.cancelled: list[str] = []
        self.disabled: set[IntegrationName] = set()

    def status(self, name: IntegrationName) -> IntegrationRecord:
        state = IntegrationState.DISABLED if name in self.disabled else IntegrationState.READY
        detail = "disabled by configuration" if name in self.disabled else "ready"
        return IntegrationRecord(1, name, state, detail, 10)

    def is_enabled(self, name: IntegrationName) -> bool:
        return name not in self.disabled

    def latest_operation(self, name: IntegrationName) -> IntegrationOperation | None:
        del name
        return None

    def start(self, name: IntegrationName, *, actor: str, operation_id: str) -> IntegrationRecord:
        self.actors.append(actor)
        return IntegrationRecord(2, name, IntegrationState.READY, operation_id, 11)

    install = start
    stop = start
    disable = start
    remove = start

    def logs(self, name: IntegrationName, *, tail: int = 200) -> tuple[str, ...]:
        del name, tail
        return ("bounded log",)

    def dispatch_agent_task(
        self, operation_id: str, request_json: str, *, actor: str, submit: object
    ) -> IntegrationOperation:
        self.actors.append(actor)
        task_id = submit()
        return IntegrationOperation(
            operation_id,
            IntegrationName.AGENT_ZERO,
            "agent-task",
            OperationState.RUNNING,
            task_id,
            request_json,
            None,
            None,
            actor,
            12,
            12,
        )

    def reconcile_agent_task(
        self, operation_id: str, state_for_task: object
    ) -> IntegrationOperation:
        del state_for_task
        return IntegrationOperation(
            operation_id,
            IntegrationName.AGENT_ZERO,
            "agent-task",
            OperationState.RUNNING,
            "task-1",
            "{}",
            None,
            None,
            "server-operator",
            12,
            13,
        )

    def cancel_agent_task(self, operation_id: str, cancel_task: object) -> IntegrationOperation:
        self.cancelled.append(operation_id)
        return IntegrationOperation(
            operation_id,
            IntegrationName.AGENT_ZERO,
            "agent-task",
            OperationState.CANCELLED,
            "task-1",
            "{}",
            None,
            "cancelled by operator",
            "server-operator",
            12,
            13,
        )

    def refresh_worldmonitor(
        self,
        operation_id: str,
        *,
        start_ms: int,
        end_ms: int,
        limit: int,
        actor: str,
    ) -> IntegrationOperation:
        del start_ms, end_ms, limit
        self.actors.append(actor)
        return IntegrationOperation(
            operation_id,
            IntegrationName.WORLDMONITOR,
            "refresh",
            OperationState.SUCCEEDED,
            None,
            "{}",
            '{"records":[]}',
            None,
            actor,
            13,
            13,
        )


def _client(tmp_path: Path) -> tuple[TestClient, Integrations]:
    database = tmp_path / "runtime.db"
    apply_migrations(database, Path(__file__).resolve().parents[2] / "migrations" / "runtime")
    service = TaskOperatorService(
        _OrchestratorStateWriter(database), SQLiteOrchestratorStateReader(database)
    )
    integrations = Integrations()
    app = create_app(
        service=service,
        operator_session=OperatorSession("session-token", "server-operator"),
        integration_control=integrations,
    )
    return TestClient(app), integrations


def test_integration_status_is_backend_authoritative(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)

    response = client.get("/api/orchestrator/integrations")

    assert response.status_code == 200
    assert response.json()["agent-zero"]["state"] == "READY"
    assert response.json()["worldmonitor"]["state"] == "READY"


def test_lifecycle_mutation_requires_runtime_operator_session(tmp_path: Path) -> None:
    client, integrations = _client(tmp_path)

    denied = client.post(
        "/api/orchestrator/integrations/agent-zero/start", json={"operation_id": "op-1"}
    )
    allowed = client.post(
        "/api/orchestrator/integrations/agent-zero/start",
        headers={"Authorization": "Bearer session-token"},
        json={"operation_id": "op-1", "operator": "spoofed"},
    )

    assert denied.status_code == 401
    assert allowed.status_code == 200
    assert integrations.actors == ["server-operator"]


def test_agent_task_and_worldmonitor_refresh_return_real_durable_payloads(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    headers = {"Authorization": "Bearer session-token"}

    agent = client.post(
        "/api/orchestrator/integrations/agent-zero/tasks",
        headers=headers,
        json={"operation_id": "dispatch-1", "instructions": "do work"},
    )
    world = client.post(
        "/api/orchestrator/integrations/worldmonitor/refresh",
        headers=headers,
        json={"operation_id": "refresh-1", "start_ms": 1, "end_ms": 2, "limit": 25},
    )

    assert agent.status_code == 200
    assert agent.json()["status"] == "RUNNING"
    assert agent.json()["context_id"].startswith("task-")
    assert world.status_code == 200
    assert world.json()["payload"] == {"records": []}


def test_logs_cancel_and_non_destructive_remove_are_authenticated(tmp_path: Path) -> None:
    client, integrations = _client(tmp_path)
    assert client.get("/api/orchestrator/integrations/agent-zero/logs").status_code == 401
    headers = {"Authorization": "Bearer session-token"}
    logs = client.get("/api/orchestrator/integrations/agent-zero/logs?tail=20", headers=headers)
    cancel = client.post(
        "/api/orchestrator/integrations/agent-zero/cancel",
        json={"operation_id": "dispatch-1"},
        headers=headers,
    )
    remove = client.post(
        "/api/orchestrator/integrations/agent-zero/remove",
        json={"operation_id": "remove-1"},
        headers=headers,
    )
    assert logs.json() == {"lines": ["bounded log"]}
    assert cancel.json()["status"] == "CANCELLED"
    assert remove.json()["state"] == "READY"
    assert integrations.cancelled == ["dispatch-1"]


def test_disabled_integration_routes_fail_closed_with_actionable_status(tmp_path: Path) -> None:
    client, integrations = _client(tmp_path)
    integrations.disabled.add(IntegrationName.AGENT_ZERO)
    response = client.post(
        "/api/orchestrator/integrations/agent-zero/tasks",
        json={"operation_id": "dispatch-disabled", "instructions": "do work"},
        headers={"Authorization": "Bearer session-token"},
    )
    assert response.status_code == 409
    assert response.json() == {"error": "agent-zero is disabled in Builder configuration"}
