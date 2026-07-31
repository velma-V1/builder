"""Provider tests — Replicate prediction lifecycle (pinned version, schema, output validation)."""

from __future__ import annotations

import json

import pytest
from support import StaticResolver, call, grant, secret_backend

from factory.network.fake_backend import FakeNetworkBackend
from factory.providers import (
    ApprovedReplicateRoute,
    PredictionState,
    ProviderConfiguration,
    ReplicateAdapter,
)
from factory.providers.transport import FakeExchange, FakeHttpTransport, HttpRequest, HttpResponse
from factory.routing.adapters.base import CallRequest
from factory.routing.models import Provider

pytestmark = pytest.mark.security

_OWNER, _NAME, _VERSION = "acme", "img-gen", "v-pinned-abc123"
_MODEL = f"{_OWNER}/{_NAME}"
_HOST = "api.replicate.com"
_ROUTE = ApprovedReplicateRoute(
    _OWNER, _NAME, _VERSION,
    input_schema_keys=frozenset({"prompt", "width"}),
    approved_output_domains=frozenset({"replicate.delivery"}),
)


def _resp(payload: dict[str, object], status: int = 200) -> HttpResponse:
    return HttpResponse(status, {"x-request-id": "r"}, json.dumps(payload).encode("utf-8"))


def _adapter(exchanges: tuple[FakeExchange, ...], *, max_polls: int = 5) -> ReplicateAdapter:
    config = ProviderConfiguration(
        Provider.REPLICATE, "https://api.replicate.com/v1", "REPLICATE_API_TOKEN",
        frozenset({_HOST}),
    )
    g = grant(host=_HOST, secret_name="REPLICATE_API_TOKEN")  # noqa: S106 - secret name/ref, not a value
    return ReplicateAdapter(
        config, FakeHttpTransport(exchanges), FakeNetworkBackend(), secret_backend(),
        StaticResolver(g), {_MODEL: _ROUTE}, clock=lambda: 0, max_polls=max_polls,
    )


def _is_create(req: HttpRequest) -> bool:
    return req.method == "POST" and req.url.endswith("/predictions")


def _is_poll(req: HttpRequest) -> bool:
    return req.method == "GET" and "/predictions/" in req.url


def _is_cancel(req: HttpRequest) -> bool:
    return req.method == "POST" and req.url.endswith("/cancel")


def _call() -> CallRequest:
    return call(route_key=f"REPLICATE:{_MODEL}")


def test_create_processing_succeeded() -> None:
    exchanges = (
        FakeExchange(_is_create, _resp({"id": "p1", "status": "processing", "version": _VERSION})),
        FakeExchange(_is_poll, _resp(
            {"id": "p1", "status": "succeeded", "version": _VERSION,
             "output": ["https://replicate.delivery/out.png"]})),
    )
    result = _adapter(exchanges).create_and_wait(_call(), {"prompt": "a cat", "width": 512})
    assert result.state is PredictionState.SUCCEEDED
    assert result.outputs == ("https://replicate.delivery/out.png",)
    assert result.prediction_id == "p1"


def test_create_failed() -> None:
    exchanges = (
        FakeExchange(_is_create, _resp({"id": "p2", "status": "failed", "version": _VERSION})),
    )
    result = _adapter(exchanges).create_and_wait(_call(), {"prompt": "x"})
    assert result.state is PredictionState.FAILED


def test_timeout_cancels() -> None:
    exchanges = (
        FakeExchange(_is_create, _resp({"id": "p3", "status": "processing", "version": _VERSION})),
        FakeExchange(_is_poll, _resp({"id": "p3", "status": "processing", "version": _VERSION})),
        FakeExchange(_is_cancel, _resp({"id": "p3", "status": "canceled", "version": _VERSION})),
    )
    result = _adapter(exchanges, max_polls=2).create_and_wait(_call(), {"prompt": "x"})
    assert result.state is PredictionState.CANCELED


def test_version_drift_rejected() -> None:
    exchanges = (
        FakeExchange(_is_create, _resp(
            {"id": "p4", "status": "processing", "version": "v-DIFFERENT"})),
    )
    result = _adapter(exchanges).create_and_wait(_call(), {"prompt": "x"})
    assert result.state is PredictionState.FAILED
    assert result.error_code == "PROVIDER_CONFLICT"


def test_unknown_input_key_rejected() -> None:
    exchanges = (
        FakeExchange(_is_create, _resp({"id": "p5", "status": "processing", "version": _VERSION})),
    )
    result = _adapter(exchanges).create_and_wait(_call(), {"prompt": "x", "evil": "y"})
    assert result.state is PredictionState.FAILED
    assert result.error_code == "MALFORMED_OUTPUT"


def test_unpinned_model_rejected() -> None:
    exchanges = (
        FakeExchange(_is_create, _resp({"id": "p6", "status": "succeeded", "version": _VERSION})),
    )
    result = _adapter(exchanges).create_and_wait(
        call(route_key="REPLICATE:someone/unapproved"), {"prompt": "x"})
    assert result.error_code == "MODEL_MISSING"


def test_malicious_output_url_rejected() -> None:
    exchanges = (
        FakeExchange(_is_create, _resp({"id": "p7", "status": "processing", "version": _VERSION})),
        FakeExchange(_is_poll, _resp(
            {"id": "p7", "status": "succeeded", "version": _VERSION,
             "output": ["https://evil.example/malware.bin"]})),
    )
    result = _adapter(exchanges).create_and_wait(_call(), {"prompt": "x"})
    assert result.state is PredictionState.FAILED
    assert result.error_code == "OUTPUT_URL_DENIED"


def test_no_cloud_grant_refused() -> None:
    config = ProviderConfiguration(
        Provider.REPLICATE, "https://api.replicate.com/v1", "REPLICATE_API_TOKEN",
        frozenset({_HOST}),
    )
    adapter = ReplicateAdapter(
        config, FakeHttpTransport(()), FakeNetworkBackend(), secret_backend(),
        StaticResolver(None), {_MODEL: _ROUTE}, clock=lambda: 0,
    )
    result = adapter.create_and_wait(_call(), {"prompt": "x"})
    assert result.error_code == "NETWORK_DENIED"
