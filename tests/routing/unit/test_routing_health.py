"""PH-4 unit — health-check trigger conditions (``01J §3.4``) + health ledger."""

from __future__ import annotations

from factory.routing import (
    HealthContext,
    HealthLedger,
    HealthState,
    TaskType,
    health_check_required,
)
from factory.routing.models import HealthRecord


def _valid_cached(now: int = 0) -> HealthRecord:
    return HealthRecord(
        "OLLAMA:qwen3:8b", HealthState.HEALTHY, checked_at=now, expires_at=now + 100, reason="ok"
    )


def test_consequential_task_always_requires_check() -> None:
    assert health_check_required(
        TaskType.ARCHITECTURE_REVIEW, HealthContext(), _valid_cached(), now=1
    )
    assert health_check_required(TaskType.REPAIR, HealthContext(), _valid_cached(), now=1)


def test_routine_task_with_valid_cache_skips_check() -> None:
    assert (
        health_check_required(TaskType.DISPATCH, HealthContext(), _valid_cached(), now=1) is False
    )


def test_missing_cache_requires_check() -> None:
    assert health_check_required(TaskType.DISPATCH, HealthContext(), None, now=1)


def test_expired_cache_requires_check() -> None:
    cached = HealthRecord("OLLAMA:qwen3:8b", HealthState.HEALTHY, 0, 5, "ok")
    assert health_check_required(TaskType.DISPATCH, HealthContext(), cached, now=10)


def test_protected_write_and_runtime_change_and_instability_trigger_check() -> None:
    assert health_check_required(
        TaskType.DISPATCH, HealthContext(writes_protected_state=True), _valid_cached(), now=1
    )
    assert health_check_required(
        TaskType.DISPATCH, HealthContext(runtime_changed_since_check=True), _valid_cached(), now=1
    )
    assert health_check_required(
        TaskType.DISPATCH, HealthContext(recent_instability=True), _valid_cached(), now=1
    )


def test_health_ledger_records_and_reports_validity() -> None:
    ledger = HealthLedger()
    assert ledger.latest("OLLAMA:qwen3:8b") is None
    ledger.check("OLLAMA:qwen3:8b", healthy=True, now=0, ttl=10, reason="ok")
    assert ledger.is_valid("OLLAMA:qwen3:8b", now=5)
    assert not ledger.is_valid("OLLAMA:qwen3:8b", now=20)
    ledger.check("OLLAMA:qwen3:8b", healthy=False, now=21, ttl=10, reason="bad")
    assert ledger.latest("OLLAMA:qwen3:8b").state is HealthState.UNHEALTHY  # type: ignore[union-attr]
    assert not ledger.is_valid("OLLAMA:qwen3:8b", now=22)
