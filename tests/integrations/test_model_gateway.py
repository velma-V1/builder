import pytest

from factory.integrations.agent_zero.policy import AgentZeroModelResult
from factory.integrations.model_gateway import ModelGateway, ModelGatewayError
from factory.worker_engine.model_router import FakeModelRouter


def _gateway(ok: bool = True) -> ModelGateway:
    result = AgentZeroModelResult(
        ok, "answer" if ok else "", "f" * 64, "ollama:local", "offline" if not ok else ""
    )
    return ModelGateway(FakeModelRouter(default=result), "session-token", "devstral-pinned")


def test_gateway_authenticates_and_routes_only_selected_model() -> None:
    response = _gateway().complete(
        "Bearer session-token",
        {"model": "devstral-pinned", "messages": [{"role": "user", "content": "task"}]},
    )
    assert response["model"] == "devstral-pinned"
    assert response["choices"][0]["message"]["content"] == "answer"  # type: ignore[index]


@pytest.mark.parametrize("credential", ["", "Bearer wrong"])
def test_gateway_rejects_missing_or_wrong_session_credential(credential: str) -> None:
    with pytest.raises(ModelGatewayError, match="authentication"):
        _gateway().complete(credential, {"model": "devstral-pinned", "messages": []})


def test_gateway_fails_closed_on_substitution_streaming_or_unavailable_model() -> None:
    with pytest.raises(ModelGatewayError, match="selected"):
        _gateway().complete("Bearer session-token", {"model": "other", "messages": [{}]})
    with pytest.raises(ModelGatewayError, match="streaming"):
        _gateway().complete("Bearer session-token", {"model": "devstral-pinned", "stream": True})
    with pytest.raises(ModelGatewayError, match="offline"):
        _gateway(False).complete(
            "Bearer session-token",
            {"model": "devstral-pinned", "messages": [{"role": "user", "content": "task"}]},
        )


def test_gateway_rejects_router_substitution_even_when_call_succeeds() -> None:
    substituted = AgentZeroModelResult(True, "answer", "f" * 64, "hosted:fallback")
    gateway = ModelGateway(FakeModelRouter(default=substituted), "session-token", "devstral-pinned")
    with pytest.raises(ModelGatewayError, match="substitution"):
        gateway.complete(
            "Bearer session-token",
            {
                "model": "devstral-pinned",
                "messages": [{"role": "user", "content": "task"}],
            },
        )
