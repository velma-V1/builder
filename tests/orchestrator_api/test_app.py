"""Phase 3A — orchestrator API HTTP behavior: submit / detail / cancel / health.

No approve/reject route exists -- confirmed absent, not merely untested.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from starlette.applications import Starlette
from starlette.testclient import TestClient

from factory.orchestrator.store.runtime_state import (
    SQLiteOrchestratorStateReader,
    _OrchestratorStateWriter,
)
from factory.orchestrator_api import TaskOperatorService, create_app

_SUBMIT_ROUTE = "/api/orchestrator/tasks"


def _submit_body(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "project_ref": "proj-1",
        "workstream_id": "ws-1",
        "description": "add feature X",
        "idempotency_key": "key-1",
    }
    body.update(overrides)
    return body


def test_submit_returns_201_and_queued_state(client: TestClient) -> None:
    response = client.post(_SUBMIT_ROUTE, json=_submit_body())
    assert response.status_code == 201
    body = response.json()
    assert body["state"] == "QUEUED"
    assert body["created"] is True
    assert isinstance(body["task_id"], str) and body["task_id"]


def test_submit_repeat_idempotency_key_returns_200_same_task(client: TestClient) -> None:
    first = client.post(_SUBMIT_ROUTE, json=_submit_body(idempotency_key="dup")).json()
    second = client.post(_SUBMIT_ROUTE, json=_submit_body(idempotency_key="dup"))
    assert second.status_code == 200
    assert second.json()["task_id"] == first["task_id"]
    assert second.json()["created"] is False


@pytest.mark.parametrize(
    "missing_field", ["project_ref", "workstream_id", "description", "idempotency_key"]
)
def test_submit_missing_required_field_returns_400(client: TestClient, missing_field: str) -> None:
    body = _submit_body()
    del body[missing_field]
    response = client.post(_SUBMIT_ROUTE, json=body)
    assert response.status_code == 400
    assert "error" in response.json()


_INVALID_REQUIRED_VALUES = (
    pytest.param(None, id="null"),
    pytest.param({}, id="object"),
    pytest.param([], id="array"),
    pytest.param(12345, id="number"),
    pytest.param(True, id="boolean"),
    pytest.param("", id="empty_string"),
    pytest.param("   ", id="whitespace_only"),
)


@pytest.mark.parametrize("invalid_value", _INVALID_REQUIRED_VALUES)
@pytest.mark.parametrize(
    "required_field", ["project_ref", "workstream_id", "description", "idempotency_key"]
)
def test_submit_invalid_required_field_value_returns_400(
    client: TestClient, required_field: str, invalid_value: object
) -> None:
    """Every required field must reject null/object/array/number/boolean/blank values with a
    400 -- none of these may be silently stringified past validation and reach the write layer
    (regression: an explicit JSON ``null`` or ``{}`` used to pass the old ``str(...).strip()``
    check and surface as a misleading 503 instead)."""
    body = _submit_body()
    body[required_field] = invalid_value
    response = client.post(_SUBMIT_ROUTE, json=body)
    assert response.status_code == 400
    assert "error" in response.json()


def test_submit_null_idempotency_key_returns_400_not_503(client: TestClient) -> None:
    response = client.post(_SUBMIT_ROUTE, json=_submit_body(idempotency_key=None))
    assert response.status_code == 400
    assert response.json()["error"]


def test_submit_object_idempotency_key_returns_400_not_503(client: TestClient) -> None:
    response = client.post(_SUBMIT_ROUTE, json=_submit_body(idempotency_key={}))
    assert response.status_code == 400
    assert response.json()["error"]


def test_submit_valid_non_empty_strings_still_accepted(client: TestClient) -> None:
    response = client.post(_SUBMIT_ROUTE, json=_submit_body(idempotency_key="still-valid-key"))
    assert response.status_code == 201
    assert response.json()["created"] is True


def test_submit_malformed_json_body_returns_400(client: TestClient) -> None:
    response = client.post(
        _SUBMIT_ROUTE, content=b"not json", headers={"content-type": "application/json"}
    )
    assert response.status_code == 400


def test_get_detail_for_known_task(client: TestClient) -> None:
    task_id = client.post(_SUBMIT_ROUTE, json=_submit_body(idempotency_key="detail-1")).json()[
        "task_id"
    ]
    response = client.get(f"{_SUBMIT_ROUTE}/{task_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["task_id"] == task_id
    assert body["state"] == "QUEUED"
    assert body["description"] == "add feature X"


def test_get_detail_for_unknown_task_returns_404(client: TestClient) -> None:
    response = client.get(f"{_SUBMIT_ROUTE}/no-such-task")
    assert response.status_code == 404
    assert "error" in response.json()


def test_cancel_known_queued_task_returns_200_cancelled(client: TestClient) -> None:
    task_id = client.post(_SUBMIT_ROUTE, json=_submit_body(idempotency_key="cancel-1")).json()[
        "task_id"
    ]
    response = client.post(f"{_SUBMIT_ROUTE}/{task_id}/cancel")
    assert response.status_code == 200
    assert response.json()["state"] == "CANCELLED"


def test_cancel_with_reason_body_is_accepted(client: TestClient) -> None:
    task_id = client.post(_SUBMIT_ROUTE, json=_submit_body(idempotency_key="cancel-2")).json()[
        "task_id"
    ]
    response = client.post(f"{_SUBMIT_ROUTE}/{task_id}/cancel", json={"reason": "no longer needed"})
    assert response.status_code == 200


def test_cancel_unknown_task_returns_404(client: TestClient) -> None:
    response = client.post(f"{_SUBMIT_ROUTE}/no-such-task/cancel")
    assert response.status_code == 404


def test_cancel_already_cancelled_task_returns_409(client: TestClient) -> None:
    task_id = client.post(_SUBMIT_ROUTE, json=_submit_body(idempotency_key="cancel-3")).json()[
        "task_id"
    ]
    client.post(f"{_SUBMIT_ROUTE}/{task_id}/cancel")
    response = client.post(f"{_SUBMIT_ROUTE}/{task_id}/cancel")
    assert response.status_code == 409
    assert "error" in response.json()


def test_health_returns_200_ok(client: TestClient) -> None:
    response = client.get("/api/orchestrator/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "reachable"}


def test_health_reports_503_when_database_is_unreachable(
    writer: _OrchestratorStateWriter, tmp_path: Path
) -> None:
    missing_db = tmp_path / "does-not-exist.db"
    reader = SQLiteOrchestratorStateReader(database_path=missing_db)
    service = TaskOperatorService(writer=writer, reader=reader)
    app: Starlette = create_app(service=service)
    client = TestClient(app)

    response = client.get("/api/orchestrator/health")
    assert response.status_code == 503
    assert response.json()["status"] == "degraded"


@pytest.mark.parametrize("method", ["get", "put", "delete", "patch"])
def test_submit_route_rejects_other_methods(client: TestClient, method: str) -> None:
    response = getattr(client, method)(_SUBMIT_ROUTE)
    assert response.status_code == 405


def test_approve_route_fails_closed_when_phase3b_is_not_configured(client: TestClient) -> None:
    task_id = client.post(_SUBMIT_ROUTE, json=_submit_body(idempotency_key="no-approve")).json()[
        "task_id"
    ]
    response = client.post(
        f"{_SUBMIT_ROUTE}/{task_id}/approve",
        json={
            "approval_id": "apr-test",
            "operator": "operator",
            "confirmed_destructive": True,
        },
    )
    assert response.status_code == 503


def test_reject_route_fails_closed_when_phase3b_is_not_configured(client: TestClient) -> None:
    task_id = client.post(_SUBMIT_ROUTE, json=_submit_body(idempotency_key="no-reject")).json()[
        "task_id"
    ]
    response = client.post(
        f"{_SUBMIT_ROUTE}/{task_id}/reject",
        json={"approval_id": "apr-test", "operator": "operator", "reason": "declined"},
    )
    assert response.status_code == 503


def test_forced_unexpected_failure_returns_controlled_503(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(self: TaskOperatorService, task_id: str) -> None:
        raise RuntimeError("simulated unexpected failure")

    monkeypatch.setattr(TaskOperatorService, "get_detail", _boom)
    response = client.get(f"{_SUBMIT_ROUTE}/anything")
    assert response.status_code == 503
    body_text = response.text
    for leak in ("Traceback", "RuntimeError", ".py", "/home/"):
        assert leak not in body_text


pytestmark = pytest.mark.loopback
