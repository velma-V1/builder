"""Provider-neutral value types + versioned fingerprint.

These describe hosted providers without disturbing the Ollama-specific
:class:`~factory.routing.models.ModelFingerprint` (legacy digests stay reproducible). Hosted calls
use the new :class:`ProviderFingerprint` (``schema_version = 2``); the legacy schema is untouched.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import StrEnum

from factory.routing.models import Provider

_SEP = "\x1f"
PROVIDER_FINGERPRINT_SCHEMA = 2


class Capability(StrEnum):
    CHAT = "chat"
    TOOLS = "tools"
    STRUCTURED_OUTPUT = "structured_output"
    STREAMING = "streaming"
    VISION = "vision"
    PREDICTION = "prediction"  # Replicate-style async prediction


@dataclass(frozen=True, slots=True)
class ProviderConfiguration:
    """Static, non-secret configuration for a hosted provider (no key material)."""

    provider: Provider
    base_url: str
    #: Name of the secret the SecretBroker will lease (never the value).
    secret_name: str
    approved_domains: frozenset[str]
    api_version: str = "v1"
    timeout_s: float = 30.0
    max_response_bytes: int = 8 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class ProviderCapability:
    """A provider/model's advertised capabilities (from read-only discovery)."""

    capabilities: frozenset[Capability]
    context_window: int = 0

    def supports(self, capability: Capability) -> bool:
        return capability in self.capabilities

    def digest(self) -> str:
        joined = ",".join(sorted(c.value for c in self.capabilities))
        return hashlib.sha256(f"{joined}|{self.context_window}".encode()).hexdigest()[:16]


@dataclass(frozen=True, slots=True)
class DiscoveredModel:
    """A model observed via read-only discovery. A catalog entry — NOT an approval."""

    provider: Provider
    model_id: str
    capability: ProviderCapability
    upstream_provider: str = ""
    discovered_at: int = 0


@dataclass(frozen=True, slots=True)
class UsageRecord:
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass(frozen=True, slots=True)
class CostRecord:
    currency: str = "USD"
    prompt_cost: float = 0.0
    completion_cost: float = 0.0
    #: Whether pricing metadata was actually supplied by the provider (else costs are unknown, 0.0).
    priced: bool = False

    @property
    def total_cost(self) -> float:
        return self.prompt_cost + self.completion_cost


@dataclass(frozen=True, slots=True)
class ProviderResponseMetadata:
    """What a hosted call actually returned (used to verify against what was requested)."""

    request_id: str = ""
    returned_model: str = ""
    upstream_provider: str = ""
    endpoint_identity: str = ""
    region: str = ""
    usage: UsageRecord = field(default_factory=UsageRecord)
    cost: CostRecord = field(default_factory=CostRecord)


@dataclass(frozen=True, slots=True)
class ProviderFingerprint:
    """Versioned, provider-neutral fingerprint (``schema_version = 2``) for hosted executions."""

    provider: Provider
    model_id: str
    model_version_or_digest: str
    upstream_provider: str
    endpoint_identity: str
    runtime_or_api_version: str
    context_window: int
    capability_digest: str
    sampling: tuple[tuple[str, str], ...]
    system_prompt_version: str
    tool_schema_version: str
    adapter_version: str
    routing_policy_version: str
    execution_region: str = ""
    schema_version: int = PROVIDER_FINGERPRINT_SCHEMA

    def digest(self) -> str:
        parts = [
            f"schema={self.schema_version}",
            self.provider.value,
            self.model_id,
            self.model_version_or_digest,
            self.upstream_provider,
            self.endpoint_identity,
            self.runtime_or_api_version,
            str(self.context_window),
            self.capability_digest,
            _SEP.join(f"{k}={v}" for k, v in sorted(self.sampling)),
            self.system_prompt_version,
            self.tool_schema_version,
            self.adapter_version,
            self.routing_policy_version,
            self.execution_region,
        ]
        return hashlib.sha256(_SEP.join(parts).encode("utf-8")).hexdigest()
