"""Shared fixtures for the PH-4 (Section 4) routing preinstallation test suite."""

from __future__ import annotations

import pytest

from factory.models.ollama_adapter import FakeOllamaAdapter
from factory.routing import (
    ApprovedRoster,
    ExecutionLedger,
    HealthLedger,
    ManualClock,
    ModelRouter,
    Provider,
    QuotaLimits,
    ResourceClass,
    ResourceProfile,
    RouteRequest,
    TaskType,
)
from factory.scheduler import QuotaLedger, ResourceScheduler
from factory.workers.aider_adapter import FakeAiderWorker


@pytest.fixture
def roster() -> ApprovedRoster:
    return ApprovedRoster.activate()


@pytest.fixture
def clock() -> ManualClock:
    return ManualClock()


@pytest.fixture
def ollama() -> FakeOllamaAdapter:
    return FakeOllamaAdapter()


@pytest.fixture
def aider() -> FakeAiderWorker:
    return FakeAiderWorker()


@pytest.fixture
def router(
    roster: ApprovedRoster,
    clock: ManualClock,
    ollama: FakeOllamaAdapter,
    aider: FakeAiderWorker,
) -> ModelRouter:
    return ModelRouter(
        roster=roster,
        scheduler=ResourceScheduler(),
        quota=QuotaLedger(QuotaLimits(max_requests=100, max_tokens=100_000, max_wall_time=100_000)),
        ledger=ExecutionLedger(),
        health=HealthLedger(),
        adapters={Provider.OLLAMA: ollama, Provider.AIDER: aider},
        clock=clock,
    )


@pytest.fixture
def light_profile() -> ResourceProfile:
    return ResourceProfile(
        ResourceClass.GPU_LIGHT, vram_mb=4000, ram_mb=4000, cpu_units=1, storage_mb=100
    )


@pytest.fixture
def dispatch_request(light_profile: ResourceProfile) -> RouteRequest:
    return RouteRequest(
        task_id="t1", stage_id="s1", task_type=TaskType.DISPATCH, profile=light_profile
    )
