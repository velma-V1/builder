"""PH-4 hardening — reservation cleanup on failure, all-outcome accounting, quota atomicity."""

from __future__ import annotations

import threading
from collections.abc import Mapping

import pytest

from factory.models.ollama_adapter import FakeOllamaAdapter
from factory.routing import (
    ApprovedRoster,
    ExecutionLedger,
    ExecutionStatus,
    HealthLedger,
    ManualClock,
    ModelRouter,
    Provider,
    QuotaLimits,
    ResourceClass,
    ResourceProfile,
    RouteRequest,
    RuntimeStatus,
    SchedulerLimits,
    TaskType,
)
from factory.routing.adapters import ProviderAdapter
from factory.routing.errors import RoutingError
from factory.scheduler import QuotaLedger, ResourceScheduler

pytestmark = pytest.mark.failure_path


def _build(
    *,
    quota: QuotaLedger | None = None,
    scheduler: ResourceScheduler | None = None,
    adapters: Mapping[Provider, ProviderAdapter] | None = None,
    behaviors: Mapping[str, ExecutionStatus] | None = None,
) -> tuple[ModelRouter, ResourceScheduler, QuotaLedger]:
    sched = (
        scheduler
        if scheduler is not None
        else ResourceScheduler(
            # cooldown_ticks=0 so repeated same-route admits under a fixed clock are not throttled.
            SchedulerLimits(
                max_vram_mb=10**9, max_ram_mb=10**9, cpu_concurrency=10**6, cooldown_ticks=0
            )
        )
    )
    q = quota if quota is not None else QuotaLedger(QuotaLimits(10**6, 10**9, 10**9))
    router = ModelRouter(
        roster=ApprovedRoster.activate(),
        scheduler=sched,
        quota=q,
        ledger=ExecutionLedger(),
        health=HealthLedger(),
        adapters=adapters
        if adapters is not None
        else {Provider.OLLAMA: FakeOllamaAdapter(behaviors=behaviors or {})},
        clock=ManualClock(),
    )
    return router, sched, q


def _req(task: str = "t1", ttype: TaskType = TaskType.DISPATCH) -> RouteRequest:
    return RouteRequest(task, "s1", ttype, ResourceProfile(ResourceClass.GPU_LIGHT, 1, 1, 1, 1))


def test_reservation_released_when_quota_charge_raises() -> None:
    router, sched, _ = _build(quota=QuotaLedger(QuotaLimits(0, 0, 0)))
    with pytest.raises(RoutingError) as exc:
        router.execute(_req())
    assert exc.value.code == "QUOTA_EXCEEDED"
    assert sched.active() == ()  # try/finally released the reservation, no leak


def test_reservation_released_when_adapter_missing() -> None:
    router, sched, _ = _build(adapters={})  # no OLLAMA adapter -> ADAPTER_MISSING mid-execute
    with pytest.raises(RoutingError) as exc:
        router.execute(_req())
    assert exc.value.code == "ADAPTER_MISSING"
    assert sched.active() == ()


def test_accounting_covers_every_outcome() -> None:
    # success
    router, _, _ = _build()
    router.execute(_req("ok"))
    # failed (malformed), timed out
    router2, _, _ = _build(behaviors={"qwen3:8b": ExecutionStatus.FAILED})
    router2.execute(_req("bad"))
    router3, _, _ = _build(behaviors={"qwen3:8b": ExecutionStatus.TIMED_OUT})
    router3.execute(_req("slow"))
    # cancelled
    cancel_adapter = FakeOllamaAdapter()
    cancel_adapter.cancel("cx")  # the next call for task "cx" returns CANCELLED
    router4, _, _ = _build(adapters={Provider.OLLAMA: cancel_adapter})
    router4.execute(_req("cx"))
    # runtime unavailable
    router5, _, _ = _build(
        adapters={Provider.OLLAMA: FakeOllamaAdapter(status=RuntimeStatus.UNAVAILABLE)}
    )
    router5.execute(_req("down"))

    assert router.accounting()[ExecutionStatus.SUCCEEDED] == 1
    assert router2.accounting()[ExecutionStatus.FAILED] == 1
    assert router3.accounting()[ExecutionStatus.TIMED_OUT] == 1
    assert router4.accounting()[ExecutionStatus.CANCELLED] == 1
    assert router5.accounting()[ExecutionStatus.RUNTIME_UNAVAILABLE] == 1


def test_every_attempt_charges_one_request() -> None:
    router, _, quota = _build(behaviors={"qwen3:8b": ExecutionStatus.TIMED_OUT})
    router.execute(_req("t1"))
    router.execute(_req("t2"))
    # Even failed/timed-out attempts are accounted: two attempts -> two requests charged.
    assert quota.usage_for("default").requests == 2


def test_concurrent_executes_have_unique_record_ids() -> None:
    router, _, _ = _build()
    ids: list[str] = []
    lock = threading.Lock()
    barrier = threading.Barrier(8)

    def run(i: int) -> None:
        barrier.wait()
        outcome = router.execute(_req(f"task-{i}"))
        assert outcome.record is not None
        with lock:
            ids.append(outcome.record.record_id)

    threads = [threading.Thread(target=run, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(ids) == 8
    assert len(set(ids)) == 8  # no duplicate/colliding record ids under concurrency


def test_quota_charge_is_atomic_under_contention() -> None:
    quota = QuotaLedger(QuotaLimits(max_requests=1000, max_tokens=10**9, max_wall_time=10**9))
    barrier = threading.Barrier(16)

    def charge() -> None:
        barrier.wait()
        for _ in range(10):
            quota.charge("s", requests=1, tokens=1, wall_time=1)

    threads = [threading.Thread(target=charge) for _ in range(16)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    # 16 threads * 10 charges, each +1 request: exactly 160, no lost updates.
    assert quota.usage_for("s").requests == 160
