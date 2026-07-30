"""Model-neutral records and value objects for PH-4 routing (Section 4).

These types encode the governing invariants of ``01J`` and ``03`` so later components (router,
scheduler, quota ledger, adapters) share one authoritative vocabulary:

* **Complete model fingerprint** (``01J §3.1``) — a display name or mutable tag is never sufficient
  identity; :class:`ModelFingerprint` carries the full material configuration and a deterministic
  :meth:`ModelFingerprint.digest`.
* **Append-only execution provenance** (``01J §3.2``, CTR-MODEL-EXEC-RECORD) —
  :class:`ExecutionRecord` is immutable; a fallback never mutates a prior record, it starts a new
  one that *supersedes* it.
* **Model-neutral state** (``01J §2.7``) — authoritative fields live here, not in a model's
  conversation history.

Time is expressed as a monotonic integer tick from a :class:`Clock` so every record is deterministic
and reproducible under test; no wall-clock is embedded in identity.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol

_SEP = "\x1f"


class Clock(Protocol):
    """Monotonic logical clock. ``now`` never decreases across calls."""

    def now(self) -> int: ...


class Provider(StrEnum):
    """Approved runtimes/providers. GLM providers are intentionally absent (``03 §6``)."""

    OLLAMA = "OLLAMA"
    AIDER = "AIDER"
    GROQ = "GROQ"
    CEREBRAS = "CEREBRAS"
    NVIDIA = "NVIDIA"


class ModelRole(StrEnum):
    DISPATCHER = "DISPATCHER"
    SUPERVISOR = "SUPERVISOR"
    CODING_WORKER = "CODING_WORKER"
    HOSTED_WORKER = "HOSTED_WORKER"
    HOSTED_REVIEWER = "HOSTED_REVIEWER"


class ResourceClass(StrEnum):
    """Coarsest scheduling unit. At most one ``GPU_HEAVY`` model may be active (``01J §3.3``)."""

    GPU_HEAVY = "GPU_HEAVY"
    GPU_LIGHT = "GPU_LIGHT"
    CPU_ONLY = "CPU_ONLY"


class TaskType(StrEnum):
    """Declared task class that drives deterministic selection (``01J §2.1``, ``03 §7``)."""

    DISPATCH = "DISPATCH"
    CLASSIFICATION = "CLASSIFICATION"
    SUMMARY = "SUMMARY"
    ROUTINE_CODING = "ROUTINE_CODING"
    HARD_CODING = "HARD_CODING"
    PLANNING = "PLANNING"
    ARCHITECTURE_REVIEW = "ARCHITECTURE_REVIEW"
    ESCALATION_REVIEW = "ESCALATION_REVIEW"
    REPAIR = "REPAIR"
    RECOVERY = "RECOVERY"
    CHAT = "CHAT"
    NAVIGATION = "NAVIGATION"


# Task classes that are consequential enough to force a fresh health check (``01J §3.4``) and to
# never be treated as verified evidence on their own (``01J §5.16``).
CONSEQUENTIAL_TASK_TYPES = frozenset(
    {
        TaskType.HARD_CODING,
        TaskType.ARCHITECTURE_REVIEW,
        TaskType.ESCALATION_REVIEW,
        TaskType.REPAIR,
        TaskType.RECOVERY,
    }
)


class Privacy(StrEnum):
    """Task privacy posture. Hosted use requires an explicit task-scoped grant (``03 §9``)."""

    LOCAL_ONLY = "LOCAL_ONLY"
    CLOUD_ALLOWED = "CLOUD_ALLOWED"


class RuntimeStatus(StrEnum):
    """Explicit runtime availability. ``UNAVAILABLE`` is a *result*, never a silent fallback."""

    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    DEGRADED = "DEGRADED"


class ExecutionStatus(StrEnum):
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"
    RUNTIME_UNAVAILABLE = "RUNTIME_UNAVAILABLE"
    SUPERSEDED = "SUPERSEDED"


TERMINAL_STATUSES = frozenset(
    {
        ExecutionStatus.SUCCEEDED,
        ExecutionStatus.FAILED,
        ExecutionStatus.CANCELLED,
        ExecutionStatus.TIMED_OUT,
        ExecutionStatus.RUNTIME_UNAVAILABLE,
        ExecutionStatus.SUPERSEDED,
    }
)


class HealthState(StrEnum):
    HEALTHY = "HEALTHY"
    UNHEALTHY = "UNHEALTHY"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class ModelDescriptor:
    """One approved roster entry (an abstract route target), keyed by provider + exact id."""

    provider: Provider
    model_id: str
    role: ModelRole
    resource_class: ResourceClass
    is_local: bool

    @property
    def route_key(self) -> str:
        return f"{self.provider.value}:{self.model_id}"


@dataclass(frozen=True, slots=True)
class ModelFingerprint:
    """Complete deterministic model fingerprint (``01J §3.1``).

    A mutable tag alone is insufficient identity, so :meth:`digest` folds in every material field.
    ``sampling`` is a sorted tuple of ``(key, value)`` pairs to stay hashable and order-independent.
    """

    family: str
    declared_name: str
    artifact_digest: str
    quantization: str
    fmt: str
    ollama_version: str
    runtime_version: str
    context_window: int
    context_allocation: int
    sampling: tuple[tuple[str, str], ...]
    system_prompt_version: str
    tool_schema_version: str
    adapter_version: str
    routing_policy_version: str
    gpu_config: str

    def digest(self) -> str:
        parts = [
            self.family,
            self.declared_name,
            self.artifact_digest,
            self.quantization,
            self.fmt,
            self.ollama_version,
            self.runtime_version,
            str(self.context_window),
            str(self.context_allocation),
            _SEP.join(f"{k}={v}" for k, v in sorted(self.sampling)),
            self.system_prompt_version,
            self.tool_schema_version,
            self.adapter_version,
            self.routing_policy_version,
            self.gpu_config,
        ]
        return hashlib.sha256(_SEP.join(parts).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ResourceProfile:
    """A model's declared resource footprint for a task class (executable, not informal)."""

    resource_class: ResourceClass
    vram_mb: int
    ram_mb: int
    cpu_units: int
    storage_mb: int


@dataclass(frozen=True, slots=True)
class Reservation:
    reservation_id: str
    task_id: str
    route_key: str
    profile: ResourceProfile
    acquired_at: int


@dataclass(frozen=True, slots=True)
class RouteDecision:
    """A deterministic, operator-visible routing decision (``01J §2.2``)."""

    task_id: str
    task_type: TaskType
    selected: ModelDescriptor
    reason: str
    privacy: Privacy
    operator_override: bool
    candidates: tuple[str, ...]
    health_check_required: bool


@dataclass(frozen=True, slots=True)
class ExecutionRecord:
    """Append-only model-execution provenance (CTR-MODEL-EXEC-RECORD, ``01J §3.1/§3.2``).

    Immutable. A fallback or retry produces a *new* record whose ``supersedes`` points at the prior
    record id; the ledger never rewrites history in place.
    """

    record_id: str
    task_id: str
    stage_id: str
    attempt: int
    route_key: str
    fingerprint_digest: str
    status: ExecutionStatus
    started_at: int
    reason: str
    supersedes: str | None = None
    reverification_required: bool = False
    error_code: str | None = None


@dataclass(frozen=True, slots=True)
class FallbackRecord:
    """Disclosed, recorded substitution (``01J §3.2``, ``01J §2.14/§2.15``)."""

    from_record_id: str
    to_record_id: str
    reason: str
    failed_fingerprint_digest: str
    substitute_fingerprint_digest: str
    reverification_gates: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class HealthRecord:
    route_key: str
    state: HealthState
    checked_at: int
    expires_at: int
    reason: str

    def is_valid_at(self, now: int) -> bool:
        return self.state is HealthState.HEALTHY and now < self.expires_at


@dataclass(frozen=True, slots=True)
class QuotaLimits:
    max_requests: int
    max_tokens: int
    max_wall_time: int


@dataclass(frozen=True, slots=True)
class UsageCounters:
    requests: int = 0
    tokens: int = 0
    wall_time: int = 0

    def plus(self, *, requests: int, tokens: int, wall_time: int) -> UsageCounters:
        return UsageCounters(
            requests=self.requests + requests,
            tokens=self.tokens + tokens,
            wall_time=self.wall_time + wall_time,
        )


@dataclass(frozen=True, slots=True)
class CapabilityReport:
    """Result of an adapter capability/availability probe (``03 §8``)."""

    provider: Provider
    status: RuntimeStatus
    exact_models: tuple[str, ...]
    runtime_version: str
    reason: str
    reduced_monitoring: bool = False


@dataclass(frozen=True, slots=True)
class SchedulerLimits:
    """Versioned executable scheduler policy (``01J §3.3``). Defaults model a 12 GB GPU host."""

    version: str = "v1"
    max_vram_mb: int = 12000
    max_ram_mb: int = 32000
    min_free_ram_mb: int = 2000
    cpu_concurrency: int = 2
    max_storage_mb: int = 200000
    min_free_storage_mb: int = 5000
    emergency_reserve_mb: int = 1000
    max_gpu_heavy: int = 1
    unload_timeout: int = 30
    health_timeout: int = 10
    cooldown_ticks: int = 5
    min_residency_ticks: int = 3


class MonitoringMode(StrEnum):
    FULL = "FULL"
    REDUCED_MONITORING = "REDUCED_MONITORING"


@dataclass(frozen=True, slots=True)
class SensorReading:
    """Observed host resource state. Any ``None`` sensor triggers REDUCED_MONITORING (``4.4``)."""

    free_vram_mb: int | None = None
    free_ram_mb: int | None = None
    free_storage_mb: int | None = None
    thermal_ok: bool | None = None


@dataclass(frozen=True, slots=True)
class RoutingSnapshot:
    """Serializable state for restart reconciliation (``01J §2.7``, ``4.4`` resource recovery)."""

    reservations: tuple[Reservation, ...] = field(default_factory=tuple)
    records: tuple[ExecutionRecord, ...] = field(default_factory=tuple)
    usage: tuple[tuple[str, UsageCounters], ...] = field(default_factory=tuple)
