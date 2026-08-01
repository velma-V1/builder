"""Dry-run lifecycle, update failure, and last-known-good rollback preparation."""

from __future__ import annotations

import pytest

from factory.integrations.agent_zero.errors import AgentZeroError, AgentZeroErrorCode
from factory.integrations.agent_zero.lifecycle import (
    FUTURE_ISOLATION,
    LIFECYCLE_PHASES,
    build_lifecycle,
    deny_self_update,
    plan_update,
)
from factory.integrations.agent_zero.models import ModuleHealthState

pytestmark = pytest.mark.security


def test_lifecycle_is_dry_run_by_default_no_mutation() -> None:
    installer = build_lifecycle()
    report = installer.run()
    assert not report.mutated


def test_lifecycle_plan_declares_a_rollback_for_every_mutating_phase() -> None:
    plan = build_lifecycle().format_plan()
    assert "(MISSING)" not in plan


def test_lifecycle_phases_cover_the_full_managed_worker_lifecycle() -> None:
    assert LIFECYCLE_PHASES == (
        "inspect", "prepare", "install_later", "start_later", "health",
        "stop_later", "update_later", "rollback_later", "remove_later",
    )


def test_future_isolation_posture_defaults_to_fully_isolated() -> None:
    assert FUTURE_ISOLATION.no_docker_socket
    assert FUTURE_ISOLATION.no_host_networking
    assert FUTURE_ISOLATION.egress_via_broker_only
    assert FUTURE_ISOLATION.non_root


def test_update_failure_when_worker_reports_a_newer_major_version() -> None:
    decision = plan_update(
        current_version="1.2.0", candidate_version="2.0.0", builder_contract_version="1.5.0",
        post_update_health=ModuleHealthState.HEALTHY,
    )
    assert not decision.applied
    assert not decision.rolled_back
    assert decision.active_version == "1.2.0"
    assert "major version mismatch" in decision.reason


def test_update_failure_when_candidate_version_is_unparseable() -> None:
    decision = plan_update(
        current_version="1.2.0", candidate_version="not-a-version",
        builder_contract_version="1.5.0", post_update_health=ModuleHealthState.HEALTHY,
    )
    assert not decision.applied
    assert "unparseable" in decision.reason


def test_last_known_good_rollback_when_post_update_health_is_unavailable() -> None:
    decision = plan_update(
        current_version="1.2.0", candidate_version="1.3.0", builder_contract_version="1.5.0",
        post_update_health=ModuleHealthState.UNAVAILABLE,
    )
    assert not decision.applied
    assert decision.rolled_back
    assert decision.active_version == "1.2.0"  # reverted to last-known-good, not the candidate
    assert "last-known-good" in decision.reason


def test_update_applied_when_compatible_and_healthy() -> None:
    decision = plan_update(
        current_version="1.2.0", candidate_version="1.3.0", builder_contract_version="1.5.0",
        post_update_health=ModuleHealthState.HEALTHY,
    )
    assert decision.applied
    assert not decision.rolled_back
    assert decision.active_version == "1.3.0"


def test_deny_self_update_when_actor_is_not_builder() -> None:
    with pytest.raises(AgentZeroError) as excinfo:
        deny_self_update("agent_zero")
    assert excinfo.value.code is AgentZeroErrorCode.SELF_UPDATE_DENIED


def test_builder_triggered_update_is_permitted() -> None:
    deny_self_update("builder")  # must not raise
