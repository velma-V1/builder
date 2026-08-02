"""WorldMonitor trust boundaries: brokered network, optional secret, and model authority.

* **Network** — all WorldMonitor traffic goes through the :class:`NetworkBroker` under a task-scoped
  approval (explicit domain allowlist, redirect validation, byte ceiling). No direct network.
* **Secret** — optional WorldMonitor credentials are leased from the :class:`SecretBroker`; keys
  are never read from the environment, persisted, or logged.
* **Model authority** — WorldMonitor MUST NOT select a provider, load/unload models, or call
  Ollama/cloud directly. An AI need is expressed as a capability request to the Builder router
  (:class:`ModelRouterPort`); Builder selects the route and enforces privacy/cost/resources.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable
from urllib.parse import urlsplit

from factory.integrations.worldmonitor.errors import WorldMonitorError, WorldMonitorErrorCode
from factory.network.broker import NetworkBroker
from factory.network.models import Direction, NetworkApproval, NetworkRequest
from factory.providers.transport import (
    HttpRequest,
    HttpResponse,
    HttpTransport,
    TransportFailure,
    TransportTimeout,
)
from factory.routing.models import Privacy
from factory.secret.broker import SecretBroker
from factory.secret.errors import SecretError
from factory.secret.models import SecretRef


@dataclass(frozen=True, slots=True)
class AiCapabilityRequest:
    """What WorldMonitor asks Builder for — a capability, never a provider/model choice."""

    task_id: str
    capability: str  # e.g. "summarize", "classify_risk"
    prompt: str
    privacy: Privacy = Privacy.LOCAL_ONLY  # local-first; hosted requires CLOUD_ALLOWED
    max_tokens: int = 512


@dataclass(frozen=True, slots=True)
class AiResult:
    ok: bool
    output: str
    model_fingerprint: str
    provider_route: str
    reason: str = ""


@runtime_checkable
class ModelRouterPort(Protocol):
    """The ONLY way WorldMonitor obtains AI: Builder routes it. WM holds no provider adapter."""

    def request(self, capability: AiCapabilityRequest) -> AiResult: ...


@dataclass(frozen=True, slots=True)
class WorldMonitorNetworkPolicy:
    task_id: str
    approval: NetworkApproval
    #: Optional secret; None means no credential is used (local mode).
    secret_ref: SecretRef | None = None
    privacy: Privacy = Privacy.LOCAL_ONLY


def _host(url: str) -> str:
    return urlsplit(url).hostname or ""


class BrokeredWorldMonitorHttp:
    """Every WorldMonitor HTTP call passes through here: broker + optional secret + redaction."""

    __slots__ = ("_network", "_now", "_policy", "_secret", "_transport")

    def __init__(
        self,
        transport: HttpTransport,
        network: NetworkBroker,
        secret: SecretBroker,
        policy: WorldMonitorNetworkPolicy,
        now: int,
    ) -> None:
        self._transport = transport
        self._network = network
        self._secret = secret
        self._policy = policy
        self._now = now

    def redact(self, text: str) -> str:
        return self._secret.redact(text, self._now)

    def request(
        self,
        method: str,
        url: str,
        *,
        body: bytes = b"",
        headers: dict[str, str] | None = None,
    ) -> HttpResponse:
        policy = self._policy
        host = _host(url)
        decision = self._network.evaluate(
            policy.approval,
            NetworkRequest(host, "https", method, Direction.OUTBOUND),
            self._now,
        )
        if not decision.allowed:
            raise WorldMonitorError(
                WorldMonitorErrorCode.NETWORK_DENIED, f"network denied: {decision.code or host}"
            )
        request_headers = dict(headers or {})
        lease_ref: str | None = None
        try:
            if policy.secret_ref is not None:
                try:
                    lease = self._secret.inject(policy.secret_ref, self._now)
                except SecretError as exc:
                    raise WorldMonitorError(
                        WorldMonitorErrorCode.SECRET_UNAVAILABLE, f"secret: {exc.code}"
                    ) from exc
                lease_ref = policy.secret_ref.ref_id
                request_headers["Authorization"] = f"Bearer {lease.value}"
            try:
                response = self._transport.send(HttpRequest(method, url, request_headers, body))
            except TransportTimeout as exc:
                raise WorldMonitorError(
                    WorldMonitorErrorCode.TIMED_OUT, self.redact(str(exc))
                ) from exc
            except TransportFailure as exc:
                raise WorldMonitorError(
                    WorldMonitorErrorCode.UNAVAILABLE, self.redact(str(exc))
                ) from exc
            final = response.final_url or url
            if _host(final) != host:
                redirect = self._network.evaluate_redirect(policy.approval, _host(final), self._now)
                if not redirect.allowed:
                    raise WorldMonitorError(
                        WorldMonitorErrorCode.NETWORK_DENIED, f"redirect denied to {_host(final)}"
                    )
            charge = self._network.charge(policy.approval, len(response.body))
            if not charge.allowed:
                raise WorldMonitorError(
                    WorldMonitorErrorCode.RESPONSE_TOO_LARGE, f"transfer denied: {charge.code}"
                )
            return response
        finally:
            if lease_ref is not None:
                self._secret.revoke(lease_ref)
