"""Agent Zero streaming compatibility adapter at the model-gateway route (SSE).

The route is the only place Agent Zero v2.7's mandatory stream=true is normalized. The
underlying ``ModelGateway.complete`` keeps its fail-closed non-streaming contract (see
``tests/integrations/test_model_gateway.py``).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from factory.integrations.agent_zero.policy import AgentZeroModelResult
from factory.integrations.model_gateway import ModelGateway, ModelGatewayError
from factory.orchestrator.store.runtime_state import (
    SQLiteOrchestratorStateReader,
    _OrchestratorStateWriter,
    apply_migrations,
)
from factory.orchestrator_api import TaskOperatorService, create_app
from factory.worker_engine.model_router import FakeModelRouter

_ROUTE = "/api/integrations/model/v1/chat/completions"
_CREDENTIAL = "Bearer session-token"


def _gateway(model: str = "devstral-pinned") -> ModelGateway:
    result = AgentZeroModelResult(True, "answer", "f" * 64, "ollama:local", "")
    return ModelGateway(FakeModelRouter(default=result), "session-token", model)


def _client(tmp_path: Path, gateway: ModelGateway) -> TestClient:
    database = tmp_path / "runtime.db"
    apply_migrations(database, Path(__file__).resolve().parents[2] / "migrations" / "runtime")
    service = TaskOperatorService(
        _OrchestratorStateWriter(database), SQLiteOrchestratorStateReader(database)
    )
    app = create_app(service=service, model_gateway=gateway)
    return TestClient(app)


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    return _client(tmp_path, _gateway())


def _payload(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "model": "devstral-pinned",
        "messages": [{"role": "user", "content": "task"}],
        "stream": True,
    }
    body.update(overrides)
    return body


def test_core_gateway_streaming_still_fails_closed() -> None:
    with pytest.raises(ModelGatewayError, match="streaming"):
        _gateway().complete(_CREDENTIAL, _payload())


def test_missing_or_wrong_token_returns_401(client: TestClient) -> None:
    assert client.post(_ROUTE, json=_payload()).status_code == 401
    assert (
        client.post(_ROUTE, json=_payload(), headers={"Authorization": "Bearer wrong"}).status_code
        == 401
    )


def test_malformed_streaming_payload_still_fails(client: TestClient) -> None:
    response = client.post(
        _ROUTE, json=_payload(messages=[]), headers={"Authorization": _CREDENTIAL}
    )
    assert response.status_code == 503
    assert "error" in response.json()


def test_unsupported_model_still_fails(client: TestClient) -> None:
    response = client.post(
        _ROUTE, json=_payload(model="other"), headers={"Authorization": _CREDENTIAL}
    )
    assert response.status_code == 503


def test_substituted_router_model_still_fails(tmp_path: Path) -> None:
    substituted = AgentZeroModelResult(True, "answer", "f" * 64, "hosted:fallback")
    gateway = ModelGateway(FakeModelRouter(default=substituted), "session-token", "devstral-pinned")
    response = _client(tmp_path, gateway).post(
        _ROUTE, json=_payload(), headers={"Authorization": _CREDENTIAL}
    )
    assert response.status_code == 503
    assert "substitution" in response.json()["error"]


def test_valid_streaming_request_returns_openai_sse(client: TestClient) -> None:
    response = client.post(_ROUTE, json=_payload(), headers={"Authorization": _CREDENTIAL})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")


def test_sse_terminates_with_done(client: TestClient) -> None:
    response = client.post(_ROUTE, json=_payload(), headers={"Authorization": _CREDENTIAL})
    assert response.text.endswith("data: [DONE]\n\n")
    assert response.text.count("data: [DONE]") == 1


def test_assembled_streamed_content_equals_completion(client: TestClient) -> None:
    response = client.post(_ROUTE, json=_payload(), headers={"Authorization": _CREDENTIAL})
    assembled = ""
    for line in response.text.splitlines():
        if not line.startswith("data: ") or line == "data: [DONE]":
            continue
        chunk = json.loads(line[len("data: ") :])
        assert chunk["object"] == "chat.completion.chunk"
        choices = chunk["choices"]
        assert isinstance(choices, list) and choices
        delta = choices[0].get("delta") or {}
        content = delta.get("content")
        if isinstance(content, str):
            assembled += content
    assert assembled == "answer"


def test_final_chunk_carries_finish_reason(client: TestClient) -> None:
    response = client.post(_ROUTE, json=_payload(), headers={"Authorization": _CREDENTIAL})
    chunks = [
        json.loads(line[len("data: ") :])
        for line in response.text.splitlines()
        if line.startswith("data: ") and line != "data: [DONE]"
    ]
    assert chunks[-1]["choices"][0]["finish_reason"] == "stop"


def test_no_token_prompt_or_headers_in_logs_or_response(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    prompt = "super-secret-prompt-text"
    with caplog.at_level(logging.DEBUG):
        response = client.post(
            _ROUTE,
            json=_payload(messages=[{"role": "user", "content": prompt}]),
            headers={"Authorization": _CREDENTIAL, "X-Extra-Header": "leaky-value"},
        )
    assert response.status_code == 200
    combined = "\n".join([response.text] + [r.getMessage() for r in caplog.records])
    assert "session-token" not in combined
    assert prompt not in combined
    assert "leaky-value" not in combined


def test_non_streaming_request_keeps_json_response(client: TestClient) -> None:
    response = client.post(
        _ROUTE,
        json=_payload(stream=False),
        headers={"Authorization": _CREDENTIAL},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["choices"][0]["message"]["content"] == "answer"
