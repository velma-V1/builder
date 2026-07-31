"""Hugging Face Inference Providers adapter (OpenAI-compatible core, strict provider selection).

Strict routes require an exact model and an **explicit inference provider**. Automatic /
fastest / cheapest routing is forbidden unless the route is separately authorized (a non-strict
grant). The actual provider is verified by the core when returned (mismatch fails closed).
"""

from __future__ import annotations

from factory.providers.errors import ProviderError, ProviderErrorCode
from factory.providers.hosted import HostedAdapter, HostedGrant
from factory.providers.openai_core import ChatMessage, ChatRequest
from factory.routing.adapters.base import CallRequest

_AUTO_SELECTORS = frozenset({"auto", "fastest", "cheapest", ""})


class HuggingFaceAdapter(HostedAdapter):
    __slots__ = ()

    def _shape(self, model_id: str, request: CallRequest, grant: HostedGrant) -> ChatRequest:
        provider = grant.expected_upstream.strip().lower()
        if grant.strict_upstream and provider in _AUTO_SELECTORS:
            raise ProviderError(
                ProviderErrorCode.CAPABILITY_UNAVAILABLE,
                "strict Hugging Face route requires an explicit inference provider "
                "(auto/fastest/cheapest forbidden)",
            )
        extra: tuple[tuple[str, object], ...] = (
            (("provider", grant.expected_upstream),) if grant.expected_upstream else ()
        )
        return ChatRequest(
            model=model_id,
            messages=(ChatMessage("user", request.prompt),),
            max_tokens=request.max_tokens,
            extra_body=extra,
            expected_upstream=grant.expected_upstream,
        )
