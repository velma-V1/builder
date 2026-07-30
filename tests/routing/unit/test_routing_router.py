"""PH-4 unit — deterministic router: selection, override, privacy, execution, clock."""

from __future__ import annotations

import pytest

from factory.models.ollama_adapter import FakeOllamaAdapter
from factory.routing import (
    ApprovedRoster,
    ExecutionLedger,
    ExecutionStatus,
    HealthContext,
    HealthLedger,
    ManualClock,
    ModelRouter,
    Privacy,
    Provider,
    QuotaLimits,
    ResourceProfile,
    RouteRequest,
    TaskType,
)
from factory.routing.errors import RoutingError
from factory.scheduler import QuotaLedger, ResourceScheduler


def test_manual_clock_advances_and_rejects_backward() -> None:
    clock = ManualClock(5)
    assert clock.now() == 5
    assert clock.advance(3) == 8
    with pytest.raises(RoutingError) as exc:
        clock.advance(-1)
    assert exc.value.code == "CLOCK_BACKWARD"


def test_route_is_deterministic_and_visible(
    router: ModelRouter, dispatch_request: RouteRequest
) -> None:
    decision = router.route(dispatch_request)
    assert decision.selected.route_key == "OLLAMA:qwen3:8b"
    assert "deterministic roster selection" in decision.reason
    assert decision.operator_override is False
    assert decision.candidates == ("OLLAMA:qwen3:8b",)


def test_local_only_privacy_excludes_hosted_route(
    router: ModelRouter, light_profile: ResourceProfile
) -> None:
    # HARD_CODING lists aider (local) first, then qwen14b (local), then a hosted route.
    req = RouteRequest("t", "s", TaskType.HARD_CODING, light_profile, privacy=Privacy.LOCAL_ONLY)
    decision = router.route(req)
    assert decision.selected.is_local


def test_hosted_only_route_needs_cloud_permission(light_profile: ResourceProfile) -> None:
    # Only-hosted route for a task: LOCAL_ONLY fails closed; CLOUD_ALLOWED selects it.
    roster = ApprovedRoster.activate(routes={TaskType.PLANNING: ("GROQ:qwen/qwen3.6-27b",)})
    router = ModelRouter(
        roster=roster,
        scheduler=ResourceScheduler(),
        quota=QuotaLedger(QuotaLimits(100, 100000, 100000)),
        ledger=ExecutionLedger(),
        health=HealthLedger(),
        adapters={Provider.GROQ: FakeOllamaAdapter(installed_models=("qwen/qwen3.6-27b",))},
        clock=ManualClock(),
    )
    local_only = RouteRequest(
        "t", "s", TaskType.PLANNING, light_profile, privacy=Privacy.LOCAL_ONLY
    )
    with pytest.raises(RoutingError) as exc:
        router.route(local_only)
    assert exc.value.code == "NO_APPROVED_ROUTE"
    cloud = RouteRequest("t", "s", TaskType.PLANNING, light_profile, privacy=Privacy.CLOUD_ALLOWED)
    assert router.route(cloud).selected.route_key == "GROQ:qwen/qwen3.6-27b"


def test_operator_override_selects_named_route(
    router: ModelRouter, light_profile: ResourceProfile
) -> None:
    req = RouteRequest(
        "t", "s", TaskType.DISPATCH, light_profile, operator_override="OLLAMA:qwen3:14b"
    )
    decision = router.route(req)
    assert decision.selected.route_key == "OLLAMA:qwen3:14b"
    assert decision.operator_override is True


def test_operator_override_unapproved_is_rejected(
    router: ModelRouter, light_profile: ResourceProfile
) -> None:
    req = RouteRequest("t", "s", TaskType.DISPATCH, light_profile, operator_override="OLLAMA:ghost")
    with pytest.raises(RoutingError) as exc:
        router.route(req)
    assert exc.value.code == "OVERRIDE_UNAPPROVED"


def test_operator_override_violating_privacy_is_rejected(
    router: ModelRouter, light_profile: ResourceProfile
) -> None:
    req = RouteRequest(
        "t",
        "s",
        TaskType.DISPATCH,
        light_profile,
        privacy=Privacy.LOCAL_ONLY,
        operator_override="GROQ:qwen/qwen3.6-27b",
    )
    with pytest.raises(RoutingError) as exc:
        router.route(req)
    assert exc.value.code == "OVERRIDE_PRIVACY"


def test_consequential_task_flags_health_check(
    router: ModelRouter, light_profile: ResourceProfile
) -> None:
    req = RouteRequest("t", "s", TaskType.REPAIR, light_profile, health_context=HealthContext())
    assert router.route(req).health_check_required is True


def test_execute_success_records_and_charges(
    router: ModelRouter, dispatch_request: RouteRequest
) -> None:
    outcome = router.execute(dispatch_request)
    assert outcome.admission.admitted
    assert outcome.record is not None
    assert outcome.record.status is ExecutionStatus.SUCCEEDED
    assert outcome.record.fingerprint_digest  # complete fingerprint attached
    assert outcome.record.attempt == 1


def test_execute_denied_admission_makes_no_call(light_profile: ResourceProfile) -> None:
    # A scheduler with no VRAM headroom denies admission; no record/call is produced.
    from factory.routing import SchedulerLimits

    router = ModelRouter(
        roster=ApprovedRoster.activate(),
        scheduler=ResourceScheduler(SchedulerLimits(max_vram_mb=0)),
        quota=QuotaLedger(QuotaLimits(100, 100000, 100000)),
        ledger=ExecutionLedger(),
        health=HealthLedger(),
        adapters={Provider.OLLAMA: FakeOllamaAdapter()},
        clock=ManualClock(),
    )
    req = RouteRequest("t", "s", TaskType.DISPATCH, light_profile)
    outcome = router.execute(req)
    assert not outcome.admission.admitted
    assert outcome.record is None
    assert outcome.call is None


def test_execute_missing_adapter_raises(light_profile: ResourceProfile) -> None:
    router = ModelRouter(
        roster=ApprovedRoster.activate(),
        scheduler=ResourceScheduler(),
        quota=QuotaLedger(QuotaLimits(100, 100000, 100000)),
        ledger=ExecutionLedger(),
        health=HealthLedger(),
        adapters={},  # no OLLAMA adapter registered
        clock=ManualClock(),
    )
    req = RouteRequest("t", "s", TaskType.DISPATCH, light_profile)
    with pytest.raises(RoutingError) as exc:
        router.execute(req)
    assert exc.value.code == "ADAPTER_MISSING"
