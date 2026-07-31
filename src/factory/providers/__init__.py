"""Hosted provider adapters (BUILT, not activated).

A shared OpenAI-compatible core drives OpenRouter / Hugging Face / Together; Replicate uses a
separate prediction lifecycle. Every hosted call goes through the brokered security envelope
(privacy → approval → secret lease → redirect check → byte charge → redaction). No live
call is possible here: the only transport is the deterministic fake, and no credentials are read.
"""

from __future__ import annotations

from factory.providers.brokered import BrokeredContext, BrokeredHttp
from factory.providers.errors import (
    ProviderError,
    ProviderErrorCode,
    map_http_status,
    status_for,
)
from factory.providers.hosted import (
    GrantResolver,
    HostedAdapter,
    HostedGrant,
    HostedResult,
)
from factory.providers.huggingface import HuggingFaceAdapter
from factory.providers.models import (
    Capability,
    CostRecord,
    DiscoveredModel,
    ProviderCapability,
    ProviderConfiguration,
    ProviderFingerprint,
    ProviderResponseMetadata,
    UsageRecord,
)
from factory.providers.openai_core import (
    ChatMessage,
    ChatRequest,
    CoreChatResult,
    OpenAICompatibleAdapterCore,
)
from factory.providers.openrouter import OpenRouterAdapter
from factory.providers.registry import (
    ApprovedHostedRoster,
    ApprovedHostedRoute,
    HostedModelCatalog,
)
from factory.providers.replicate import (
    ApprovedReplicateRoute,
    PredictionState,
    ReplicateAdapter,
    ReplicatePrediction,
)
from factory.providers.together import TogetherAdapter
from factory.providers.transport import (
    FakeExchange,
    FakeHttpTransport,
    HttpRequest,
    HttpResponse,
    HttpTransport,
    TransportFailure,
    TransportTimeout,
)

__all__ = [
    "ApprovedHostedRoster",
    "ApprovedHostedRoute",
    "ApprovedReplicateRoute",
    "BrokeredContext",
    "BrokeredHttp",
    "Capability",
    "ChatMessage",
    "ChatRequest",
    "CoreChatResult",
    "CostRecord",
    "DiscoveredModel",
    "FakeExchange",
    "FakeHttpTransport",
    "GrantResolver",
    "HostedAdapter",
    "HostedGrant",
    "HostedModelCatalog",
    "HostedResult",
    "HttpRequest",
    "HttpResponse",
    "HttpTransport",
    "HuggingFaceAdapter",
    "OpenAICompatibleAdapterCore",
    "OpenRouterAdapter",
    "PredictionState",
    "ProviderCapability",
    "ProviderConfiguration",
    "ProviderError",
    "ProviderErrorCode",
    "ProviderFingerprint",
    "ProviderResponseMetadata",
    "ReplicateAdapter",
    "ReplicatePrediction",
    "TogetherAdapter",
    "TransportFailure",
    "TransportTimeout",
    "UsageRecord",
    "map_http_status",
    "status_for",
]
