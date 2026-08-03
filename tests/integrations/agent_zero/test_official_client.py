import json

import pytest

from factory.integrations.agent_zero.official_client import (
    AgentZeroOfficialClient,
    AgentZeroOfficialError,
)
from factory.providers.transport import FakeExchange, FakeHttpTransport, HttpResponse


def _response(payload: dict[str, object], status: int = 200) -> HttpResponse:
    return HttpResponse(status, {}, json.dumps(payload).encode(), "http://127.0.0.1:50080")


def _client(transport: FakeHttpTransport) -> AgentZeroOfficialClient:
    return AgentZeroOfficialClient(
        base_url="http://127.0.0.1:50080",
        api_key="session-only-key",
        transport=transport,
        timeout_s=30,
    )


def test_async_contract_establishes_csrf_starts_and_polls_context() -> None:
    transport = FakeHttpTransport(
        (
            FakeExchange(
                lambda request: request.url.endswith("/api/csrf_token"),
                HttpResponse(
                    200,
                    {"Set-Cookie": "session=abc; HttpOnly"},
                    json.dumps({"ok": True, "token": "csrf", "runtime_id": "r1"}).encode(),
                ),
            ),
            FakeExchange(
                lambda request: request.url.endswith("/api/message_async"),
                _response({"message": "Message received.", "context": "ctx-async"}),
            ),
            FakeExchange(
                lambda request: request.url.endswith("/api/poll"),
                _response(
                    {
                        "context": "ctx-async",
                        "log_progress_active": False,
                        "logs": [{"type": "response", "content": "patch ready"}],
                    }
                ),
            ),
        )
    )
    client = _client(transport)
    context = client.start_async('{"work_order_id":"wo-1"}')
    poll = client.poll(context)
    assert context == "ctx-async"
    assert poll.response == "patch ready" and poll.running is False
    assert transport.sent[1].headers["X-CSRF-Token"] == "csrf"
    assert transport.sent[1].headers["Cookie"] == "session=abc"


def test_poll_ignores_greeting_demo_response_until_user_message_turn_completes() -> None:
    def poll_payload(logs: list[dict[str, object]]) -> dict[str, object]:
        return {"context": "ctx-race", "log_progress_active": False, "logs": logs}

    csrf = FakeExchange(
        lambda request: request.url.endswith("/api/csrf_token"),
        HttpResponse(200, {"Set-Cookie": "session=s"}, b'{"ok":true,"token":"t"}'),
    )
    transport = FakeHttpTransport(
        (
            csrf,
            FakeExchange(
                lambda request: request.url.endswith("/api/poll"),
                _response(
                    poll_payload(
                        [
                            {"type": "response", "content": "**Hello! 👋**, I'm **Agent Zero**"},
                            {"type": "user", "content": "Reply with exactly: LIVE-MODEL-OK"},
                        ]
                    )
                ),
            ),
        )
    )
    client = _client(transport)

    assert client.poll("ctx-race").response is None

    transport2 = FakeHttpTransport(
        (
            csrf,
            FakeExchange(
                lambda request: request.url.endswith("/api/poll"),
                _response(
                    poll_payload(
                        [
                            {"type": "response", "content": "**Hello! 👋**, I'm **Agent Zero**"},
                            {"type": "user", "content": "Reply with exactly: LIVE-MODEL-OK"},
                            {"type": "response", "content": "LIVE-MODEL-OK"},
                        ]
                    )
                ),
            ),
        )
    )

    assert _client(transport2).poll("ctx-race").response == "LIVE-MODEL-OK"


def test_async_contract_rejects_missing_context_and_malformed_poll() -> None:
    missing = FakeHttpTransport(
        (
            FakeExchange(
                lambda request: request.url.endswith("/api/csrf_token"),
                HttpResponse(200, {"Set-Cookie": "session=x"}, b'{"ok":true,"token":"t"}'),
            ),
            FakeExchange(lambda _request: True, _response({"message": "received"})),
        )
    )
    with pytest.raises(AgentZeroOfficialError, match="context"):
        _client(missing).start_async("{}")


def test_probe_uses_official_health_endpoint_without_sending_secret() -> None:
    transport = FakeHttpTransport(
        (FakeExchange(lambda request: request.url.endswith("/api/health"), _response({})),)
    )

    _client(transport).probe()

    assert transport.sent[0].method == "GET"
    assert "X-API-KEY" not in transport.sent[0].headers


def test_cancel_uses_official_terminate_chat_contract() -> None:
    transport = FakeHttpTransport(
        (
            FakeExchange(
                lambda request: request.url.endswith("/api/api_terminate_chat"),
                _response({"success": True, "context_id": "ctx-1"}),
            ),
        )
    )

    assert _client(transport).cancel("ctx-1") is True
    assert json.loads(transport.sent[0].body) == {"context_id": "ctx-1"}


def test_logs_use_official_bounded_log_endpoint() -> None:
    transport = FakeHttpTransport(
        (
            FakeExchange(
                lambda request: "/api/api_log_get?" in request.url,
                _response({"context_id": "ctx-1", "log": {"items": [{"content": "ok"}]}}),
            ),
        )
    )

    assert _client(transport).logs("ctx-1", length=25) == ({"content": "ok"},)
    assert "length=25" in transport.sent[0].url


def test_malformed_or_failed_response_fails_closed_without_leaking_key() -> None:
    transport = FakeHttpTransport(
        (FakeExchange(lambda _request: True, HttpResponse(401, {}, b"bad key")),)
    )

    with pytest.raises(AgentZeroOfficialError, match="HTTP 401") as raised:
        _client(transport).cancel("ctx")

    assert "session-only-key" not in str(raised.value)
