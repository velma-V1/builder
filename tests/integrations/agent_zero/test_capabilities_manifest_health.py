"""Capability discovery, manifest posture, provenance chain, and health derivation."""

from __future__ import annotations

from factory.integrations.agent_zero.capabilities import CapabilitySet
from factory.integrations.agent_zero.health import check_health
from factory.integrations.agent_zero.manifest import AGENT_ZERO_MANIFEST, MANAGED_WORKER_OBLIGATIONS
from factory.integrations.agent_zero.models import ModuleHealthState
from factory.integrations.agent_zero.provenance import build_provenance


def test_capability_set_supports_only_granted_tools() -> None:
    capabilities = CapabilitySet("wo-1", frozenset({"read_file", "write_patch"}))
    assert capabilities.supports("read_file")
    assert not capabilities.supports("shell_exec")


def test_manifest_pins_verified_official_release_and_license() -> None:
    assert AGENT_ZERO_MANIFEST.upstream_repo == "github.com/agent0ai/agent-zero"
    assert AGENT_ZERO_MANIFEST.pinned_release == "v2.7"
    assert AGENT_ZERO_MANIFEST.pinned_commit == "87e1e591e1ba2e8b1a19d34e134fcae490c8dded"
    assert AGENT_ZERO_MANIFEST.license == "MIT"
    assert AGENT_ZERO_MANIFEST.license_verified is True
    assert AGENT_ZERO_MANIFEST.revision_verified is True
    assert bool(MANAGED_WORKER_OBLIGATIONS)


def test_provenance_chain_never_asserts_verification_happened() -> None:
    steps = build_provenance(
        work_order_id="wo-1", run_id="run-1", submitted_at=1000, worker_reported_version="1.0.0"
    )
    assert steps[0].stage == "work_order"
    assert "unverified claim" in steps[-1].detail


def test_health_is_unavailable_with_no_recorded_interaction() -> None:
    health = check_health(consecutive_failures=0, now=100, last_success_at=None)
    assert health.state is ModuleHealthState.UNAVAILABLE


def test_health_degrades_after_a_failure_and_recovers_after_success() -> None:
    degraded = check_health(consecutive_failures=1, now=100, last_success_at=50)
    assert degraded.state is ModuleHealthState.DEGRADED
    healthy = check_health(consecutive_failures=0, now=100, last_success_at=100)
    assert healthy.state is ModuleHealthState.HEALTHY


def test_health_is_unavailable_after_repeated_consecutive_failures() -> None:
    health = check_health(consecutive_failures=3, now=100, last_success_at=10)
    assert health.state is ModuleHealthState.UNAVAILABLE
