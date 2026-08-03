from __future__ import annotations

import io
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from email.message import Message
from typing import cast

import pytest

from factory.models.ollama_adapter.live_ollama import (
    DEVSTRAL_DISPLAY_NAME,
    OllamaClient,
    OllamaMalformedResponse,
    OllamaModelMissing,
    OllamaTimeout,
    OllamaUnavailable,
    resolve_devstral_tag,
)


@dataclass
class Response:
    body: bytes

    def __enter__(self) -> Response:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def _reply(monkeypatch: pytest.MonkeyPatch, payload: object) -> None:
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: Response(json.dumps(payload).encode()),
    )


def test_list_models_and_normalized_model_presence(monkeypatch: pytest.MonkeyPatch) -> None:
    _reply(monkeypatch, {"models": [{"name": "qwen:latest"}, {"name": "devstral:24b"}]})
    client = OllamaClient(base_url="http://localhost:11434/")
    assert client.list_models() == ("qwen:latest", "devstral:24b")
    assert client.has_model("qwen")
    assert client.has_model("devstral:24b")
    assert not client.has_model("missing:1b")


@pytest.mark.parametrize("payload", [{}, {"models": None}, b"not-json"])
def test_list_models_rejects_malformed_responses(
    monkeypatch: pytest.MonkeyPatch, payload: object
) -> None:
    if isinstance(payload, bytes):
        monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout: Response(payload))
    else:
        _reply(monkeypatch, payload)
    with pytest.raises(OllamaMalformedResponse):
        OllamaClient().list_models()


@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        (urllib.error.URLError("refused"), OllamaUnavailable),
        (TimeoutError("slow"), OllamaTimeout),
    ],
)
def test_list_models_maps_transport_failures(
    monkeypatch: pytest.MonkeyPatch, failure: Exception, expected: type[Exception]
) -> None:
    def fail(request: object, timeout: int) -> Response:
        raise failure

    monkeypatch.setattr("urllib.request.urlopen", fail)
    with pytest.raises(expected):
        OllamaClient(timeout_s=1).list_models()


def test_generate_posts_non_streaming_request_and_parses_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def respond(request: object, timeout: int) -> Response:
        captured["request"] = request
        captured["timeout"] = timeout
        return Response(
            json.dumps(
                {"model": "devstral:24b", "response": "done", "done": True, "total_duration": 42}
            ).encode()
        )

    monkeypatch.setattr("urllib.request.urlopen", respond)
    result = OllamaClient(timeout_s=9).generate(model="devstral:24b", prompt="hello", timeout_s=3)
    assert (result.model, result.response_text, result.done, result.total_duration_ns) == (
        "devstral:24b",
        "done",
        True,
        42,
    )
    assert captured["timeout"] == 3
    request = cast(urllib.request.Request, captured["request"])
    assert json.loads(cast(bytes, request.data)) == {
        "model": "devstral:24b",
        "prompt": "hello",
        "stream": False,
    }


@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        (urllib.error.URLError("refused"), OllamaUnavailable),
        (TimeoutError("slow"), OllamaTimeout),
        (
            urllib.error.HTTPError(
                "http://localhost", 404, "missing", Message(), io.BytesIO(b"model not found")
            ),
            OllamaModelMissing,
        ),
        (
            urllib.error.HTTPError(
                "http://localhost", 500, "bad", Message(), io.BytesIO(b"server error")
            ),
            OllamaUnavailable,
        ),
    ],
)
def test_generate_maps_transport_and_http_failures(
    monkeypatch: pytest.MonkeyPatch, failure: Exception, expected: type[Exception]
) -> None:
    def fail(request: object, timeout: int) -> Response:
        raise failure

    monkeypatch.setattr("urllib.request.urlopen", fail)
    with pytest.raises(expected):
        OllamaClient().generate(model="missing", prompt="hello")


@pytest.mark.parametrize("payload", [{}, {"model": "x"}, b"not-json"])
def test_generate_rejects_malformed_responses(
    monkeypatch: pytest.MonkeyPatch, payload: object
) -> None:
    if isinstance(payload, bytes):
        monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout: Response(payload))
    else:
        _reply(monkeypatch, payload)
    with pytest.raises(OllamaMalformedResponse):
        OllamaClient().generate(model="x", prompt="hello")


def test_resolve_devstral_discovers_supported_tag(monkeypatch: pytest.MonkeyPatch) -> None:
    _reply(monkeypatch, {"models": [{"name": "devstral-small2:24b"}]})
    resolved = resolve_devstral_tag(OllamaClient())
    assert resolved.display_name == DEVSTRAL_DISPLAY_NAME
    assert resolved.configured_tag == "devstral-small2:24b"


def test_resolve_override_requires_installed_tag(monkeypatch: pytest.MonkeyPatch) -> None:
    _reply(monkeypatch, {"models": [{"name": "devstral-small-2:24b"}]})
    client = OllamaClient()
    assert resolve_devstral_tag(client, override_tag="devstral-small-2:24b").configured_tag == (
        "devstral-small-2:24b"
    )
    with pytest.raises(OllamaModelMissing, match="configured model tag"):
        resolve_devstral_tag(client, override_tag="missing:24b")


def test_resolve_reports_installed_tags_when_no_devstral_matches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reply(monkeypatch, {"models": [{"name": "qwen:8b"}]})
    with pytest.raises(OllamaModelMissing, match="qwen:8b"):
        resolve_devstral_tag(OllamaClient())
