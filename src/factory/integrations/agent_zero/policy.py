"""Agent Zero trust boundaries: brokered network, no secret, model-router-only AI, sandbox posture,
path scope, and explicit denial of every authority Agent Zero must never hold.

* **Network** — any outbound call the adapter makes on Agent Zero's behalf goes through the
  :class:`NetworkBroker` under a task-scoped approval. No direct network.
* **Secret** — structurally absent: nothing in this module (or anywhere in this package) accepts a
  :class:`~factory.secret.broker.SecretBroker` or a provider API key. There is no code path that
  could inject one.
* **Model authority** — Agent Zero MUST NOT select a provider, load a model, or call a provider
  directly. An AI need is expressed as a capability request to the Builder router
  (:class:`ModelRouterPort`); Builder selects the route and enforces privacy/cost/resources.
* **Sandbox posture** — :func:`enforce_sandbox_boundary` reuses
  :func:`factory.sandbox.policy.evaluate_spec` (never a weaker, bespoke check) and additionally
  fails closed with ``DOCKER_SOCKET_DENIED`` for a host Docker/container-runtime socket request.
* **Path scope** — :func:`evaluate_output_path` reuses
  :class:`~factory.contracts.validation.paths.PathAuthority` (never a bespoke traversal/symlink/UNC
  check) for every patch/artifact path Agent Zero proposes.
* **Authority denial** — direct ``main`` access, merge/approval/promotion authority, self-
  certification, self-update, and hidden scheduling are each denied by an explicit guard below, not
  merely "not implemented".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable
from urllib.parse import urlsplit

from factory.contracts.validation.paths import PathAuthority, PathAuthorityResult
from factory.integrations.agent_zero.errors import AgentZeroError, AgentZeroErrorCode
from factory.integrations.agent_zero.models import AgentZeroResult, WorkOrder
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
from factory.sandbox.models import SandboxSpec
from factory.sandbox.policy import evaluate_spec

#: Branch refs Agent Zero must never be granted direct access to.
_PROTECTED_BRANCHES = frozenset({"main", "master"})

#: Free-form ``worker_self_report`` keys whose truthy value is a self-certification attempt.
_SELF_CERTIFICATION_KEYS = frozenset({"verified", "certified", "approved"})

#: Free-form ``worker_self_report`` keys whose truthy value is a self-promotion attempt.
_SELF_PROMOTION_KEYS = frozenset({"promoted", "merged", "published"})

#: WorkOrder payload/self-report keys that would smuggle a self-scheduled/recurring run.
_SCHEDULING_KEYS = frozenset({"scheduled_at", "cron", "recurring", "next_run_at"})

_TRUTHY = frozenset({"true", "1", "yes"})


@dataclass(frozen=True, slots=True)
class AgentZeroCapabilityRequest:
    """What Agent Zero asks Builder for — a capability, never a provider/model choice."""

    task_id: str
    capability: str
    prompt: str
    privacy: Privacy = Privacy.LOCAL_ONLY
    max_tokens: int = 512


@dataclass(frozen=True, slots=True)
class AgentZeroModelResult:
    ok: bool
    output: str
    model_fingerprint: str
    provider_route: str
    reason: str = ""


@runtime_checkable
class ModelRouterPort(Protocol):
    """The ONLY way Agent Zero obtains AI: Builder routes it. Agent Zero holds no provider
    adapter."""

    def request(self, capability: AgentZeroCapabilityRequest) -> AgentZeroModelResult: ...


@dataclass(frozen=True, slots=True)
class AgentZeroNetworkPolicy:
    task_id: str
    approval: NetworkApproval
    #: Fixed at LOCAL_ONLY: Agent Zero's own outbound traffic never carries a cloud-privacy grant.
    privacy: Privacy = Privacy.LOCAL_ONLY


def _host(url: str) -> str:
    return urlsplit(url).hostname or ""


class BrokeredAgentZeroHttp:
    """Every outbound call the adapter makes for Agent Zero passes through here: broker only.

    No ``SecretBroker`` parameter exists on this class — there is no way to construct an instance
    that could inject a secret, which is how "Agent Zero must never receive a provider API key" is
    enforced structurally rather than by convention.
    """

    __slots__ = ("_network", "_now", "_policy", "_transport")

    def __init__(
        self,
        transport: HttpTransport,
        network: NetworkBroker,
        policy: AgentZeroNetworkPolicy,
        now: int,
    ) -> None:
        self._transport = transport
        self._network = network
        self._policy = policy
        self._now = now

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
            raise AgentZeroError(
                AgentZeroErrorCode.NETWORK_DENIED, f"network denied: {decision.code or host}"
            )
        try:
            response = self._transport.send(HttpRequest(method, url, headers or {}, body))
        except TransportTimeout as exc:
            raise AgentZeroError(AgentZeroErrorCode.TIMED_OUT, str(exc)) from exc
        except TransportFailure as exc:
            raise AgentZeroError(AgentZeroErrorCode.UNAVAILABLE, str(exc)) from exc
        final = response.final_url or url
        if _host(final) != host:
            redirect = self._network.evaluate_redirect(policy.approval, _host(final), self._now)
            if not redirect.allowed:
                raise AgentZeroError(
                    AgentZeroErrorCode.NETWORK_DENIED, f"redirect denied to {_host(final)}"
                )
        charge = self._network.charge(policy.approval, len(response.body))
        if not charge.allowed:
            raise AgentZeroError(
                AgentZeroErrorCode.NETWORK_DENIED, f"transfer denied: {charge.code}"
            )
        return response


def enforce_sandbox_boundary(spec: SandboxSpec) -> None:
    """Raise a typed ``AgentZeroError`` for any sandbox policy violation (never a weaker check).

    Delegates to :func:`factory.sandbox.policy.evaluate_spec` — the single source of truth for the
    prohibited-privilege surface — and additionally maps a host Docker/container-runtime socket
    request to the Agent-Zero-specific ``DOCKER_SOCKET_DENIED`` code.
    """
    violations = evaluate_spec(spec)
    if not violations:
        return
    docker = next((v for v in violations if v.code == "HOST_SOCKET_DENIED"), None)
    if docker is not None:
        raise AgentZeroError(AgentZeroErrorCode.DOCKER_SOCKET_DENIED, docker.detail)
    first = violations[0]
    raise AgentZeroError(AgentZeroErrorCode.CAPABILITY_UNAVAILABLE, f"{first.code}: {first.detail}")


def deny_direct_main_access(
    branch_ref: str, *, protected: frozenset[str] = _PROTECTED_BRANCHES
) -> None:
    """Raise ``DIRECT_MAIN_DENIED`` if ``branch_ref`` targets a protected branch."""
    if branch_ref.strip().lower() in protected:
        raise AgentZeroError(
            AgentZeroErrorCode.DIRECT_MAIN_DENIED,
            f"work order may not target the protected branch {branch_ref!r}",
        )


def deny_hidden_scheduling(work_order: WorkOrder) -> None:
    """Raise ``HIDDEN_SCHEDULING_DENIED`` if the work order carries any scheduling hint.

    ``WorkOrder`` structurally has no schedule field; this guard defends against a future field
    addition or a caller smuggling a scheduling hint through ``instructions``/free text being
    mistaken for a grant. It is defense in depth, not the primary control.
    """
    lowered = work_order.instructions.lower()
    hit = next((key for key in _SCHEDULING_KEYS if key in lowered), None)
    if hit is not None:
        raise AgentZeroError(
            AgentZeroErrorCode.HIDDEN_SCHEDULING_DENIED,
            f"work order instructions reference a scheduling hint ({hit!r}); "
            "Agent Zero may not self-schedule background work",
        )


def _claims_truthy(report: object, keys: frozenset[str]) -> str | None:
    if not isinstance(report, dict):
        return None
    for key in keys:
        value = report.get(key)
        if isinstance(value, str) and value.strip().lower() in _TRUTHY:
            return key
    return None


def assert_no_self_certification(result: AgentZeroResult) -> None:
    """Raise ``SELF_CERTIFICATION_DENIED`` if the worker's self-report claims to be verified.

    Called wherever a caller might be tempted to read ``worker_self_report`` as authoritative —
    this guard makes such a claim loud and rejected rather than silently ignored.
    """
    hit = _claims_truthy(result.worker_self_report, _SELF_CERTIFICATION_KEYS)
    if hit is not None:
        raise AgentZeroError(
            AgentZeroErrorCode.SELF_CERTIFICATION_DENIED,
            f"worker self-report claims {hit!r}=true; a worker's own claim is never Builder "
            "verification and must not be treated as one",
        )


def assert_no_self_promotion(result: AgentZeroResult) -> None:
    """Raise ``PROMOTION_AUTHORITY_DENIED`` if the worker's self-report claims to be promoted."""
    hit = _claims_truthy(result.worker_self_report, _SELF_PROMOTION_KEYS)
    if hit is not None:
        raise AgentZeroError(
            AgentZeroErrorCode.PROMOTION_AUTHORITY_DENIED,
            f"worker self-report claims {hit!r}=true; Agent Zero holds no promotion authority",
        )


def evaluate_output_path(
    authority: PathAuthority, candidate: str, *, allowed: tuple[str, ...]
) -> PathAuthorityResult:
    """Evaluate a proposed patch/artifact path through :class:`PathAuthority`.

    Never a bespoke traversal/symlink/UNC check — this is a thin, faithful call-through so every
    escape vector PathAuthority already defends against (traversal, symlink/junction, Windows
    drive/UNC, reserved device names, NTFS ADS, TOCTOU) is defended here too, with no weaker path.
    """
    result = authority.evaluate(
        candidate,
        operation="write",
        allowed=allowed,
        forbidden=(),
        read_only=(),
        active_exclusive_paths=(),
    )
    if not result.allowed:
        raise AgentZeroError(AgentZeroErrorCode.PATH_DENIED, result.reason)
    return result
