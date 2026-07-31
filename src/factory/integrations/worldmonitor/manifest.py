"""WorldMonitor upstream manifest — external pinned dependency (NOT vendored).

WorldMonitor is an **external, independently-licensed** project. Its source is **not** copied,
forked, or rebranded into Builder; this manifest only *pins and describes* the upstream so the
integration targets an exact, reviewable revision. The pinned revision, image digest, and license
facts here are **UNVERIFIED from this environment** (no network egress to the upstream) and MUST be
confirmed by the operator before any live use. Commercial-use licensing is **unresolved** — no
commercial-use right is claimed.
"""

from __future__ import annotations

from dataclasses import dataclass

from factory.integrations.worldmonitor.models import WorldMonitorMode

UNVERIFIED = "UNVERIFIED_PENDING_OPERATOR_CONFIRMATION"


@dataclass(frozen=True, slots=True)
class WorldMonitorManifest:
    upstream_repo: str
    pinned_release: str
    pinned_commit: str
    image_digest_placeholder: str
    license: str
    attribution: str
    commercial_use_status: str
    supported_integration_modes: tuple[WorldMonitorMode, ...]
    required_domains: frozenset[str]
    required_ports: tuple[int, ...]
    compatibility_version: str
    license_verified: bool = False
    revision_verified: bool = False


#: The shipped manifest. Every upstream-fact field is UNVERIFIED until the operator confirms it.
WORLDMONITOR_MANIFEST = WorldMonitorManifest(
    upstream_repo="github.com/koala73/worldmonitor",
    pinned_release=UNVERIFIED,
    pinned_commit=UNVERIFIED,
    image_digest_placeholder="__PINNED_DIGEST__",
    license=f"{UNVERIFIED} (assumed AGPL-family — confirm from upstream LICENSE)",
    attribution="WorldMonitor © its authors (koala73/worldmonitor); used as an external dependency",
    commercial_use_status="UNRESOLVED — no commercial-use right claimed; requires legal review",
    supported_integration_modes=(
        WorldMonitorMode.LOCAL_MANAGED_UI,
        WorldMonitorMode.LOCAL_REST,
        WorldMonitorMode.HOSTED_REST,
        WorldMonitorMode.HOSTED_MCP,
    ),
    required_domains=frozenset(),   # populated per approved deployment; empty = none approved yet
    required_ports=(),
    compatibility_version="0.1-integration",
)


AGPL_OBLIGATIONS = (
    "If the upstream is AGPL-3.0: (1) preserve copyright + license notices; (2) offer the complete "
    "corresponding source of the running WorldMonitor to its network users; (3) keep Builder's own "
    "source boundary independent (no source merge); (4) do not relicense upstream code. Commercial "
    "or SaaS use may impose additional obligations — resolve before any hosted/commercial use."
)
