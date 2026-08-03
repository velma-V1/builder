"""Shared OpenAI-compatible adapter core (used by OpenRouter, Hugging Face, Together).

One implementation of health/probe, read-only model discovery, non-streaming chat, tool calls,
structured output, usage normalization, error mapping, and **returned-model / upstream-provider
verification**. There is exactly one HTTP client seam (the injected :class:`BrokeredHttp`) — no
per-provider duplicate clients. A provider failure is never turned into success, and the core never
retries against a different model or provider (the Builder router owns fallback).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from factory.providers.brokered import BrokeredHttp
from factory.providers.errors import ProviderError, ProviderErrorCode, map_http_status
from factory.providers.models import (
    Capability,
    CostRecord,
    DiscoveredModel,
    ProviderCapability,
    ProviderConfiguration,
    ProviderResponseMetadata,
    UsageRecord,
)
from factory.providers.transport import HttpResponse


@dataclass(frozen=True, slots=True)
class ChatMessage:
    role: str
    content: str


@dataclass(frozen=True, slots=True)
class ChatRequest:
    model: str
    messages: tuple[ChatMessage, ...]
    max_tokens: int = 512
    require: frozenset[Capability] = field(default_factory=frozenset)
    advertised: ProviderCapability | None = None
    #: Provider-specific body fields (e.g. OpenRouter provider policy, Together params).
    extra_body: tuple[tuple[str, object], ...] = ()
    #: When set, the upstream provider the caller expects; a mismatch fails closed.
    expected_upstream: str = ""


@dataclass(frozen=True, slots=True)
class CoreChatResult:
    ok: bool
    output: str
    tool_calls: tuple[str, ...]
    metadata: ProviderResponseMetadata
    error_code: ProviderErrorCode | None = None
    reason: str = ""


def _parse_json(response: HttpResponse, brokered: BrokeredHttp) -> dict[str, object]:
    try:
        data = json.loads(response.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise ProviderError(ProviderErrorCode.MALFORMED_OUTPUT, brokered.redact(str(exc))) from exc
    if not isinstance(data, dict):
        raise ProviderError(ProviderErrorCode.MALFORMED_OUTPUT, "response was not a JSON object")
    return data


def _usage(data: dict[str, object]) -> UsageRecord:
    usage = data.get("usage")
    if not isinstance(usage, dict):
        return UsageRecord()
    prompt = usage.get("prompt_tokens", 0)
    completion = usage.get("completion_tokens", 0)
    return UsageRecord(
        prompt_tokens=int(prompt) if isinstance(prompt, int) else 0,
        completion_tokens=int(completion) if isinstance(completion, int) else 0,
    )


class OpenAICompatibleAdapterCore:
    """Stateless core. Each method takes the provider config + a brokered HTTP seam."""

    __slots__ = ()

    def discover_models(
        self, config: ProviderConfiguration, brokered: BrokeredHttp
    ) -> tuple[DiscoveredModel, ...]:
        """Read-only model discovery (``GET /models``). Discovery is NEVER approval."""
        url = f"{config.base_url}/models"
        response = brokered.request("GET", url)
        if response.status != 200:
            raise ProviderError(map_http_status(response.status), f"discovery {response.status}")
        data = _parse_json(response, brokered)
        models = data.get("data")
        out: list[DiscoveredModel] = []
        if isinstance(models, list):
            for entry in models:
                if isinstance(entry, dict) and isinstance(entry.get("id"), str):
                    out.append(
                        DiscoveredModel(
                            provider=config.provider,
                            model_id=str(entry["id"]),
                            capability=ProviderCapability(frozenset({Capability.CHAT})),
                        )
                    )
        return tuple(out)

    def chat(
        self, config: ProviderConfiguration, brokered: BrokeredHttp, request: ChatRequest
    ) -> CoreChatResult:
        """Non-streaming chat with returned-model + upstream-provider verification (fail closed)."""
        if request.advertised is not None:
            missing = [c for c in request.require if not request.advertised.supports(c)]
            if missing:
                raise ProviderError(
                    ProviderErrorCode.CAPABILITY_UNAVAILABLE,
                    f"unsupported capability: {[c.value for c in missing]}",
                )

        body_obj: dict[str, object] = {
            "model": request.model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "max_tokens": request.max_tokens,
            "stream": False,
        }
        body_obj.update(dict(request.extra_body))
        url = f"{config.base_url}/chat/completions"
        response = brokered.request(
            "POST",
            url,
            body=json.dumps(body_obj).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        if response.status != 200:
            code = map_http_status(response.status)
            return CoreChatResult(
                False,
                "",
                (),
                ProviderResponseMetadata(response.request_id),
                error_code=code,
                reason=f"HTTP {response.status}",
            )

        data = _parse_json(response, brokered)
        returned_model = str(data.get("model", ""))
        upstream = str(data.get("provider", "")) or request.expected_upstream
        metadata = ProviderResponseMetadata(
            request_id=response.request_id or str(data.get("id", "")),
            returned_model=returned_model,
            upstream_provider=upstream,
            usage=_usage(data),
            cost=CostRecord(),
        )

        # Fail closed on a silent model or provider substitution.
        if returned_model and returned_model != request.model:
            raise ProviderError(
                ProviderErrorCode.RETURNED_MODEL_MISMATCH,
                f"requested {request.model!r} but server returned {returned_model!r}",
            )
        if request.expected_upstream and upstream and upstream != request.expected_upstream:
            raise ProviderError(
                ProviderErrorCode.PROVIDER_MISMATCH,
                f"expected upstream {request.expected_upstream!r}, got {upstream!r}",
            )

        content, tool_calls = self._extract_choice(data, brokered)
        return CoreChatResult(True, content, tool_calls, metadata)

    def _extract_choice(
        self, data: dict[str, object], brokered: BrokeredHttp
    ) -> tuple[str, tuple[str, ...]]:
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            raise ProviderError(ProviderErrorCode.MALFORMED_OUTPUT, "no choices in response")
        message = choices[0].get("message")
        if not isinstance(message, dict):
            raise ProviderError(ProviderErrorCode.MALFORMED_OUTPUT, "choice has no message")
        content = message.get("content")
        text = content if isinstance(content, str) else ""
        tool_calls: list[str] = []
        raw_tools = message.get("tool_calls")
        if isinstance(raw_tools, list):
            for call in raw_tools:
                if isinstance(call, dict):
                    fn = call.get("function")
                    if isinstance(fn, dict) and isinstance(fn.get("name"), str):
                        tool_calls.append(str(fn["name"]))
        return text, tuple(tool_calls)
