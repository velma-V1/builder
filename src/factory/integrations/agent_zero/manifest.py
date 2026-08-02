"""Agent Zero upstream manifest — external pinned dependency (NOT vendored).

Agent Zero is an **external, independently-licensed** managed worker. Its source is **not** copied,
forked, or rebranded into Builder; this manifest only *pins and describes* the upstream so the
integration targets an exact, reviewable revision once one is designated. Every upstream fact here
is **UNVERIFIED from this environment** (no network egress, nothing installed) and MUST be confirmed
by the operator before any live use. Commercial-use licensing is **unresolved**.
"""

from __future__ import annotations

from dataclasses import dataclass

from factory.integrations.agent_zero.models import AgentZeroIntegrationMode

UNVERIFIED = "UNVERIFIED_PENDING_OPERATOR_CONFIRMATION"


@dataclass(frozen=True, slots=True)
class AgentZeroManifest:
    upstream_repo: str
    pinned_release: str
    pinned_commit: str
    image_digest_placeholder: str
    license: str
    attribution: str
    commercial_use_status: str
    supported_integration_modes: tuple[AgentZeroIntegrationMode, ...]
    required_domains: frozenset[str]
    required_ports: tuple[int, ...]
    compatibility_version: str
    license_verified: bool = False
    revision_verified: bool = False


#: The shipped manifest. Every upstream-fact field is UNVERIFIED until the operator confirms it.
AGENT_ZERO_MANIFEST = AgentZeroManifest(
    upstream_repo=f"{UNVERIFIED} (Agent Zero upstream not yet designated)",
    pinned_release=UNVERIFIED,
    pinned_commit=UNVERIFIED,
    image_digest_placeholder="__PINNED_DIGEST__",
    license=f"{UNVERIFIED} (confirm from upstream LICENSE before any live use)",
    attribution="Agent Zero © its authors; used as an external managed-worker dependency",
    commercial_use_status="UNRESOLVED — no commercial-use right claimed; requires legal review",
    supported_integration_modes=(AgentZeroIntegrationMode.MANAGED_WORKER,),
    required_domains=frozenset(),  # populated per approved deployment; empty = none approved yet
    required_ports=(),
    compatibility_version="0.1-integration",
)


MANAGED_WORKER_OBLIGATIONS = (
    "Agent Zero is integrated strictly as a managed external worker: (1) it executes only an "
    "assigned WorkOrder and uses only explicitly granted tools; (2) it never receives a provider "
    "API key, a Docker socket, unrestricted host filesystem access, or direct access to the main "
    "branch; (3) it never holds merge, approval, promotion, or self-update authority; (4) it never "
    "self-schedules background work; (5) its own claim of success is never treated as Builder's "
    "verification verdict. Upstream license/commercial-use terms remain UNRESOLVED and must be "
    "confirmed by the operator before any live installation."
)
