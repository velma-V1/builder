"""Shared builders for provider adapter tests (deterministic fakes only; no real endpoints/keys)."""

from __future__ import annotations

import json
from collections.abc import Mapping

from factory.network.broker import NetworkBroker
from factory.network.fake_backend import FakeNetworkBackend
from factory.network.models import NetworkApproval
from factory.providers import (
    OpenAICompatibleAdapterCore,
    OpenRouterAdapter,
    ProviderConfiguration,
)
from factory.providers.hosted import HostedGrant
from factory.providers.transport import FakeExchange, FakeHttpTransport, HttpRequest, HttpResponse
from factory.routing.adapters.base import CallRequest
from factory.routing.models import Privacy, Provider
from factory.secret.broker import SecretBroker
from factory.secret.fake_backend import FakeSecretBackend
from factory.secret.models import SecretRef

APPROVED_HOST = "openrouter.ai"
SECRET_NAME = "OPENROUTER_API_KEY"  # noqa: S105 - a secret *name*/ref, not a value
SECRET_VALUE = "sk-fake-do-not-use-000000"  # noqa: S105 - dummy test material, never a real key
DEFAULT_MODEL = "openai/gpt-x"


class StaticResolver:
    """A GrantResolver that returns a fixed grant (or None to model 'no cloud grant')."""

    def __init__(self, grant: HostedGrant | None) -> None:
        self._grant = grant

    def resolve(self, task_id: str) -> HostedGrant | None:
        return self._grant


def approval(
    host: str = APPROVED_HOST, *, task_id: str = "T1", max_bytes: int = 1_000_000
) -> NetworkApproval:
    return NetworkApproval(
        approval_id="A1",
        task_id=task_id,
        destinations=frozenset({host}),
        protocols=frozenset({"https"}),
        methods=frozenset({"GET", "POST"}),
        expires_at=10_000,
        max_total_bytes=max_bytes,
        follow_redirects=True,
    )


def grant(
    *,
    host: str = APPROVED_HOST,
    task_id: str = "T1",
    secret_name: str = SECRET_NAME,
    expected_upstream: str = "",
    strict_upstream: bool = True,
    require_zdr: bool = False,
    endpoint_identity: str = "",
    region: str = "",
    privacy: Privacy = Privacy.CLOUD_ALLOWED,
    max_bytes: int = 1_000_000,
) -> HostedGrant:
    return HostedGrant(
        privacy=privacy,
        approval=approval(host, task_id=task_id, max_bytes=max_bytes),
        secret_ref=SecretRef("R1", secret_name, task_id, max_ttl=100),
        expected_upstream=expected_upstream,
        strict_upstream=strict_upstream,
        require_zdr=require_zdr,
        endpoint_identity=endpoint_identity,
        region=region,
    )


def secret_backend(value: str = SECRET_VALUE, *, ref_id: str = "R1") -> FakeSecretBackend:
    # FakeSecretBackend keys material by ref_id (matches SecretRef.ref_id used in grant()).
    return FakeSecretBackend({ref_id: value})


def network_backend() -> FakeNetworkBackend:
    return FakeNetworkBackend()


def call(
    prompt: str = "hello", *, route_key: str = f"OPENROUTER:{DEFAULT_MODEL}", task_id: str = "T1"
) -> CallRequest:
    return CallRequest(
        task_id=task_id,
        stage_id="S1",
        route_key=route_key,
        prompt=prompt,
        max_tokens=64,
        timeout=30,
    )


def json_response(
    payload: Mapping[str, object], *, status: int = 200, headers: Mapping[str, str] | None = None
) -> HttpResponse:
    return HttpResponse(
        status,
        dict(headers or {"x-request-id": "req-1"}),
        json.dumps(payload).encode("utf-8"),
    )


def chat_ok(
    model: str, *, provider: str = "", content: str = "hi", tools: list[str] | None = None
) -> dict[str, object]:
    message: dict[str, object] = {"role": "assistant", "content": content}
    if tools:
        message["tool_calls"] = [{"function": {"name": t}} for t in tools]
    body: dict[str, object] = {
        "id": "gen-1",
        "model": model,
        "choices": [{"message": message}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 7},
    }
    if provider:
        body["provider"] = provider
    return body


def transport_for(match_substr: str, response: HttpResponse) -> FakeHttpTransport:
    def _m(req: HttpRequest) -> bool:
        return match_substr in req.url

    return FakeHttpTransport((FakeExchange(_m, response),))


def openrouter_adapter(
    transport: FakeHttpTransport,
    net: NetworkBroker,
    sec: SecretBroker,
    resolver: StaticResolver,
    approved: frozenset[str] = frozenset({DEFAULT_MODEL}),
) -> OpenRouterAdapter:
    config = ProviderConfiguration(
        Provider.OPENROUTER,
        "https://openrouter.ai/api/v1",
        SECRET_NAME,
        frozenset({APPROVED_HOST}),
    )
    return OpenRouterAdapter(
        config,
        OpenAICompatibleAdapterCore(),
        transport,
        net,
        sec,
        resolver,
        approved,
        clock=lambda: 0,
    )
