"""PH-4 hardening — restart reconciliation restores history without id collisions."""

from __future__ import annotations

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
    UsageCounters,
)
from factory.scheduler import QuotaLedger, ResourceScheduler


def _fresh_router() -> ModelRouter:
    return ModelRouter(
        roster=ApprovedRoster.activate(),
        scheduler=ResourceScheduler(),
        quota=QuotaLedger(QuotaLimits(1000, 10**9, 10**9)),
        ledger=ExecutionLedger(),
        health=HealthLedger(),
        adapters={Provider.OLLAMA: FakeOllamaAdapter()},
        clock=ManualClock(),
    )


def _rec(rid: str, status: ExecutionStatus) -> ExecutionRecord:
    return ExecutionRecord(rid, "t1", "s1", 1, "OLLAMA:qwen3:8b", "d", status, 0, "r")


def test_restart_rebuilds_history_and_resumes_in_flight() -> None:
    snapshot = RoutingSnapshot(
        reservations=(
            Reservation(
                "resv-3",
                "t1",
                "OLLAMA:qwen3:8b",
                ResourceProfile(ResourceClass.GPU_LIGHT, 1, 1, 1, 1),
                acquired_at=0,
            ),
        ),
        records=(
            _rec("exec-1", ExecutionStatus.SUCCEEDED),
            _rec("exec-2", ExecutionStatus.RUNNING),
        ),
        usage=(("default", UsageCounters(requests=5, tokens=50, wall_time=5)),),
    )
    router = _fresh_router()
    resumable = router.reconcile_restart(snapshot)

    # History rebuilt; the RUNNING attempt is surfaced for bounded resume.
    assert [r.record_id for r in resumable] == ["exec-2"]
    assert {r.record_id for r in router.snapshot().records} == {"exec-1", "exec-2"}
    assert router.snapshot().usage == (("default", UsageCounters(5, 50, 5)),)
    # Prior reservation adopted as STALE (must be revalidated before reactivation).
    assert router.snapshot().reservations[0].stale is True


def test_new_record_after_restart_does_not_collide() -> None:
    snapshot = RoutingSnapshot(
        records=(
            _rec("exec-1", ExecutionStatus.SUCCEEDED),
            _rec("exec-2", ExecutionStatus.RUNNING),
        ),
    )
    router = _fresh_router()
    router.reconcile_restart(snapshot)
    outcome = router.execute(
        RouteRequest(
            "t9", "s9", TaskType.DISPATCH, ResourceProfile(ResourceClass.GPU_LIGHT, 1, 1, 1, 1)
        )
    )
    assert outcome.record is not None
    # The id sequence advanced past the restored ids: the new record is exec-3, not a duplicate.
    assert outcome.record.record_id == "exec-3"
    assert outcome.record.record_id not in {"exec-1", "exec-2"}


def test_reconcile_restart_is_idempotent() -> None:
    # Restoring the same snapshot twice must not raise RECORD_DUPLICATE (restore skips present ids).
    snapshot = RoutingSnapshot(records=(_rec("exec-1", ExecutionStatus.SUCCEEDED),))
    router = _fresh_router()
    router.reconcile_restart(snapshot)
    router.reconcile_restart(snapshot)  # idempotent replay
    assert {r.record_id for r in router.snapshot().records} == {"exec-1"}
