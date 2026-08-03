"""Agent Zero upstream manifest — external pinned dependency (NOT vendored).

Agent Zero is an **external, independently-licensed** managed worker. Its source is **not** copied,
forked, or rebranded into Builder; this manifest only *pins and describes* the upstream so the
integration targets the exact official v2.7 revision verified on 2026-08-02. Live image digest and
container behavior remain installation-time checks.
"""

from __future__ import annotations

from dataclasses import dataclass

from factory.integrations.agent_zero.models import AgentZeroIntegrationMode


@dataclass(frozen=True, slots=True)
class AgentZeroManifest:
    upstream_repo: str
    pinned_release: str
    pinned_commit: str
    immutable_image_reference: str
    license: str
    attribution: str
    commercial_use_status: str
    supported_integration_modes: tuple[AgentZeroIntegrationMode, ...]
    required_domains: frozenset[str]
    required_ports: tuple[int, ...]
    compatibility_version: str
    license_verified: bool = False
    revision_verified: bool = False


#: Pinned official upstream release verified against the repository tag and license on 2026-08-02.
AGENT_ZERO_MANIFEST = AgentZeroManifest(
    upstream_repo="github.com/agent0ai/agent-zero",
    pinned_release="v2.7",
    pinned_commit="87e1e591e1ba2e8b1a19d34e134fcae490c8dded",
    immutable_image_reference="builder/agent-zero:v2.7-87e1e591@87e1e591e1ba2e8b1a19d34e134fcae490c8dded",
    license="MIT",
    attribution="Agent Zero © 2025 Agent Zero, s.r.o.; MIT licensed external dependency",
    commercial_use_status="MIT permits local and commercial use subject to notice preservation",
    supported_integration_modes=(AgentZeroIntegrationMode.MANAGED_WORKER,),
    required_domains=frozenset(),  # populated per approved deployment; empty = none approved yet
    required_ports=(80,),
    compatibility_version="2.7",
    license_verified=True,
    revision_verified=True,
)


MANAGED_WORKER_OBLIGATIONS = (
    "Agent Zero is integrated strictly as a managed external worker: (1) it executes only an "
    "assigned WorkOrder and uses only explicitly granted tools; (2) it never receives a provider "
    "API key, a Docker socket, unrestricted host filesystem access, or direct access to the main "
    "branch; (3) it never holds merge, approval, promotion, or self-update authority; (4) it never "
    "self-schedules background work; (5) its own claim of success is never treated as Builder's "
    "verification verdict. The upstream MIT notice must be preserved with the installed external "
    "dependency."
)
