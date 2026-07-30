"""PH-4 failure paths — timeouts, cancellation, malformed output, quota, admission denial."""

from __future__ import annotations

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
    SchedulerLimits,
    TaskType,
)
from factory.routing.errors import RoutingError
from factory.scheduler import QuotaLedger, ResourceScheduler

pytestmark = pytest.mark.failure_path


def _router(
    *,
    quota: QuotaLedger | None = None,
    scheduler: ResourceScheduler | None = None,
    behaviors: dict[str, ExecutionStatus] | None = None,
) -> ModelRouter:
    return ModelRouter(
        roster=ApprovedRoster.activate(),
        scheduler=scheduler if scheduler is not None else ResourceScheduler(),
        quota=quota if quota is not None else QuotaLedger(QuotaLimits(100, 100000, 100000)),
        ledger=ExecutionLedger(),
        health=HealthLedger(),
        adapters={Provider.OLLAMA: FakeOllamaAdapter(behaviors=behaviors or {})},
        clock=ManualClock(),
    )


def _req() -> RouteRequest:
    profile = ResourceProfile(ResourceClass.GPU_LIGHT, 1000, 1000, 1, 100)
    return RouteRequest("t1", "s1", TaskType.DISPATCH, profile)


def test_timeout_is_recorded_as_terminal() -> None:
    router = _router(behaviors={"qwen3:8b": ExecutionStatus.TIMED_OUT})
    outcome = router.execute(_req())
    assert outcome.record is not None
    assert outcome.record.status is ExecutionStatus.TIMED_OUT
    assert outcome.record.error_code == "TIMEOUT"


def test_malformed_output_never_succeeds() -> None:
    router = _router(behaviors={"qwen3:8b": ExecutionStatus.FAILED})
    outcome = router.execute(_req())
    assert outcome.record is not None
    assert outcome.record.status is ExecutionStatus.FAILED


def test_quota_exhaustion_blocks_charge() -> None:
    quota = QuotaLedger(QuotaLimits(max_requests=0, max_tokens=0, max_wall_time=0))
    router = _router(quota=quota)
    with pytest.raises(RoutingError) as exc:
        router.execute(_req())
    assert exc.value.code == "QUOTA_EXCEEDED"


def test_admission_denied_produces_no_record() -> None:
    router = _router(scheduler=ResourceScheduler(SchedulerLimits(max_vram_mb=0)))
    outcome = router.execute(_req())
    assert not outcome.admission.admitted
    assert outcome.record is None


def test_fallback_from_unknown_record_is_rejected() -> None:
    router = _router()
    with pytest.raises(RoutingError) as exc:
        router.fallback("ghost", _req(), substitute_route_key="OLLAMA:qwen3:14b")
    assert exc.value.code == "FALLBACK_UNKNOWN"


def test_fallback_denied_admission_yields_no_new_record() -> None:
    # First attempt fails (timeout) and is recorded; the substitute then cannot be admitted
    # (its profile exceeds every VRAM ceiling), so fallback returns a denied outcome with no record.
    router = _router(behaviors={"qwen3:8b": ExecutionStatus.TIMED_OUT})
    seeded = router.execute(_req()).record
    assert seeded is not None
    oversized = RouteRequest(
        "t1", "s1", TaskType.HARD_CODING,
        ResourceProfile(ResourceClass.GPU_HEAVY, 999999, 999999, 1, 100),
    )
    outcome = router.fallback(seeded.record_id, oversized, substitute_route_key="OLLAMA:qwen3:14b")
    assert not outcome.admission.admitted
    assert outcome.record is None
    assert outcome.reverification_required is True


def test_fallback_substitute_that_also_fails_is_recorded() -> None:
    # The substitute times out too: a new (failed) record still supersedes, still flags reverify.
    router = _router(
        behaviors={"qwen3:8b": ExecutionStatus.TIMED_OUT, "qwen3:14b": ExecutionStatus.TIMED_OUT}
    )
    failed = router.execute(_req()).record
    assert failed is not None
    heavy = RouteRequest(
        "t1", "s1", TaskType.DISPATCH,
        ResourceProfile(ResourceClass.GPU_LIGHT, 1000, 1000, 1, 100),
    )
    outcome = router.fallback(failed.record_id, heavy, substitute_route_key="OLLAMA:qwen3:14b")
    assert outcome.record is not None
    assert outcome.record.status is ExecutionStatus.TIMED_OUT
    assert outcome.record.supersedes == failed.record_id
    assert outcome.record.reverification_required is True
