from pathlib import Path

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


def _impact(**overrides: object) -> ImpactResult:
    defaults: dict[str, object] = {
        "compatible": True,
        "ownership_conflicts": (),
        "affected_components": (),
        "required_tests": (),
        "authority_expanded": False,
        "evidence_weakened": False,
        "protected_boundary_crossed": False,
        "reasons": (),
    }
    defaults.update(overrides)
    return ImpactResult(**defaults)  # type: ignore[arg-type]


def test_bounded_owned_edit_with_passing_tests_and_rollback_allows_with_checkpoint() -> None:
    engine = PolicyEngine()
    decision = engine.decide(
        candidate=_contract(),
        impact=_impact(),
        validation=_VALID,
        evidence_passed=True,
        rollback_available=True,
        deletion_classification=None,
    )
    assert decision.outcome is PolicyOutcome.ALLOW_WITH_CHECKPOINT


def test_compatible_shared_interface_requires_serialize_and_test() -> None:
    engine = PolicyEngine()
    decision = engine.decide(
        candidate=_contract(),
        impact=_impact(affected_components=("OWN-002",), required_tests=("integration",)),
        validation=_VALID,
        evidence_passed=True,
        rollback_available=True,
        deletion_classification=None,
    )
    assert decision.outcome is PolicyOutcome.SERIALIZE_AND_TEST
    assert decision.required_tests == ("integration",)


def test_ambiguous_compatibility_requires_human_approval() -> None:
    engine = PolicyEngine()
    decision = engine.decide(
        candidate=_contract(),
        impact=_impact(compatible=False, reasons=("IMPACT_UNPROVEN: interfaces removed",)),
        validation=_VALID,
        evidence_passed=True,
        rollback_available=True,
        deletion_classification=None,
    )
    assert decision.outcome is PolicyOutcome.HUMAN_APPROVAL_REQUIRED


def test_authority_expansion_requires_human_approval() -> None:
    engine = PolicyEngine()
    decision = engine.decide(
        candidate=_contract(),
        impact=_impact(authority_expanded=True, reasons=("authority expanded: cloud became true",)),
        validation=_VALID,
        evidence_passed=True,
        rollback_available=True,
        deletion_classification=None,
    )
    assert decision.outcome is PolicyOutcome.HUMAN_APPROVAL_REQUIRED


def test_protected_boundary_crossed_requires_human_approval() -> None:
    engine = PolicyEngine()
    decision = engine.decide(
        candidate=_contract(),
        impact=_impact(protected_boundary_crossed=True),
        validation=_VALID,
        evidence_passed=True,
        rollback_available=True,
        deletion_classification=None,
    )
    assert decision.outcome is PolicyOutcome.HUMAN_APPROVAL_REQUIRED


def test_security_violation_denies() -> None:
    engine = PolicyEngine()
    validation = ValidationReport(
        valid=False,
        issues=(ValidationIssue(ErrorCode.SECURITY_DENIED, "/allowed_paths", "path escapes root"),),
    )
    decision = engine.decide(
        candidate=_contract(),
        impact=_impact(),
        validation=validation,
        evidence_passed=True,
        rollback_available=True,
        deletion_classification=None,
    )
    assert decision.outcome is PolicyOutcome.DENY_SECURITY_VIOLATION


def test_deletion_of_disposable_artifact_requires_approval() -> None:
    engine = PolicyEngine()
    decision = engine.decide(
        candidate=_contract(),
        impact=_impact(),
        validation=_VALID,
        evidence_passed=True,
        rollback_available=True,
        deletion_classification="disposable",
    )
    assert decision.outcome is PolicyOutcome.HUMAN_APPROVAL_REQUIRED
    assert "file_deletion" in decision.required_approvals


def test_deletion_of_pre_existing_file_requires_approval() -> None:
    engine = PolicyEngine()
    decision = engine.decide(
        candidate=_contract(),
        impact=_impact(),
        validation=_VALID,
        evidence_passed=True,
        rollback_available=True,
        deletion_classification="pre_existing",
    )
    assert decision.outcome is PolicyOutcome.HUMAN_APPROVAL_REQUIRED


def test_deletion_outside_ownership_denies() -> None:
    engine = PolicyEngine()
    decision = engine.decide(
        candidate=_contract(),
        impact=_impact(),
        validation=_VALID,
        evidence_passed=True,
        rollback_available=True,
        deletion_classification="outside_ownership",
    )
    assert decision.outcome is PolicyOutcome.DENY_SECURITY_VIOLATION


def test_evidence_not_yet_passed_requires_human_approval() -> None:
    engine = PolicyEngine()
    decision = engine.decide(
        candidate=_contract(),
        impact=_impact(),
        validation=_VALID,
        evidence_passed=False,
        rollback_available=True,
        deletion_classification=None,
    )
    assert decision.outcome is PolicyOutcome.HUMAN_APPROVAL_REQUIRED


def test_evidence_weakening_requires_human_approval() -> None:
    engine = PolicyEngine()
    decision = engine.decide(
        candidate=_contract(),
        impact=_impact(evidence_weakened=True, reasons=("evidence weakened: test_commands lost",)),
        validation=_VALID,
        evidence_passed=True,
        rollback_available=True,
        deletion_classification=None,
    )
    assert decision.outcome is PolicyOutcome.HUMAN_APPROVAL_REQUIRED


def test_missing_rollback_target_requires_human_approval() -> None:
    engine = PolicyEngine()
    decision = engine.decide(
        candidate=_contract(),
        impact=_impact(),
        validation=_VALID,
        evidence_passed=True,
        rollback_available=False,
        deletion_classification=None,
    )
    assert decision.outcome is PolicyOutcome.HUMAN_APPROVAL_REQUIRED


def test_security_violation_takes_precedence_over_deletion_approval() -> None:
    engine = PolicyEngine()
    validation = ValidationReport(
        valid=False,
        issues=(ValidationIssue(ErrorCode.SECURITY_DENIED, "/path", "traversal detected"),),
    )
    decision = engine.decide(
        candidate=_contract(),
        impact=_impact(),
        validation=validation,
        evidence_passed=True,
        rollback_available=True,
        deletion_classification="pre_existing",
    )
    assert decision.outcome is PolicyOutcome.DENY_SECURITY_VIOLATION
