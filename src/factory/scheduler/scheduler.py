"""Resource Scheduler + reservation lifecycle (Task 4.4, ``01J §3.3``).

Executable, versioned admission control rather than informal judgement. A reservation is acquired
*before* a model would load and released/reconciled after termination, so a model cannot start
merely because instantaneous usage is low. Enforced invariants:

* **≤ 1 GPU-heavy active** (``01J §3.3``, ``max_gpu_heavy``);
* **ceilings** on VRAM / RAM / CPU concurrency / storage, honoring the emergency storage reserve and
  minimum-free-RAM floor;
* **anti-thrash** — a route re-admitted within ``cooldown_ticks`` of its own release is refused
  (minimum residency / cooldown, ``01J §3.3``);
* **REDUCED_MONITORING** — a missing sensor never fails open; admission continues under conservative
  full-reservation accounting with the mode flagged (Task 4.4).

All decisions are deterministic and pure; no wall-clock, no host calls.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from factory.routing.models import (
    MonitoringMode,
    Reservation,
    ResourceClass,
    ResourceProfile,
    SchedulerLimits,
    SensorReading,
)


class AdmissionOutcome(StrEnum):
    ADMITTED = "ADMITTED"
    DENIED_OVERCOMMIT = "DENIED_OVERCOMMIT"
    DENIED_GPU_HEAVY_BUSY = "DENIED_GPU_HEAVY_BUSY"
    DENIED_COOLDOWN = "DENIED_COOLDOWN"


@dataclass(frozen=True, slots=True)
class AdmissionResult:
    outcome: AdmissionOutcome
    reason: str
    monitoring: MonitoringMode
    reservation: Reservation | None = None

    @property
    def admitted(self) -> bool:
        return self.outcome is AdmissionOutcome.ADMITTED


class ResourceScheduler:
    """Deterministic reservation authority for model loading."""

    __slots__ = ("_active", "_last_release", "_limits", "_seq")

    def __init__(self, limits: SchedulerLimits | None = None) -> None:
        self._limits = limits if limits is not None else SchedulerLimits()
        self._active: dict[str, Reservation] = {}
        self._last_release: dict[str, int] = {}
        self._seq = 0

    # -- introspection -----------------------------------------------------------------------
    def active(self) -> tuple[Reservation, ...]:
        return tuple(self._active.values())

    def _reserved_vram(self) -> int:
        return sum(r.profile.vram_mb for r in self._active.values())

    def _reserved_ram(self) -> int:
        return sum(r.profile.ram_mb for r in self._active.values())

    def _reserved_cpu(self) -> int:
        return sum(
            1 for r in self._active.values() if r.profile.resource_class is ResourceClass.CPU_ONLY
        )

    def _gpu_heavy_count(self) -> int:
        return sum(
            1 for r in self._active.values() if r.profile.resource_class is ResourceClass.GPU_HEAVY
        )

    # -- admission ---------------------------------------------------------------------------
    def admit(
        self,
        task_id: str,
        route_key: str,
        profile: ResourceProfile,
        now: int,
        sensors: SensorReading | None = None,
    ) -> AdmissionResult:
        reading = sensors if sensors is not None else SensorReading()
        reduced = (
            reading.free_vram_mb is None
            or reading.free_ram_mb is None
            or reading.free_storage_mb is None
            or reading.thermal_ok is None
        )
        mode = MonitoringMode.REDUCED_MONITORING if reduced else MonitoringMode.FULL

        released_at = self._last_release.get(route_key)
        if released_at is not None and now - released_at < self._limits.cooldown_ticks:
            return AdmissionResult(
                AdmissionOutcome.DENIED_COOLDOWN,
                f"route {route_key} in cooldown until {released_at + self._limits.cooldown_ticks}",
                mode,
            )

        if (
            profile.resource_class is ResourceClass.GPU_HEAVY
            and self._gpu_heavy_count() >= self._limits.max_gpu_heavy
        ):
            return AdmissionResult(
                AdmissionOutcome.DENIED_GPU_HEAVY_BUSY,
                "a GPU-heavy model is already active (single-active policy)",
                mode,
            )

        if self._reserved_vram() + profile.vram_mb > self._limits.max_vram_mb:
            return AdmissionResult(
                AdmissionOutcome.DENIED_OVERCOMMIT, "VRAM reservation ceiling exceeded", mode
            )
        if self._reserved_ram() + profile.ram_mb > self._limits.max_ram_mb:
            return AdmissionResult(
                AdmissionOutcome.DENIED_OVERCOMMIT, "RAM reservation ceiling exceeded", mode
            )
        if (
            reading.free_ram_mb is not None
            and reading.free_ram_mb - profile.ram_mb < self._limits.min_free_ram_mb
        ):
            return AdmissionResult(
                AdmissionOutcome.DENIED_OVERCOMMIT, "minimum free RAM floor would be breached", mode
            )
        if (
            profile.resource_class is ResourceClass.CPU_ONLY
            and self._reserved_cpu() + 1 > self._limits.cpu_concurrency
        ):
            return AdmissionResult(
                AdmissionOutcome.DENIED_OVERCOMMIT, "CPU concurrency ceiling exceeded", mode
            )
        if (
            reading.free_storage_mb is not None
            and reading.free_storage_mb - profile.storage_mb
            < self._limits.min_free_storage_mb + self._limits.emergency_reserve_mb
        ):
            return AdmissionResult(
                AdmissionOutcome.DENIED_OVERCOMMIT, "storage reserve would be breached", mode
            )

        self._seq += 1
        reservation = Reservation(
            reservation_id=f"resv-{self._seq}",
            task_id=task_id,
            route_key=route_key,
            profile=profile,
            acquired_at=now,
        )
        self._active[reservation.reservation_id] = reservation
        return AdmissionResult(AdmissionOutcome.ADMITTED, "reserved", mode, reservation)

    def release(self, reservation_id: str, now: int) -> bool:
        """Release a reservation and start its cooldown. Idempotent (False if already gone)."""
        reservation = self._active.pop(reservation_id, None)
        if reservation is None:
            return False
        self._last_release[reservation.route_key] = now
        return True

    def pressure_order(self) -> tuple[Reservation, ...]:
        """Deterministic pause/cancel order under resource pressure: GPU-heavy first, then most
        recently acquired, then reservation id (``01J §3.3`` deterministic pressure order)."""
        rank = {ResourceClass.GPU_HEAVY: 0, ResourceClass.GPU_LIGHT: 1, ResourceClass.CPU_ONLY: 2}
        return tuple(
            sorted(
                self._active.values(),
                key=lambda r: (rank[r.profile.resource_class], -r.acquired_at, r.reservation_id),
            )
        )

    def reconcile(self, live_reservations: tuple[Reservation, ...], now: int) -> tuple[str, ...]:
        """Restart reconciliation: adopt the durable reservation set and drop any orphan not in it.
        Returns the ids of released orphans (``4.4`` resource recovery)."""
        live_ids = {r.reservation_id for r in live_reservations}
        orphans = tuple(rid for rid in self._active if rid not in live_ids)
        for rid in orphans:
            self.release(rid, now)
        for reservation in live_reservations:
            self._active.setdefault(reservation.reservation_id, reservation)
        return orphans
