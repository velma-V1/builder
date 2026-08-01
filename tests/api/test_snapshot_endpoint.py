"""Phase 2B — GET /api/tasks/snapshot HTTP behavior.

The route is read-only end to end: the app only ever holds an OrchestratorStateReader
(never a writer), and no mutation method is registered on the path.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import httpx2
import pytest
from starlette.applications import Starlette
from starlette.testclient import TestClient

from factory.api import app as app_module
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


def test_app_state_only_exposes_a_reader_not_a_writer(
    reader: SQLiteOrchestratorStateReader,
) -> None:
    app: Starlette = create_app(task_reader=reader)
    assert app.state.task_reader is reader
    assert not hasattr(app.state, "task_writer")
    assert not hasattr(app.state, "writer")


# ---- Finding 1: every read-and-map failure mode returns the same controlled 503 JSON ----


def _assert_controlled_503(response: httpx2.Response) -> None:
    assert response.status_code == 503
    assert response.headers["content-type"].startswith("application/json")
    body = response.json()
    assert body == {"error": "snapshot temporarily unavailable"}
    body_text = response.text
    for leak in ("Traceback", "OperationalError", "ValueError", ".py", "/home/", "sqlite3"):
        assert leak not in body_text


def test_sqlite_error_returns_controlled_503_json(
    db_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    reader = SQLiteOrchestratorStateReader(database_path=db_path)

    def _boom(self: SQLiteOrchestratorStateReader, workstream_id: str) -> tuple[object, ...]:
        raise sqlite3.OperationalError("disk I/O error: /secret/internal/path/runtime.db")

    monkeypatch.setattr(SQLiteOrchestratorStateReader, "list_tasks_by_workstream", _boom)
    client = TestClient(create_app(task_reader=reader))

    _assert_controlled_503(client.get(_ROUTE, params={"workstream": "ws-1"}))


def test_malformed_updated_at_returns_controlled_503_json(
    writer: _OrchestratorStateWriter, db_path: Path
) -> None:
    writer.create_task(
        task_id="TASK-CORRUPT", project_id="P", contract_version=1, workstream_id="ws-1"
    )
    # Simulate authoritative-data corruption directly at the storage layer (bypassing the
    # writer, which never produces a malformed timestamp) so the real reader + real mapping
    # code hit a genuine parse failure, not a mocked one.
    connection = sqlite3.connect(str(db_path))
    connection.execute(
        "UPDATE tasks SET updated_at = 'not-a-timestamp' WHERE task_id = 'TASK-CORRUPT'"
    )
    connection.commit()
    connection.close()

    reader = SQLiteOrchestratorStateReader(database_path=db_path)
    client = TestClient(create_app(task_reader=reader))

    _assert_controlled_503(client.get(_ROUTE, params={"workstream": "ws-1"}))


def test_invalid_authoritative_task_state_returns_controlled_503_json(
    writer: _OrchestratorStateWriter, db_path: Path
) -> None:
    writer.create_task(
        task_id="TASK-BADSTATE", project_id="P", contract_version=1, workstream_id="ws-1"
    )
    # A current_state value outside the TaskState enum (e.g. from a future schema/enum this
    # reader doesn't know about yet) must still degrade to the controlled response, not an
    # uncaught ValueError from TaskState(...).
    connection = sqlite3.connect(str(db_path))
    connection.execute(
        "UPDATE tasks SET current_state = 'NOT_A_REAL_STATE' WHERE task_id = 'TASK-BADSTATE'"
    )
    connection.commit()
    connection.close()

    reader = SQLiteOrchestratorStateReader(database_path=db_path)
    client = TestClient(create_app(task_reader=reader))

    _assert_controlled_503(client.get(_ROUTE, params={"workstream": "ws-1"}))


def test_unexpected_mapping_layer_exception_returns_controlled_503_json(
    writer: _OrchestratorStateWriter,
    reader: SQLiteOrchestratorStateReader,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A row must actually reach the mapping step for it to raise; an empty result never calls it.
    writer.create_task(
        task_id="TASK-ANY", project_id="P", contract_version=1, workstream_id="ws-1"
    )

    # Any mapping-layer failure — not just ValueError — must be caught by the same boundary.
    def _explode(record: object) -> None:
        raise RuntimeError("unexpected mapping failure")

    monkeypatch.setattr(app_module, "to_task_snapshot", _explode)
    client = TestClient(create_app(task_reader=reader))

    _assert_controlled_503(client.get(_ROUTE, params={"workstream": "ws-1"}))


def test_request_validation_errors_are_unaffected_by_the_503_boundary(client: TestClient) -> None:
    # 400s are raised before the try/except boundary and must stay 400, not get swept into 503.
    response = client.get(_ROUTE)
    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/json")
