"""PH-4 integration — disclosed fallback with reverification + restart reconciliation."""

from __future__ import annotations

import pytest

from factory.models.ollama_adapter import FakeOllamaAdapter
from factory.routing import (
    ApprovedRoster,
    ExecutionLedger,
    ExecutionRecord,
    ExecutionStatus,
    HealthLedger,
    ManualClock,
    ModelRouter,
    Provider,
    QuotaLimits,
    Reservation,
    ResourceClass,
    ResourceProfile,
    RouteRequest,
    RoutingSnapshot,
    TaskType,
)
from factory.scheduler import QuotaLedger, ResourceScheduler
from factory.workers.aider_adapter import FakeAiderWorker


@pytest.fixture
def heavy_request() -> RouteRequest:
    profile = ResourceProfile(
        ResourceClass.GPU_HEAVY, vram_mb=6000, ram_mb=6000, cpu_units=1, storage_mb=100
    )
    return RouteRequest("t1", "s1", TaskType.HARD_CODING, profile)


def _router(aider_available: bool) -> ModelRouter:
    return ModelRouter(
        roster=ApprovedRoster.activate(),
        scheduler=ResourceScheduler(),
        quota=QuotaLedger(QuotaLimits(100, 100000, 100000)),
        ledger=ExecutionLedger(),
        health=HealthLedger(),
        adapters={
            Provider.OLLAMA: FakeOllamaAdapter(),
            Provider.AIDER: FakeAiderWorker(available=aider_available),
        },
        clock=ManualClock(),
    )


def test_fallback_opens_new_record_and_discloses_substitution(heavy_request: RouteRequest) -> None:
    router = _router(aider_available=False)
    # First attempt routes to AIDER (first HARD_CODING candidate), which is offline.
    failed = router.execute(heavy_request).record
    assert failed is not None
    assert failed.route_key == "AIDER:aider"
    assert failed.status is ExecutionStatus.RUNTIME_UNAVAILABLE

    # Disclosed fallback to an approved local supervisor model.
    outcome = router.fallback(
        failed.record_id, heavy_request, substitute_route_key="OLLAMA:qwen3:14b"
    )
    assert outcome.record is not None
    new = outcome.record
    assert new.route_key == "OLLAMA:qwen3:14b"
    assert new.status is ExecutionStatus.SUCCEEDED
    assert new.supersedes == failed.record_id  # provenance link, not a mutation
    assert new.reverification_required is True  # 01J §3.2 rerun-affected-gates
    assert outcome.reverification_required is True
    assert new.attempt == failed.attempt + 1

    fallbacks = router.snapshot().records
    assert len(fallbacks) == 2  # both attempts preserved (append-only)


def test_fallback_records_a_disclosed_fallback_entry(heavy_request: RouteRequest) -> None:
    router = _router(aider_available=False)
    failed = router.execute(heavy_request).record
    assert failed is not None
    router.fallback(failed.record_id, heavy_request, substitute_route_key="OLLAMA:qwen3:14b")
    # The disclosed FallbackRecord links the two attempts and lists reverification gates.
    disclosed = router.fallbacks()
    assert len(disclosed) == 1
    assert disclosed[0].from_record_id == failed.record_id
    assert disclosed[0].reverification_gates


def test_restart_reconciliation_restores_usage_and_reports_in_flight(
    heavy_request: RouteRequest,
) -> None:
    live = _router(aider_available=True)
    # A completed task charges quota; snapshot captures durable state.
    ok_request = RouteRequest(
        "t9",
        "s9",
        TaskType.DISPATCH,
        ResourceProfile(ResourceClass.GPU_LIGHT, 1000, 1000, 1, 100),
    )
    live.execute(ok_request)
    snapshot = live.snapshot()

    # A fresh process reconciles from the durable snapshot, plus a simulated in-flight attempt.
    in_flight = ExecutionRecord(
        record_id="exec-inflight",
        task_id="t1",
        stage_id="s1",
        attempt=1,
        route_key="OLLAMA:qwen3:8b",
        fingerprint_digest="d",
        status=ExecutionStatus.RUNNING,
        started_at=0,
        reason="crashed mid-run",
    )
    orphan = Reservation(
        "resv-orphan",
        "t1",
        "OLLAMA:qwen3:8b",
        ResourceProfile(ResourceClass.GPU_LIGHT, 1000, 1000, 1, 100),
        acquired_at=0,
    )
    durable = RoutingSnapshot(
        reservations=(orphan,), records=(*snapshot.records, in_flight), usage=snapshot.usage
    )

    fresh = _router(aider_available=True)
    resumable = fresh.reconcile_restart(durable)
    assert [r.record_id for r in resumable] == ["exec-inflight"]  # RUNNING surfaced for resume
    assert fresh.snapshot().usage == snapshot.usage  # quota usage restored
    assert {r.reservation_id for r in fresh.snapshot().reservations} == {"resv-orphan"}
