"""Phase 2B — GET /api/tasks/snapshot HTTP behavior.

The route is read-only end to end: the app only ever holds an OrchestratorStateReader
(never a writer), and no mutation method is registered on the path.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from starlette.applications import Starlette
from starlette.testclient import TestClient

from factory.api import create_app
from factory.orchestrator.store.runtime_state import (
    SQLiteOrchestratorStateReader,
    _OrchestratorStateWriter,
)

_ROUTE = "/api/tasks/snapshot"


def test_known_workstream_returns_200_with_exact_task_snapshot_shape(
    writer: _OrchestratorStateWriter, client: TestClient
) -> None:
    writer.create_task(
        task_id="TASK-001", project_id="P", contract_version=1, workstream_id="ws-1"
    )
    response = client.get(_ROUTE, params={"workstream": "ws-1"})
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 1
    assert set(body[0].keys()) == {"task_id", "state", "updated_at"}
    assert body[0]["task_id"] == "TASK-001"
    assert body[0]["state"] == "QUEUED"
    assert isinstance(body[0]["updated_at"], int)


def test_known_workstream_returns_only_its_assigned_tasks(
    writer: _OrchestratorStateWriter, client: TestClient
) -> None:
    writer.create_task(
        task_id="TASK-A", project_id="P", contract_version=1, workstream_id="ws-1"
    )
    writer.create_task(
        task_id="TASK-B", project_id="P", contract_version=1, workstream_id="ws-2"
    )
    writer.create_task(task_id="TASK-C", project_id="P", contract_version=1)  # unassigned

    response = client.get(_ROUTE, params={"workstream": "ws-1"})
    assert response.status_code == 200
    assert [t["task_id"] for t in response.json()] == ["TASK-A"]


def test_unknown_workstream_returns_200_with_empty_array(client: TestClient) -> None:
    response = client.get(_ROUTE, params={"workstream": "no-such-workstream"})
    assert response.status_code == 200
    assert response.json() == []


def test_missing_workstream_query_param_returns_400(client: TestClient) -> None:
    response = client.get(_ROUTE)
    assert response.status_code == 400
    body = response.json()
    assert "error" in body


def test_blank_workstream_query_param_returns_400(client: TestClient) -> None:
    response = client.get(_ROUTE, params={"workstream": ""})
    assert response.status_code == 400


def test_whitespace_only_workstream_query_param_returns_400(client: TestClient) -> None:
    response = client.get(_ROUTE, params={"workstream": "   "})
    assert response.status_code == 400


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_mutation_methods_are_rejected(client: TestClient, method: str) -> None:
    response = getattr(client, method)(_ROUTE, params={"workstream": "ws-1"})
    assert response.status_code == 405


def test_mutation_attempt_does_not_create_or_alter_any_task(
    writer: _OrchestratorStateWriter, reader: SQLiteOrchestratorStateReader, client: TestClient
) -> None:
    client.post(_ROUTE, params={"workstream": "ws-1"})
    assert reader.list_tasks_by_workstream("ws-1") == ()


def test_database_failure_returns_controlled_response_without_internals(
    db_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    reader = SQLiteOrchestratorStateReader(database_path=db_path)

    def _boom(self: SQLiteOrchestratorStateReader, workstream_id: str) -> tuple[object, ...]:
        raise sqlite3.OperationalError("disk I/O error: /secret/internal/path/runtime.db")

    monkeypatch.setattr(SQLiteOrchestratorStateReader, "list_tasks_by_workstream", _boom)
    app = create_app(task_reader=reader)
    client = TestClient(app)

    response = client.get(_ROUTE, params={"workstream": "ws-1"})
    assert response.status_code == 503
    body_text = response.text
    assert "/secret/internal/path" not in body_text
    assert "OperationalError" not in body_text
    assert "Traceback" not in body_text


def test_app_state_only_exposes_a_reader_not_a_writer(
    reader: SQLiteOrchestratorStateReader,
) -> None:
    app: Starlette = create_app(task_reader=reader)
    assert app.state.task_reader is reader
    assert not hasattr(app.state, "task_writer")
    assert not hasattr(app.state, "writer")
