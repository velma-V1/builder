"""WorldMonitor contracts (value types).

A normalized summary is **not** a verified fact; a raw source reference is always preserved; stale
data is visibly marked; confidence is never invented (``None`` unless the source supplied it); and
every :class:`IntelligenceRecord` carries an immutable provenance chain. WorldMonitor data is an
*external claim*, attributed to its source — never asserted as Builder truth.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import StrEnum


class WorldMonitorMode(StrEnum):
    LOCAL_MANAGED_UI = "LOCAL_MANAGED_UI"
    LOCAL_REST = "LOCAL_REST"
    HOSTED_REST = "HOSTED_REST"
    HOSTED_MCP = "HOSTED_MCP"


class Freshness(StrEnum):
    FRESH = "FRESH"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


class HealthState(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


class Category(StrEnum):
    WORLD_BRIEF = "world_brief"
    COUNTRY_RISK = "country_risk"
    CONFLICT_EVENTS = "conflict_events"
    MILITARY_ACTIVITY = "military_activity"
    CYBER_THREATS = "cyber_threats"
    DISASTERS = "disasters"
    CLIMATE = "climate"
    MARITIME = "maritime"
    AVIATION = "aviation"
    MARKETS = "markets"
    ECONOMIC_INDICATORS = "economic_indicators"
    INFRASTRUCTURE = "infrastructure"
    NEWS_RESEARCH = "news_research"


@dataclass(frozen=True, slots=True)
class WorldMonitorCapability:
    category: Category
    mode: WorldMonitorMode
    read_only: bool = True


@dataclass(frozen=True, slots=True)
class WorldMonitorHealth:
    state: HealthState
    detail: str = ""
    checked_at: int = 0


@dataclass(frozen=True, slots=True)
class WorldMonitorSourceRef:
    """A preserved reference to the upstream source (an external claim, never Builder truth)."""

    source_name: str
    source_url: str
    upstream_record_id: str = ""


@dataclass(frozen=True, slots=True)
class WorldMonitorFreshness:
    freshness: Freshness
    observed_at: int = 0
    fetched_at: int = 0
    ttl_s: int = 0


@dataclass(frozen=True, slots=True)
class WorldMonitorQuery:
    category: Category
    geography: str = ""
    since: int = 0
    limit: int = 50


@dataclass(frozen=True, slots=True)
class ProvenanceStep:
    stage: str
    detail: str


@dataclass(frozen=True, slots=True)
class IntelligenceRecord:
    """A normalized, provenance-preserving record. The summary is a claim, not a verified fact."""

    record_id: str
    category: Category
    source: WorldMonitorSourceRef
    geography: str
    freshness: WorldMonitorFreshness
    normalized_summary: str
    content_digest: str
    raw_reference: str
    provider_route: str = ""
    model_fingerprint: str = ""
    #: Only present when the source *supplied* it. Never invented.
    confidence: float | None = None
    provenance_chain: tuple[ProvenanceStep, ...] = ()

    @property
    def is_stale(self) -> bool:
        return self.freshness.freshness is Freshness.STALE


@dataclass(frozen=True, slots=True)
class WorldMonitorResult:
    query: WorldMonitorQuery
    records: tuple[IntelligenceRecord, ...] = ()
    error_code: str | None = None
    reason: str = ""

    @property
    def ok(self) -> bool:
        return self.error_code is None


@dataclass(frozen=True, slots=True)
class WorldMonitorEvent:
    event_id: str
    category: Category
    summary: str
    geography: str
    source: WorldMonitorSourceRef


class ViewCommandType(StrEnum):
    FOCUS_REGION = "focus_region"
    OPEN_COUNTRY = "open_country"
    ENABLE_LAYER = "enable_layer"
    DISABLE_LAYER = "disable_layer"
    OPEN_PANEL = "open_panel"
    SHOW_EVENT = "show_event"
    RESET_VIEW = "reset_view"


@dataclass(frozen=True, slots=True)
class WorldMonitorViewCommand:
    command: ViewCommandType
    argument: str = ""
    schema_version: int = 1


@dataclass(frozen=True, slots=True)
class WorldMonitorWorkspaceState:
    mode: WorldMonitorMode
    health: HealthState
    version: str
    origin: str
    controls_enabled: bool = False  # start/stop controls prepared but disabled
    offline: bool = True


def content_digest(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


def dedup_key(source: WorldMonitorSourceRef, digest: str) -> str:
    """Stable dedup key from source identity + content digest."""
    return f"{source.source_name}|{source.upstream_record_id or source.source_url}|{digest}"
