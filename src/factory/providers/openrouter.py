"""OpenRouter adapter (OpenAI-compatible core + strict routing policy).

Strict routes require an exact approved model slug and an explicit upstream provider. Hidden
fallback is disabled (``allow_fallbacks=false``), ``require_parameters=true``, data collection is
denied, and ZDR is requested when the route requires it. The returned model and upstream provider
are verified by the core (mismatch fails closed).
"""

from __future__ import annotations

from factory.providers.errors import ProviderError, ProviderErrorCode
from factory.providers.hosted import HostedAdapter, HostedGrant
from factory.providers.openai_core import ChatMessage, ChatRequest
from factory.routing.adapters.base import CallRequest


class OpenRouterAdapter(HostedAdapter):
    """Uses the shared OpenAI core; adds OpenRouter's strict provider policy."""

    __slots__ = ()

    def _shape(self, model_id: str, request: CallRequest, grant: HostedGrant) -> ChatRequest:
        provider_policy: dict[str, object] = {
            "allow_fallbacks": False,  # never let OpenRouter silently substitute
            "require_parameters": True,
            "data_collection": "deny",
        }
        if grant.require_zdr:
            provider_policy["zdr"] = True
        if grant.expected_upstream:
            provider_policy["order"] = [grant.expected_upstream]
        elif grant.strict_upstream:
            raise ProviderError(
                ProviderErrorCode.CAPABILITY_UNAVAILABLE,
                "strict OpenRouter route requires an explicit upstream provider",
            )
        return ChatRequest(
            model=model_id,
            messages=(ChatMessage("user", request.prompt),),
            max_tokens=request.max_tokens,
            extra_body=(("provider", provider_policy),),
            expected_upstream=grant.expected_upstream,
        )
