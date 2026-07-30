"""PH-4 (Section 4) — Model & Coding-Tool Routing & Quotas — preinstallation core.

Deterministic, offline, local-first routing built from the governing contracts (``01J``, ``03``,
CTR-ROUTE-REGISTRY / CTR-MODEL-FINGERPRINT / CTR-MODEL-EXEC-RECORD). This package delivers the
routing *core* against deterministic fake provider adapters; wiring the live Ollama runtime adapter
(``src/factory/models/ollama_adapter``) and live Aider worker adapter
(``src/factory/workers/aider_adapter``) to real daemons is LIVE_RUNTIME_PENDING and gated behind
installation.

Guarantees realized here: visible deterministic routing, operator override within limits, privacy
before hosted use, no silent substitution, complete model fingerprints, append-only execution
records, quota/usage accounting, executable resource reservations with a single-active GPU-heavy
policy and anti-thrash cooldown, explicit runtime-unavailable results, health-check triggers,
disclosed + reverified fallback provenance, and restart reconciliation.
"""

from __future__ import annotations

from factory.routing.errors import RoutingError
from factory.routing.fingerprint import require_full_fingerprint
from factory.routing.health import HealthContext, HealthLedger, health_check_required
from factory.routing.models import (
    CapabilityReport,
    ExecutionRecord,
    ExecutionStatus,
    FallbackRecord,
    HealthRecord,
    HealthState,
    ModelDescriptor,
    ModelFingerprint,
    ModelRole,
    MonitoringMode,
    Privacy,
    Provider,
    QuotaLimits,
    Reservation,
    ResourceClass,
    ResourceProfile,
    RouteDecision,
    RoutingSnapshot,
    RuntimeStatus,
    SchedulerLimits,
    SensorReading,
    TaskType,
    UsageCounters,
)
from factory.routing.records import ExecutionLedger, InMemoryRecordStore
from factory.routing.roster import ApprovedRoster
from factory.routing.router import (
    ExecutionOutcome,
    ManualClock,
    ModelRouter,
    RouteRequest,
)

__all__ = [
    "ApprovedRoster",
    "CapabilityReport",
    "ExecutionLedger",
    "ExecutionOutcome",
    "ExecutionRecord",
    "ExecutionStatus",
    "FallbackRecord",
    "HealthContext",
    "HealthLedger",
    "HealthRecord",
    "HealthState",
    "InMemoryRecordStore",
    "ManualClock",
    "ModelDescriptor",
    "ModelFingerprint",
    "ModelRole",
    "ModelRouter",
    "MonitoringMode",
    "Privacy",
    "Provider",
    "QuotaLimits",
    "Reservation",
    "ResourceClass",
    "ResourceProfile",
    "RouteDecision",
    "RouteRequest",
    "RoutingError",
    "RoutingSnapshot",
    "RuntimeStatus",
    "SchedulerLimits",
    "SensorReading",
    "TaskType",
    "UsageCounters",
    "health_check_required",
    "require_full_fingerprint",
]
