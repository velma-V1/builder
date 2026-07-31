"""Provider tests — OpenAI core behaviour + brokered security, via the OpenRouter adapter."""

from __future__ import annotations

import json

import pytest
from support import (
    SECRET_VALUE,
    StaticResolver,
    call,
    chat_ok,
    grant,
    json_response,
    network_backend,
    openrouter_adapter,
    secret_backend,
    transport_for,
)

from factory.network.fake_backend import FakeNetworkBackend
from factory.providers import HostedGrant, OpenRouterAdapter
from factory.providers.transport import FakeExchange, FakeHttpTransport, HttpRequest, HttpResponse
from factory.routing.models import ExecutionStatus, Privacy
from factory.secret.broker import SecretBroker

pytestmark = pytest.mark.security

_MODEL = "openai/gpt-x"


def _adapter(
    transport: FakeHttpTransport,
    g: HostedGrant | None = None,
    sec: SecretBroker | None = None,
    net: FakeNetworkBackend | None = None,
) -> OpenRouterAdapter:
    resolver = StaticResolver(g if g is not None else grant(expected_upstream="openai"))
    return openrouter_adapter(
        transport, net or network_backend(), sec or secret_backend(), resolver,
    )


def test_success_returns_output_usage_and_no_secret_leak() -> None:
    sec = secret_backend()
    transport = transport_for("chat/completions", json_response(chat_ok(_MODEL, provider="openai")))
    result = _adapter(transport, sec=sec).execute(call(route_key=f"OPENROUTER:{_MODEL}"))
    assert result.status is ExecutionStatus.SUCCEEDED
    assert result.output == "hi"
    assert result.tokens == 12
    assert result.fingerprint is not None and result.fingerprint.digest()
    # secret never appears in surfaced output/reason
    assert SECRET_VALUE not in result.output and SECRET_VALUE not in result.reason
    # secret lease revoked after the call (revoke-and-forget)
    assert sec.has_persisted_material(0) is False


def test_returned_model_mismatch_fails_closed() -> None:
    resp = json_response(chat_ok("someone/else", provider="openai"))
    transport = transport_for("chat/completions", resp)
    result = _adapter(transport).execute(call(route_key=f"OPENROUTER:{_MODEL}"))
    assert result.status is ExecutionStatus.FAILED
    assert result.error_code == "RETURNED_MODEL_MISMATCH"


def test_hidden_upstream_change_rejected() -> None:
    resp = json_response(chat_ok(_MODEL, provider="anthropic"))
    transport = transport_for("chat/completions", resp)
    result = _adapter(transport).execute(call(route_key=f"OPENROUTER:{_MODEL}"))
    assert result.status is ExecutionStatus.FAILED
    assert result.error_code == "PROVIDER_MISMATCH"


def test_openrouter_disables_fallbacks_and_denies_data_collection() -> None:
    transport = transport_for("chat/completions", json_response(chat_ok(_MODEL, provider="openai")))
    _adapter(transport).execute(call(route_key=f"OPENROUTER:{_MODEL}"))
    body = json.loads(transport.sent[0].body.decode("utf-8"))
    assert body["provider"]["allow_fallbacks"] is False
    assert body["provider"]["require_parameters"] is True
    assert body["provider"]["data_collection"] == "deny"
    assert body["provider"]["order"] == ["openai"]


def test_zdr_requested_when_route_requires() -> None:
    transport = transport_for("chat/completions", json_response(chat_ok(_MODEL, provider="openai")))
    g = grant(expected_upstream="openai", require_zdr=True)
    _adapter(transport, g=g).execute(call(route_key=f"OPENROUTER:{_MODEL}"))
    assert json.loads(transport.sent[0].body.decode("utf-8"))["provider"]["zdr"] is True


def test_strict_route_requires_explicit_upstream() -> None:
    transport = transport_for("chat/completions", json_response(chat_ok(_MODEL)))
    g = grant(expected_upstream="", strict_upstream=True)
    result = _adapter(transport, g=g).execute(call(route_key=f"OPENROUTER:{_MODEL}"))
    assert result.error_code == "CAPABILITY_UNAVAILABLE"
    assert transport.sent == []  # never left the adapter


@pytest.mark.parametrize(
    ("status", "code"),
    [(401, "AUTH_UNAVAILABLE"), (403, "AUTH_UNAVAILABLE"), (404, "MODEL_MISSING"),
     (429, "RATE_LIMITED"), (500, "RUNTIME_UNAVAILABLE"), (503, "RUNTIME_UNAVAILABLE")],
)
def test_http_errors_map_and_never_succeed(status: int, code: str) -> None:
    transport = transport_for("chat/completions", json_response({"error": "x"}, status=status))
    result = _adapter(transport).execute(call(route_key=f"OPENROUTER:{_MODEL}"))
    assert result.status is not ExecutionStatus.SUCCEEDED
    assert result.error_code == code


def test_malformed_json_fails_closed() -> None:
    bad = HttpResponse(200, {"x-request-id": "r"}, b"not json{{")
    transport = transport_for("chat/completions", bad)
    result = _adapter(transport).execute(call(route_key=f"OPENROUTER:{_MODEL}"))
    assert result.error_code == "MALFORMED_OUTPUT"


def test_missing_choices_is_malformed() -> None:
    resp = json_response({"model": _MODEL, "provider": "openai"})
    transport = transport_for("chat/completions", resp)
    result = _adapter(transport).execute(call(route_key=f"OPENROUTER:{_MODEL}"))
    assert result.error_code == "MALFORMED_OUTPUT"


def test_local_only_task_is_refused() -> None:
    local = grant(expected_upstream="openai", privacy=Privacy.LOCAL_ONLY)
    transport = transport_for("chat/completions", json_response(chat_ok(_MODEL, provider="openai")))
    result = _adapter(transport, g=local).execute(call(route_key=f"OPENROUTER:{_MODEL}"))
    assert result.error_code == "NETWORK_DENIED"
    assert transport.sent == []


def test_no_cloud_grant_is_refused() -> None:
    transport = transport_for("chat/completions", json_response(chat_ok(_MODEL, provider="openai")))
    result = openrouter_adapter(
        transport, network_backend(), secret_backend(), StaticResolver(None),
    ).execute(call(route_key=f"OPENROUTER:{_MODEL}"))
    assert result.status is ExecutionStatus.RUNTIME_UNAVAILABLE
    assert result.error_code == "NETWORK_DENIED"


def test_unapproved_model_rejected_discovery_is_not_approval() -> None:
    resp = json_response(chat_ok("discovered/model", provider="openai"))
    transport = transport_for("chat/completions", resp)
    result = _adapter(transport).execute(call(route_key="OPENROUTER:discovered/model"))
    assert result.error_code == "MODEL_MISSING"
    assert transport.sent == []


def test_missing_credential_is_secret_unavailable() -> None:
    # secret backend has no material for ref R1
    from factory.secret.fake_backend import FakeSecretBackend
    transport = transport_for("chat/completions", json_response(chat_ok(_MODEL, provider="openai")))
    adapter = _adapter(transport, sec=FakeSecretBackend({}))
    result = adapter.execute(call(route_key=f"OPENROUTER:{_MODEL}"))
    assert result.error_code == "SECRET_UNAVAILABLE"
    assert transport.sent == []  # never sent without a key


def test_network_denied_when_host_not_approved() -> None:
    transport = transport_for("chat/completions", json_response(chat_ok(_MODEL, provider="openai")))
    g = grant(host="not-approved.example", expected_upstream="openai")
    result = _adapter(transport, g=g).execute(call(route_key=f"OPENROUTER:{_MODEL}"))
    assert result.error_code == "NETWORK_DENIED"
    assert transport.sent == []


def test_response_over_byte_ceiling_denied() -> None:
    big = json_response(chat_ok(_MODEL, provider="openai"))
    g = grant(expected_upstream="openai", max_bytes=1)  # 1-byte ceiling
    transport = transport_for("chat/completions", big)
    result = _adapter(transport, g=g).execute(call(route_key=f"OPENROUTER:{_MODEL}"))
    assert result.error_code == "RESPONSE_TOO_LARGE"


def test_redirect_to_unapproved_host_denied() -> None:
    redirected = HttpResponse(
        200, {"x-request-id": "r"}, json.dumps(chat_ok(_MODEL, provider="openai")).encode(),
        final_url="https://evil.example/api/v1/chat/completions",
    )

    def _m(req: HttpRequest) -> bool:
        return "chat/completions" in req.url
    transport = FakeHttpTransport((FakeExchange(_m, redirected),))
    result = _adapter(transport).execute(call(route_key=f"OPENROUTER:{_MODEL}"))
    assert result.error_code == "NETWORK_DENIED"


def test_tool_calls_extracted() -> None:
    transport = transport_for(
        "chat/completions", json_response(chat_ok(_MODEL, provider="openai", tools=["search"])),
    )
    result = _adapter(transport).execute(call(route_key=f"OPENROUTER:{_MODEL}"))
    assert result.tool_calls == ("search",)
