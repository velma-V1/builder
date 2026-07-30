"""PH-4 unit — Resource Scheduler (single-active GPU-heavy, ceilings, cooldown, reconcile)."""

from __future__ import annotations

from factory.routing import (
    MonitoringMode,
    Reservation,
    ResourceClass,
    ResourceProfile,
    SchedulerLimits,
    SensorReading,
)
from factory.scheduler import AdmissionOutcome, ResourceScheduler


def _profile(cls: ResourceClass, vram: int = 0, ram: int = 0, storage: int = 0) -> ResourceProfile:
    return ResourceProfile(cls, vram_mb=vram, ram_mb=ram, cpu_units=1, storage_mb=storage)


def test_admit_returns_reservation_and_tracks_active() -> None:
    sched = ResourceScheduler()
    result = sched.admit(
        "t1", "OLLAMA:qwen3:8b", _profile(ResourceClass.GPU_LIGHT, vram=4000), now=0
    )
    assert result.admitted
    assert result.reservation is not None
    assert len(sched.active()) == 1


def test_only_one_gpu_heavy_active() -> None:
    sched = ResourceScheduler()
    a = sched.admit("t1", "AIDER:aider", _profile(ResourceClass.GPU_HEAVY, vram=6000), now=0)
    assert a.admitted
    b = sched.admit("t2", "OLLAMA:qwen3:14b", _profile(ResourceClass.GPU_HEAVY, vram=1000), now=0)
    assert not b.admitted
    assert b.outcome is AdmissionOutcome.DENIED_GPU_HEAVY_BUSY


def test_vram_ceiling_denies_overcommit() -> None:
    sched = ResourceScheduler(SchedulerLimits(max_vram_mb=8000))
    assert sched.admit("t1", "r", _profile(ResourceClass.GPU_LIGHT, vram=5000), now=0).admitted
    denied = sched.admit("t2", "r2", _profile(ResourceClass.GPU_LIGHT, vram=5000), now=0)
    assert denied.outcome is AdmissionOutcome.DENIED_OVERCOMMIT


def test_ram_ceiling_denies_overcommit() -> None:
    sched = ResourceScheduler(SchedulerLimits(max_ram_mb=4000))
    denied = sched.admit("t1", "r", _profile(ResourceClass.CPU_ONLY, ram=5000), now=0)
    assert denied.outcome is AdmissionOutcome.DENIED_OVERCOMMIT


def test_free_ram_floor_is_enforced() -> None:
    sched = ResourceScheduler(SchedulerLimits(min_free_ram_mb=2000))
    sensors = SensorReading(
        free_vram_mb=8000, free_ram_mb=2500, free_storage_mb=100000, thermal_ok=True
    )
    denied = sched.admit(
        "t1", "r", _profile(ResourceClass.CPU_ONLY, ram=1000), now=0, sensors=sensors
    )
    assert denied.outcome is AdmissionOutcome.DENIED_OVERCOMMIT


def test_cpu_concurrency_ceiling() -> None:
    sched = ResourceScheduler(SchedulerLimits(cpu_concurrency=1))
    assert sched.admit("t1", "r", _profile(ResourceClass.CPU_ONLY), now=0).admitted
    denied = sched.admit("t2", "r2", _profile(ResourceClass.CPU_ONLY), now=0)
    assert denied.outcome is AdmissionOutcome.DENIED_OVERCOMMIT


def test_storage_reserve_is_protected() -> None:
    sched = ResourceScheduler(SchedulerLimits(min_free_storage_mb=5000, emergency_reserve_mb=1000))
    sensors = SensorReading(
        free_vram_mb=8000, free_ram_mb=8000, free_storage_mb=6500, thermal_ok=True
    )
    denied = sched.admit(
        "t1", "r", _profile(ResourceClass.GPU_LIGHT, storage=1000), now=0, sensors=sensors
    )
    assert denied.outcome is AdmissionOutcome.DENIED_OVERCOMMIT


def test_missing_sensor_triggers_reduced_monitoring_but_still_admits() -> None:
    sched = ResourceScheduler()
    result = sched.admit("t1", "r", _profile(ResourceClass.GPU_LIGHT, vram=1000), now=0)
    assert result.admitted
    assert result.monitoring is MonitoringMode.REDUCED_MONITORING


def test_full_monitoring_with_all_sensors_present() -> None:
    sched = ResourceScheduler()
    sensors = SensorReading(
        free_vram_mb=8000, free_ram_mb=8000, free_storage_mb=100000, thermal_ok=True
    )
    result = sched.admit(
        "t1", "r", _profile(ResourceClass.GPU_LIGHT, vram=1000), now=0, sensors=sensors
    )
    assert result.monitoring is MonitoringMode.FULL


def test_cooldown_blocks_immediate_readmission() -> None:
    sched = ResourceScheduler(SchedulerLimits(cooldown_ticks=5))
    admitted = sched.admit(
        "t1", "OLLAMA:qwen3:8b", _profile(ResourceClass.GPU_LIGHT, vram=1000), now=0
    )
    sched.release(admitted.reservation.reservation_id, now=1)  # type: ignore[union-attr]
    blocked = sched.admit(
        "t2", "OLLAMA:qwen3:8b", _profile(ResourceClass.GPU_LIGHT, vram=1000), now=3
    )
    assert blocked.outcome is AdmissionOutcome.DENIED_COOLDOWN
    ok = sched.admit("t3", "OLLAMA:qwen3:8b", _profile(ResourceClass.GPU_LIGHT, vram=1000), now=6)
    assert ok.admitted  # cooldown elapsed


def test_release_is_idempotent() -> None:
    sched = ResourceScheduler()
    res = sched.admit("t1", "r", _profile(ResourceClass.GPU_LIGHT, vram=1000), now=0).reservation
    assert sched.release(res.reservation_id, now=1) is True  # type: ignore[union-attr]
    assert sched.release(res.reservation_id, now=2) is False  # type: ignore[union-attr]


def test_pressure_order_prioritizes_gpu_heavy_then_recency() -> None:
    sched = ResourceScheduler(SchedulerLimits(max_gpu_heavy=1, max_vram_mb=100000))
    sched.admit("t1", "cpu", _profile(ResourceClass.CPU_ONLY), now=0)
    sched.admit("t2", "heavy", _profile(ResourceClass.GPU_HEAVY, vram=1000), now=1)
    sched.admit("t3", "light", _profile(ResourceClass.GPU_LIGHT, vram=1000), now=2)
    order = [r.route_key for r in sched.pressure_order()]
    assert order[0] == "heavy"  # GPU-heavy paused first


def test_reconcile_releases_orphans_and_adopts_live() -> None:
    sched = ResourceScheduler()
    sched.admit("t1", "orphan", _profile(ResourceClass.GPU_LIGHT, vram=1000), now=0)
    live = Reservation("resv-live", "t2", "live", _profile(ResourceClass.CPU_ONLY), acquired_at=0)
    orphans = sched.reconcile((live,), now=5)
    keys = {r.route_key for r in sched.active()}
    assert keys == {"live"}
    assert len(orphans) == 1
