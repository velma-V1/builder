"""PH-4 hardening — scheduler epoch/STALE reconciliation, revalidation, id-collision guards."""

from __future__ import annotations

from factory.routing import Reservation, ResourceClass, ResourceProfile, SchedulerLimits
from factory.scheduler import AdmissionOutcome, ResourceScheduler
from factory.scheduler.scheduler import _seq_of


def _profile(cls: ResourceClass = ResourceClass.GPU_LIGHT, vram: int = 1000) -> ResourceProfile:
    return ResourceProfile(cls, vram_mb=vram, ram_mb=1000, cpu_units=1, storage_mb=10)


def _resv(rid: str, route: str = "r", vram: int = 1000) -> Reservation:
    return Reservation(rid, "t1", route, _profile(vram=vram), acquired_at=0)


def test_seq_of_parses_and_rejects() -> None:
    assert _seq_of("resv-7") == 7
    assert _seq_of("resv-x") == 0
    assert _seq_of("other-3") == 0


def test_reconcile_marks_stale_advances_epoch_and_seq() -> None:
    sched = ResourceScheduler()
    sched.reconcile((_resv("resv-9"),), now=0)
    restored = sched.active()[0]
    assert restored.stale is True
    assert sched.epoch == 1  # default advances by one
    # A newly admitted reservation cannot collide with the restored resv-9 id.
    admitted = sched.admit("t2", "r2", _profile(), now=0)
    assert admitted.reservation is not None
    assert _seq_of(admitted.reservation.reservation_id) > 9


def test_reconcile_accepts_explicit_epoch_and_releases_orphans() -> None:
    sched = ResourceScheduler()
    sched.admit("t1", "orphan", _profile(), now=0)
    orphans = sched.reconcile((_resv("resv-50", route="live"),), now=1, new_epoch=42)
    assert sched.epoch == 42
    assert len(orphans) == 1
    assert {r.reservation_id for r in sched.active()} == {"resv-50"}


def test_revalidate_clears_stale_on_success() -> None:
    sched = ResourceScheduler()
    sched.reconcile((_resv("resv-1"),), now=0)
    ok = sched.revalidate("resv-1", now=1, task_ok=True, route_ok=True, resources_ok=True)
    assert ok is True
    assert sched.active()[0].stale is False


def test_revalidate_releases_when_task_invalid() -> None:
    sched = ResourceScheduler()
    sched.reconcile((_resv("resv-1"),), now=0)
    ok = sched.revalidate("resv-1", now=1, task_ok=False, route_ok=True, resources_ok=True)
    assert ok is False
    assert sched.active() == ()  # released


def test_revalidate_releases_on_resource_pressure() -> None:
    # A tiny VRAM ceiling means re-admission of the restored reservation now fails.
    sched = ResourceScheduler(SchedulerLimits(max_vram_mb=100))
    sched.reconcile((_resv("resv-1", vram=5000),), now=0)
    ok = sched.revalidate("resv-1", now=1, task_ok=True, route_ok=True, resources_ok=True)
    assert ok is False
    assert sched.active() == ()


def test_revalidate_unknown_and_non_stale() -> None:
    sched = ResourceScheduler()
    assert sched.revalidate("ghost", now=0, task_ok=True, route_ok=True, resources_ok=True) is False
    admitted = sched.admit("t1", "r", _profile(), now=0)
    assert admitted.reservation is not None
    # A freshly admitted (non-stale) reservation needs no revalidation.
    assert (
        sched.revalidate(
            admitted.reservation.reservation_id,
            now=0,
            task_ok=True,
            route_ok=True,
            resources_ok=True,
        )
        is True
    )


def test_gpu_heavy_single_active_still_enforced_after_hardening() -> None:
    sched = ResourceScheduler()
    a = sched.admit("t1", "aider", _profile(ResourceClass.GPU_HEAVY), now=0)
    assert a.admitted
    b = sched.admit("t2", "qwen", _profile(ResourceClass.GPU_HEAVY), now=0)
    assert b.outcome is AdmissionOutcome.DENIED_GPU_HEAVY_BUSY
