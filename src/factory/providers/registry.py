"""Hosted route approval + discovery catalog (discovery is READ-ONLY; approval is EXPLICIT).

A :class:`DiscoveredModel` may enter the :class:`HostedModelCatalog`; it **never** becomes an
approved route automatically. An :class:`ApprovedHostedRoute` is an explicit, fully-specified
declaration (provider, exact model + version, capabilities, privacy, cost ceiling, timeout, context,
domains, fallback policy, retention/ZDR, resource profile, role). The catalog cannot promote a
model — promotion is an out-of-band human decision.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from factory.providers.models import Capability, DiscoveredModel
from factory.routing.models import ModelRole, Privacy, Provider, ResourceClass


@dataclass(frozen=True, slots=True)
class ApprovedHostedRoute:
    """A fully-declared approved hosted route. Everything is explicit; nothing is inferred."""

    provider: Provider
    model_id: str
    role: ModelRole
    privacy_class: Privacy
    allowed_capabilities: frozenset[Capability]
    approved_domains: frozenset[str]
    resource_class: ResourceClass
    cost_ceiling_usd: float
    timeout_s: float
    context_limit: int
    model_version: str = ""  # exact version/digest when applicable (e.g. Replicate)
    upstream_provider: str = ""  # required for strict routes
    fallback_allowed: bool = False  # adapter fallback is always forbidden; router-only
    require_zdr: bool = False

    @property
    def route_key(self) -> str:
        return f"{self.provider.value}:{self.model_id}"


class HostedModelCatalog:
    """Read-only catalog of discovered models. Membership here is NOT approval."""

    __slots__ = ("_by_key",)

    def __init__(self) -> None:
        self._by_key: dict[str, DiscoveredModel] = {}

    def record(self, model: DiscoveredModel) -> None:
        """Record a discovered model. Idempotent; carries no approval semantics."""
        self._by_key[f"{model.provider.value}:{model.model_id}"] = model

    def is_catalogued(self, route_key: str) -> bool:
        return route_key in self._by_key

    def is_approved(self, route_key: str) -> bool:
        """A catalogued model is never approved by virtue of discovery. Always False."""
        return False

    def all(self) -> tuple[DiscoveredModel, ...]:
        return tuple(self._by_key.values())


@dataclass(frozen=True, slots=True)
class ApprovedHostedRoster:
    """An immutable set of explicitly approved hosted routes (parallel to ApprovedRoster)."""

    routes: tuple[ApprovedHostedRoute, ...] = field(default_factory=tuple)

    def approved_model_ids(self, provider: Provider) -> frozenset[str]:
        return frozenset(r.model_id for r in self.routes if r.provider is provider)

    def get(self, route_key: str) -> ApprovedHostedRoute | None:
        for route in self.routes:
            if route.route_key == route_key:
                return route
        return None
