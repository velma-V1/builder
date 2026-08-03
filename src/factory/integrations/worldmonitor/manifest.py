"""WorldMonitor upstream manifest — external pinned dependency (NOT vendored).

WorldMonitor is an **external, independently-licensed** project. Its source is **not** copied,
forked, or rebranded into Builder; this manifest only *pins and describes* the upstream so the
integration targets an exact, reviewable revision. The pinned revision, image digest, and license
release and license were verified on 2026-08-02. Builder supports local integration only; hosted or
commercial deployment and relicensing remain explicitly out of scope.
"""

from __future__ import annotations

from dataclasses import dataclass

from factory.integrations.worldmonitor.models import WorldMonitorMode


@dataclass(frozen=True, slots=True)
class WorldMonitorManifest:
    upstream_repo: str
    pinned_release: str
    pinned_commit: str
    immutable_image_reference: str
    license: str
    attribution: str
    commercial_use_status: str
    supported_integration_modes: tuple[WorldMonitorMode, ...]
    required_domains: frozenset[str]
    required_ports: tuple[int, ...]
    compatibility_version: str
    approved_capability_scope: tuple[str, ...]
    implemented_capability_scope: tuple[str, ...]
    section_complete: bool
    license_verified: bool = False
    revision_verified: bool = False


#: Pinned official upstream release verified against the repository tag and license on 2026-08-02.
WORLDMONITOR_MANIFEST = WorldMonitorManifest(
    upstream_repo="github.com/koala73/worldmonitor",
    pinned_release="v2.5.23",
    pinned_commit="e51058e1765ef2f0c83ccb1d08d984bc59d23f10",
    immutable_image_reference="builder/worldmonitor:v2.5.23@e51058e1765ef2f0c83ccb1d08d984bc59d23f10",
    license="AGPL-3.0-or-later",
    attribution="WorldMonitor © its authors (koala73/worldmonitor); used as an external dependency",
    commercial_use_status=(
        "Approved for local integration under AGPL; hosted/commercial deployment is out of scope"
    ),
    supported_integration_modes=(
        WorldMonitorMode.LOCAL_MANAGED_UI,
        WorldMonitorMode.LOCAL_REST,
        WorldMonitorMode.HOSTED_REST,
        WorldMonitorMode.HOSTED_MCP,
    ),
    required_domains=frozenset({"earthquake.usgs.gov"}),
    required_ports=(3000,),
    compatibility_version="2.5.23",
    approved_capability_scope=(
        "world_brief",
        "country_risk",
        "conflict_events",
        "military_activity",
        "cyber_threats",
        "disasters",
        "climate",
        "maritime",
        "aviation",
        "markets",
        "economic_indicators",
        "infrastructure",
        "news_research",
    ),
    implemented_capability_scope=("disasters.earthquakes",),
    section_complete=False,
    license_verified=True,
    revision_verified=True,
)


AGPL_OBLIGATIONS = (
    "If the upstream is AGPL-3.0: (1) preserve copyright + license notices; (2) offer the complete "
    "corresponding source of the running WorldMonitor to its network users; (3) keep Builder's own "
    "source boundary independent (no source merge); (4) do not relicense upstream code. Commercial "
    "or SaaS use may impose additional obligations — resolve before any hosted/commercial use."
)
