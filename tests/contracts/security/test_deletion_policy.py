from pathlib import Path

import pytest

from factory.contracts.models import (
    CanonicalContract,
    ContractType,
    ErrorCode,
    ImpactResult,
    PolicyOutcome,
    ValidationIssue,
    ValidationReport,
)
from factory.contracts.policy.engine import PolicyEngine

pytestmark = pytest.mark.security

_VALID = ValidationReport(valid=True, issues=())


def _contract() -> CanonicalContract:
    return CanonicalContract(
        source_path=Path("contracts/tasks/PROJ-001/TASK-001/v1.yaml"),
        contract_type=ContractType.TASK,
        contract_id="TASK-001",
        version=1,
        schema_version="1.0",
        project_id="PROJ-001",
        canonical_bytes=b"{}",
        content_hash="0" * 64,
        document={},
        validation=_VALID,
    )


def _clean_impact() -> ImpactResult:
    return ImpactResult(
        compatible=True,
        ownership_conflicts=(),
        affected_components=(),
        required_tests=(),
        authority_expanded=False,
        evidence_weakened=False,
        protected_boundary_crossed=False,
        reasons=(),
    )


@pytest.mark.parametrize("evidence_passed", [True, False])
@pytest.mark.parametrize("rollback_available", [True, False])
def test_deletion_outside_ownership_always_denies(
    evidence_passed: bool, rollback_available: bool
) -> None:
    engine = PolicyEngine()
    decision = engine.decide(
        candidate=_contract(),
        impact=_clean_impact(),
        validation=_VALID,
        evidence_passed=evidence_passed,
        rollback_available=rollback_available,
        deletion_classification="outside_ownership",
    )
    assert decision.outcome is PolicyOutcome.DENY_SECURITY_VIOLATION


@pytest.mark.parametrize("evidence_passed", [True, False])
@pytest.mark.parametrize("rollback_available", [True, False])
def test_deletion_of_pre_existing_file_cannot_be_auto_approved_by_passing_tests(
    evidence_passed: bool, rollback_available: bool
) -> None:
    """01R Decision B: passing evidence/rollback availability must never bypass the
    approval gate for deleting a pre-existing source/test/schema/contract/decision/
    shared/user-authored file."""
    engine = PolicyEngine()
    decision = engine.decide(
        candidate=_contract(),
        impact=_clean_impact(),
        validation=_VALID,
        evidence_passed=evidence_passed,
        rollback_available=rollback_available,
        deletion_classification="pre_existing",
    )
    assert decision.outcome is PolicyOutcome.HUMAN_APPROVAL_REQUIRED


@pytest.mark.parametrize("evidence_passed", [True, False])
@pytest.mark.parametrize("rollback_available", [True, False])
def test_deletion_of_task_created_disposable_artifact_still_requires_approval(
    evidence_passed: bool, rollback_available: bool
) -> None:
    """01R Decision B: there is no disposable-auto-delete carve-out, even for
    artifacts the task itself generated."""
    engine = PolicyEngine()
    decision = engine.decide(
        candidate=_contract(),
        impact=_clean_impact(),
        validation=_VALID,
        evidence_passed=evidence_passed,
        rollback_available=rollback_available,
        deletion_classification="disposable",
    )
    assert decision.outcome is PolicyOutcome.HUMAN_APPROVAL_REQUIRED
    assert "file_deletion" in decision.required_approvals


def test_security_violation_is_not_downgraded_to_a_mere_approval_by_deletion_framing() -> None:
    engine = PolicyEngine()
    validation = ValidationReport(
        valid=False,
        issues=(ValidationIssue(ErrorCode.SECURITY_DENIED, "/allowed_paths", "path traversal"),),
    )
    decision = engine.decide(
        candidate=_contract(),
        impact=_clean_impact(),
        validation=validation,
        evidence_passed=True,
        rollback_available=True,
        deletion_classification="pre_existing",
    )
    assert decision.outcome is PolicyOutcome.DENY_SECURITY_VIOLATION


def test_non_deletion_change_is_unaffected_by_deletion_gate() -> None:
    engine = PolicyEngine()
    decision = engine.decide(
        candidate=_contract(),
        impact=_clean_impact(),
        validation=_VALID,
        evidence_passed=True,
        rollback_available=True,
        deletion_classification=None,
    )
    assert decision.outcome is PolicyOutcome.ALLOW_WITH_CHECKPOINT
