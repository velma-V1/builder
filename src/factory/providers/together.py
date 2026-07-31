"""Together adapter (OpenAI-compatible core; serverless vs dedicated endpoint identity).

Requires an exact approved serverless model **or** a dedicated-endpoint identifier. The endpoint
identity (serverless model id vs dedicated endpoint) is preserved on the fingerprint. Only
documented parameters are sent; unsupported parameters are never sent (fail closed at the
core's capability check).
"""

from __future__ import annotations

from factory.providers.hosted import HostedAdapter, HostedGrant
from factory.providers.openai_core import ChatMessage, ChatRequest
from factory.routing.adapters.base import CallRequest


class TogetherAdapter(HostedAdapter):
    __slots__ = ()

    def _shape(self, model_id: str, request: CallRequest, grant: HostedGrant) -> ChatRequest:
        # Together is OpenAI-compatible; endpoint identity (serverless vs dedicated) rides on the
        # grant and is folded into the fingerprint by the base. Only documented fields are sent.
        return ChatRequest(
            model=model_id,
            messages=(ChatMessage("user", request.prompt),),
            max_tokens=request.max_tokens,
            expected_upstream=grant.expected_upstream,
        )
