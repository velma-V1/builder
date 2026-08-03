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

import threading
from dataclasses import dataclass, replace
from enum import StrEnum

from factory.routing.models import (
    MonitoringMode,
    Reservation,
    ResourceClass,
    ResourceProfile,
    SchedulerLimits,
    SensorReading,
)


def _seq_of(reservation_id: str) -> int:
    """Parse the numeric suffix of a ``resv-N`` id (0 if it does not match)."""
    prefix, _, tail = reservation_id.rpartition("-")
    return int(tail) if prefix == "resv" and tail.isdigit() else 0


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
    """Deterministic, thread-safe reservation authority for model loading."""

    __slots__ = ("_active", "_epoch", "_last_release", "_limits", "_lock", "_seq")

    def __init__(self, limits: SchedulerLimits | None = None, *, epoch: int = 0) -> None:
        self._limits = limits if limits is not None else SchedulerLimits()
        self._active: dict[str, Reservation] = {}
        self._last_release: dict[str, int] = {}
        self._seq = 0
        self._epoch = epoch
        # A re-entrant lock makes admit/release/reconcile/revalidate atomic across threads and lets
        # reservation-id issuance be collision-free even under concurrency.
        self._lock = threading.RLock()

    @property
    def epoch(self) -> int:
        return self._epoch

    # -- introspection -----------------------------------------------------------------------
    def active(self) -> tuple[Reservation, ...]:
        with self._lock:
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
        with self._lock:
            reading = sensors if sensors is not None else SensorReading()
            reduced = (
                reading.free_vram_mb is None
                or reading.free_ram_mb is None
                or reading.free_storage_mb is None
                or reading.thermal_ok is None
            )
            mode = MonitoringMode.REDUCED_MONITORING if reduced else MonitoringMode.FULL
            denial = self._deny_reason(route_key, profile, reading, now, mode)
            if denial is not None:
                return denial

            self._seq += 1
            reservation = Reservation(
                reservation_id=f"resv-{self._seq}",
                task_id=task_id,
                route_key=route_key,
                profile=profile,
                acquired_at=now,
                process_epoch=self._epoch,
            )
            self._active[reservation.reservation_id] = reservation
            return AdmissionResult(AdmissionOutcome.ADMITTED, "reserved", mode, reservation)

    def _deny_reason(
        self,
        route_key: str,
        profile: ResourceProfile,
        reading: SensorReading,
        now: int,
        mode: MonitoringMode,
    ) -> AdmissionResult | None:
        """Return a denial result if admission is not permitted, else None (caller holds lock)."""
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
        return None

    def release(self, reservation_id: str, now: int) -> bool:
        """Release a reservation and start its cooldown. Idempotent (False if already gone)."""
        with self._lock:
            reservation = self._active.pop(reservation_id, None)
            if reservation is None:
                return False
            self._last_release[reservation.route_key] = now
            return True

    def pressure_order(self) -> tuple[Reservation, ...]:
        """Deterministic pause/cancel order under resource pressure: GPU-heavy first, then most
        recently acquired, then reservation id (``01J §3.3`` deterministic pressure order)."""
        rank = {ResourceClass.GPU_HEAVY: 0, ResourceClass.GPU_LIGHT: 1, ResourceClass.CPU_ONLY: 2}
        with self._lock:
            return tuple(
                sorted(
                    self._active.values(),
                    key=lambda r: (
                        rank[r.profile.resource_class],
                        -r.acquired_at,
                        r.reservation_id,
                    ),
                )
            )

    def reconcile(
        self, live_reservations: tuple[Reservation, ...], now: int, *, new_epoch: int | None = None
    ) -> tuple[str, ...]:
        """Restart reconciliation. Restored reservations are adopted **as STALE** under a fresh
        process epoch and cannot be reactivated until :meth:`revalidate` re-checks them; any active
        reservation absent from the durable set is released as an orphan. The id sequence advances
        past every restored id so a newly admitted reservation cannot collide with a restored one.
        Returns the released orphan ids (``4.4`` resource recovery)."""
        with self._lock:
            self._epoch = new_epoch if new_epoch is not None else self._epoch + 1
            live_ids = {r.reservation_id for r in live_reservations}
            orphans = tuple(rid for rid in self._active if rid not in live_ids)
            for rid in orphans:
                self.release(rid, now)
            for reservation in live_reservations:
                self._seq = max(self._seq, _seq_of(reservation.reservation_id))
                self._active[reservation.reservation_id] = replace(
                    reservation, stale=True, process_epoch=self._epoch
                )
            return orphans

    def revalidate(
        self,
        reservation_id: str,
        now: int,
        *,
        task_ok: bool,
        route_ok: bool,
        resources_ok: bool,
        sensors: SensorReading | None = None,
    ) -> bool:
        """Revalidate a STALE restored reservation before reactivation (``01J §3.2`` provenance).

        Re-checks task validity, route approval, resource availability, and re-runs admission
        against current pressure. On success the reservation is cleared of ``stale`` and remains
        active; on any failure it is released. Returns True iff the reservation is now valid."""
        with self._lock:
            reservation = self._active.get(reservation_id)
            if reservation is None:
                return False
            if not reservation.stale:
                return True  # already validated / never stale
            reading = sensors if sensors is not None else SensorReading()
            mode = MonitoringMode.FULL
            # Temporarily exclude the reservation itself so re-admission does not double-count it.
            self._active.pop(reservation_id)
            denial = self._deny_reason(
                reservation.route_key, reservation.profile, reading, now, mode
            )
            if not (task_ok and route_ok and resources_ok) or denial is not None:
                self._last_release[reservation.route_key] = now
                return False
            self._active[reservation_id] = replace(reservation, stale=False)
            return True
