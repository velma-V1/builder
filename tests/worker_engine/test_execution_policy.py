"""Phase 3B execution-policy boundary: the sandbox is an optional tool, never a mandatory
environment for every task. Proves the deterministic mode decision for all three modes, that
policy can force escalation regardless of what the worker requested, and that the worker can
never downgrade a policy-required mode.
"""

from __future__ import annotations

import pytest

from factory.worker_engine.execution_policy import (
    ExecutionMode,
    ExecutionPolicy,
    ExecutionPolicyInput,
    RiskClassification,
)


@pytest.fixture
def policy() -> ExecutionPolicy:
    return ExecutionPolicy()


def test_repository_inspection_task_selects_direct_read_only(policy: ExecutionPolicy) -> None:
    """Requirement 1: a repository inspection task uses DIRECT_READ_ONLY."""
    decision = policy.decide(
        ExecutionPolicyInput(
            requested_mode=ExecutionMode.DIRECT_READ_ONLY,
            command_type="read_file",
            write_intent=False,
            dependency_changes=False,
            risk_classification=RiskClassification.LOW,
        )
    )
    assert decision.selected_mode is ExecutionMode.DIRECT_READ_ONLY
    assert decision.requested_mode is ExecutionMode.DIRECT_READ_ONLY


@pytest.mark.parametrize(
    "command_type", ["search", "list_files", "diff_analysis", "dependency_inspection"]
)
def test_other_non_mutating_command_types_select_direct_read_only(
    policy: ExecutionPolicy, command_type: str
) -> None:
    decision = policy.decide(
        ExecutionPolicyInput(
            requested_mode=ExecutionMode.DIRECT_READ_ONLY,
            command_type=command_type,
            write_intent=False,
            dependency_changes=False,
            risk_classification=RiskClassification.LOW,
        )
    )
    assert decision.selected_mode is ExecutionMode.DIRECT_READ_ONLY


def test_proposed_file_modification_selects_staged_write(policy: ExecutionPolicy) -> None:
    """Requirement 3: a proposed file modification (no code execution) uses STAGED_WRITE."""
    decision = policy.decide(
        ExecutionPolicyInput(
            requested_mode=ExecutionMode.STAGED_WRITE,
            command_type="edit_file",
            write_intent=True,
            dependency_changes=False,
            risk_classification=RiskClassification.LOW,
        )
    )
    assert decision.selected_mode is ExecutionMode.STAGED_WRITE


@pytest.mark.parametrize(
    "command_type",
    ["execute", "run_script", "run_tests", "build", "install_dependency", "reproduce_failure"],
)
def test_generated_code_execution_task_selects_sandboxed_execution(
    policy: ExecutionPolicy, command_type: str
) -> None:
    """Requirement 4: a generated-code execution task uses SANDBOXED_EXECUTION."""
    decision = policy.decide(
        ExecutionPolicyInput(
            requested_mode=ExecutionMode.SANDBOXED_EXECUTION,
            command_type=command_type,
            write_intent=True,
            dependency_changes=False,
            risk_classification=RiskClassification.MEDIUM,
        )
    )
    assert decision.selected_mode is ExecutionMode.SANDBOXED_EXECUTION


def test_policy_forces_sandbox_even_when_worker_requests_read_only(
    policy: ExecutionPolicy,
) -> None:
    """Requirement 5: policy can force sandbox use regardless of the worker's own request."""
    decision = policy.decide(
        ExecutionPolicyInput(
            requested_mode=ExecutionMode.DIRECT_READ_ONLY,
            command_type="run_tests",
            write_intent=False,
            dependency_changes=False,
            risk_classification=RiskClassification.LOW,
        )
    )
    assert decision.requested_mode is ExecutionMode.DIRECT_READ_ONLY
    assert decision.selected_mode is ExecutionMode.SANDBOXED_EXECUTION
    assert decision.policy_rule == "RULE_EXECUTABLE_COMMAND_REQUIRES_SANDBOX"


def test_high_risk_classification_forces_sandbox(policy: ExecutionPolicy) -> None:
    decision = policy.decide(
        ExecutionPolicyInput(
            requested_mode=ExecutionMode.DIRECT_READ_ONLY,
            command_type="edit_file",
            write_intent=False,
            dependency_changes=False,
            risk_classification=RiskClassification.HIGH,
        )
    )
    assert decision.selected_mode is ExecutionMode.SANDBOXED_EXECUTION
    assert decision.policy_rule == "RULE_HIGH_RISK_REQUIRES_SANDBOX"


def test_dependency_changes_force_sandbox(policy: ExecutionPolicy) -> None:
    decision = policy.decide(
        ExecutionPolicyInput(
            requested_mode=ExecutionMode.STAGED_WRITE,
            command_type="edit_file",
            write_intent=True,
            dependency_changes=True,
            risk_classification=RiskClassification.LOW,
        )
    )
    assert decision.selected_mode is ExecutionMode.SANDBOXED_EXECUTION
    assert decision.policy_rule == "RULE_DEPENDENCY_CHANGE_REQUIRES_SANDBOX"


def test_worker_cannot_downgrade_a_policy_required_sandbox_operation(
    policy: ExecutionPolicy,
) -> None:
    """Requirement 6: the worker cannot downgrade forced sandbox execution by requesting a
    weaker mode -- installing a dependency always requires SANDBOXED_EXECUTION even if the
    worker asks for STAGED_WRITE or DIRECT_READ_ONLY."""
    for requested in (
        ExecutionMode.DIRECT_READ_ONLY,
        ExecutionMode.STAGED_WRITE,
        ExecutionMode.SANDBOXED_EXECUTION,
    ):
        decision = policy.decide(
            ExecutionPolicyInput(
                requested_mode=requested,
                command_type="install_dependency",
                write_intent=True,
                dependency_changes=True,
                risk_classification=RiskClassification.LOW,
            )
        )
        assert decision.selected_mode is ExecutionMode.SANDBOXED_EXECUTION, (
            f"requested={requested} must not be able to escape the sandbox requirement"
        )


def test_worker_cannot_downgrade_write_intent_below_staged_write(
    policy: ExecutionPolicy,
) -> None:
    """A worker claiming DIRECT_READ_ONLY while actually intending to write must still be
    escalated to at least STAGED_WRITE -- write_intent is authoritative input, not the worker's
    own claim about its request."""
    decision = policy.decide(
        ExecutionPolicyInput(
            requested_mode=ExecutionMode.DIRECT_READ_ONLY,
            command_type="edit_file",
            write_intent=True,
            dependency_changes=False,
            risk_classification=RiskClassification.LOW,
        )
    )
    assert decision.selected_mode is ExecutionMode.STAGED_WRITE


def test_task_policy_minimum_raises_the_floor_even_for_a_read_only_request(
    policy: ExecutionPolicy,
) -> None:
    decision = policy.decide(
        ExecutionPolicyInput(
            requested_mode=ExecutionMode.DIRECT_READ_ONLY,
            command_type="read_file",
            write_intent=False,
            dependency_changes=False,
            risk_classification=RiskClassification.LOW,
            task_policy_minimum=ExecutionMode.STAGED_WRITE,
        )
    )
    assert decision.selected_mode is ExecutionMode.STAGED_WRITE
    assert decision.policy_rule == "RULE_TASK_POLICY_FLOOR"


def test_repository_policy_minimum_raises_the_floor_repo_wide(policy: ExecutionPolicy) -> None:
    decision = policy.decide(
        ExecutionPolicyInput(
            requested_mode=ExecutionMode.DIRECT_READ_ONLY,
            command_type="read_file",
            write_intent=False,
            dependency_changes=False,
            risk_classification=RiskClassification.LOW,
            repository_policy_minimum=ExecutionMode.SANDBOXED_EXECUTION,
        )
    )
    assert decision.selected_mode is ExecutionMode.SANDBOXED_EXECUTION
    assert decision.policy_rule == "RULE_REPOSITORY_POLICY_FLOOR"


def test_decision_persists_requested_and_selected_mode_reason_and_rule(
    policy: ExecutionPolicy,
) -> None:
    """Requirement 10 (decision half): every decision carries exactly the fields Phase 3B
    persists -- requested mode, selected mode, reason, and the specific policy rule."""
    decision = policy.decide(
        ExecutionPolicyInput(
            requested_mode=ExecutionMode.DIRECT_READ_ONLY,
            command_type="run_tests",
            write_intent=False,
            dependency_changes=False,
            risk_classification=RiskClassification.LOW,
        )
    )
    assert decision.requested_mode is ExecutionMode.DIRECT_READ_ONLY
    assert decision.selected_mode is ExecutionMode.SANDBOXED_EXECUTION
    assert decision.reason
    assert decision.policy_rule
