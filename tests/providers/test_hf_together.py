"""Provider tests — Hugging Face (explicit provider) + Together (endpoint identity + capability)."""

from __future__ import annotations

import pytest
from support import (
    StaticResolver,
    call,
    chat_ok,
    grant,
    json_response,
    network_backend,
    secret_backend,
    transport_for,
)

from factory.providers import (
    Capability,
    HuggingFaceAdapter,
    OpenAICompatibleAdapterCore,
    ProviderCapability,
    ProviderConfiguration,
    ProviderError,
    ProviderErrorCode,
    TogetherAdapter,
)
from factory.providers.brokered import BrokeredContext, BrokeredHttp
from factory.providers.hosted import HostedGrant
from factory.providers.openai_core import ChatMessage, ChatRequest
from factory.providers.transport import FakeHttpTransport
from factory.routing.models import ExecutionStatus, Privacy, Provider

pytestmark = pytest.mark.security

_HF = "meta-llama/Llama-3-8B-Instruct"
_TG = "meta-llama/Llama-3-70B"


def _hf(transport: FakeHttpTransport, g: HostedGrant) -> HuggingFaceAdapter:
    config = ProviderConfiguration(
        Provider.HUGGING_FACE, "https://router.huggingface.co/v1", "HF_TOKEN",
        frozenset({"router.huggingface.co"}),
    )
    return HuggingFaceAdapter(
        config, OpenAICompatibleAdapterCore(), transport, network_backend(),
        secret_backend(), StaticResolver(g), frozenset({_HF}), clock=lambda: 0,
    )


def _together(transport: FakeHttpTransport, g: HostedGrant) -> TogetherAdapter:
    config = ProviderConfiguration(
        Provider.TOGETHER, "https://api.together.xyz/v1", "TOGETHER_API_KEY",
        frozenset({"api.together.xyz"}),
    )
    return TogetherAdapter(
        config, OpenAICompatibleAdapterCore(), transport, network_backend(),
        secret_backend(), StaticResolver(g), frozenset({_TG}), clock=lambda: 0,
    )


@pytest.mark.parametrize("selector", ["", "auto", "fastest", "cheapest"])
def test_hf_strict_forbids_auto_selection(selector: str) -> None:
    transport = transport_for("chat/completions", json_response(chat_ok(_HF)))
    g = grant(host="router.huggingface.co", secret_name="HF_TOKEN",  # noqa: S106 - secret name/ref, not a value
              expected_upstream=selector, strict_upstream=True)
    result = _hf(transport, g).execute(call(route_key=f"HUGGING_FACE:{_HF}"))
    assert result.error_code == "CAPABILITY_UNAVAILABLE"


def test_hf_explicit_provider_accepted_and_verified() -> None:
    transport = transport_for("chat/completions", json_response(chat_ok(_HF, provider="together")))
    g = grant(host="router.huggingface.co", secret_name="HF_TOKEN", expected_upstream="together")  # noqa: S106 - secret name/ref, not a value
    result = _hf(transport, g).execute(call(route_key=f"HUGGING_FACE:{_HF}"))
    assert result.status is ExecutionStatus.SUCCEEDED


def test_hf_provider_mismatch_rejected() -> None:
    transport = transport_for("chat/completions", json_response(chat_ok(_HF, provider="fireworks")))
    g = grant(host="router.huggingface.co", secret_name="HF_TOKEN", expected_upstream="together")  # noqa: S106 - secret name/ref, not a value
    result = _hf(transport, g).execute(call(route_key=f"HUGGING_FACE:{_HF}"))
    assert result.error_code == "PROVIDER_MISMATCH"


def test_together_serverless_success_and_endpoint_identity() -> None:
    transport = transport_for("chat/completions", json_response(chat_ok(_TG)))
    g = grant(host="api.together.xyz", secret_name="TOGETHER_API_KEY",  # noqa: S106 - secret name/ref, not a value
              strict_upstream=False, endpoint_identity="serverless:together")
    result = _together(transport, g).execute(call(route_key=f"TOGETHER:{_TG}"))
    assert result.status is ExecutionStatus.SUCCEEDED
    assert result.fingerprint is not None
    assert result.fingerprint.endpoint_identity == "serverless:together"


def test_together_dedicated_endpoint_identity_preserved() -> None:
    transport = transport_for("chat/completions", json_response(chat_ok(_TG)))
    g = grant(host="api.together.xyz", secret_name="TOGETHER_API_KEY",  # noqa: S106 - secret name/ref, not a value
              strict_upstream=False, endpoint_identity="dedicated:ep-123")
    result = _together(transport, g).execute(call(route_key=f"TOGETHER:{_TG}"))
    assert result.fingerprint is not None
    assert result.fingerprint.endpoint_identity == "dedicated:ep-123"


def test_core_capability_enforcement_for_unsupported_feature() -> None:
    # Directly exercise the core's capability gate (tools requested but not advertised).
    core = OpenAICompatibleAdapterCore()
    config = ProviderConfiguration(
        Provider.TOGETHER, "https://api.together.xyz/v1", "TOGETHER_API_KEY",
        frozenset({"api.together.xyz"}),
    )
    transport = transport_for("chat/completions", json_response(chat_ok(_TG)))
    g = grant(host="api.together.xyz", secret_name="TOGETHER_API_KEY", strict_upstream=False)  # noqa: S106 - secret name/ref, not a value
    brokered = BrokeredHttp(transport, BrokeredContext(
        task_id="T1", privacy=Privacy.CLOUD_ALLOWED, network=network_backend(),
        approval=g.approval, secret=secret_backend(), secret_ref=g.secret_ref, now=0,
    ))
    chat = ChatRequest(
        model=_TG, messages=(ChatMessage("user", "hi"),),
        require=frozenset({Capability.TOOLS}),
        advertised=ProviderCapability(frozenset({Capability.CHAT})),
    )
    with pytest.raises(ProviderError) as exc:
        core.chat(config, brokered, chat)
    assert exc.value.code is ProviderErrorCode.CAPABILITY_UNAVAILABLE
