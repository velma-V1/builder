"""Health checks + trigger conditions (Task 4.5, ``01J §3.4``).

A model health record has a validity window. A fresh check is *required* — a still-valid cached
record may not be reused — when a task is consequential or when the runtime changed since the last
valid check (loaded / restarted / recovered / drifted). Routine low-risk work may reuse a valid
record. The determination is deterministic and testable.
"""

from __future__ import annotations

from dataclasses import dataclass

from factory.routing.models import (
    CONSEQUENTIAL_TASK_TYPES,
    HealthRecord,
    HealthState,
    TaskType,
)


@dataclass(frozen=True, slots=True)
class HealthContext:
    """Signals that bear on whether a fresh health check is required (``01J §3.4``)."""

    writes_protected_state: bool = False
    runtime_changed_since_check: bool = False
    recent_instability: bool = False


def health_check_required(
    task_type: TaskType,
    context: HealthContext,
    cached: HealthRecord | None,
    now: int,
) -> bool:
    """Deterministic ``01J §3.4`` trigger. Any consequential condition forces a fresh check."""
    if task_type in CONSEQUENTIAL_TASK_TYPES:
        return True
    if context.writes_protected_state or context.runtime_changed_since_check:
        return True
    if context.recent_instability:
        return True
    if cached is None:
        return True
    return not cached.is_valid_at(now)


class HealthLedger:
    """Stores the latest health record per route and answers validity queries."""

    __slots__ = ("_records",)

    def __init__(self) -> None:
        self._records: dict[str, HealthRecord] = {}

    def record(self, health: HealthRecord) -> HealthRecord:
        self._records[health.route_key] = health
        return health

    def latest(self, route_key: str) -> HealthRecord | None:
        return self._records.get(route_key)

    def is_valid(self, route_key: str, now: int) -> bool:
        record = self._records.get(route_key)
        return record is not None and record.is_valid_at(now)

    def check(
        self, route_key: str, healthy: bool, now: int, ttl: int, reason: str
    ) -> HealthRecord:
        state = HealthState.HEALTHY if healthy else HealthState.UNHEALTHY
        return self.record(HealthRecord(route_key, state, now, now + ttl, reason))
