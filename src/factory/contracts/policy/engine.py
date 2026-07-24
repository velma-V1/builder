from __future__ import annotations

from dataclasses import dataclass

from factory.contracts.models import (
    CanonicalContract,
    ErrorCode,
    ImpactResult,
    PolicyDecision,
    PolicyOutcome,
    ValidationReport,
)

# Deletion classifications passed by the caller (see docs/01R Decision B):
# "outside_ownership" -> a delete targeting a path the task does not own.
# "disposable"         -> a delete of an artifact the task itself created.
# "pre_existing"       -> a delete of a pre-existing source/test/schema/contract/
#                          decision/shared/user-authored file.
# None                 -> the candidate change is not a deletion.


@dataclass(frozen=True, slots=True)
class PolicyEngine:
    def decide(
        self,
        *,
        candidate: CanonicalContract,
        impact: ImpactResult,
        validation: ValidationReport,
        evidence_passed: bool,
        rollback_available: bool,
        deletion_classification: str | None,
    ) -> PolicyDecision:
        del candidate  # identity is carried in `reasons`/caller logs, not in this decision logic

        if deletion_classification == "outside_ownership":
            return PolicyDecision(
                outcome=PolicyOutcome.DENY_SECURITY_VIOLATION,
                reasons=("deletion targets a path outside the task's ownership",),
                required_approvals=(),
                required_tests=(),
            )

        security_issues = tuple(
            issue.message for issue in validation.issues if issue.code is ErrorCode.SECURITY_DENIED
        )
        if security_issues:
            return PolicyDecision(
                outcome=PolicyOutcome.DENY_SECURITY_VIOLATION,
                reasons=security_issues,
                required_approvals=(),
                required_tests=(),
            )

        if deletion_classification in ("disposable", "pre_existing"):
            reason = f"file deletion requires approval (01R Decision B): {deletion_classification}"
            return PolicyDecision(
                outcome=PolicyOutcome.HUMAN_APPROVAL_REQUIRED,
                reasons=(reason,),
                required_approvals=("file_deletion",),
                required_tests=(),
            )

        if not validation.valid:
            reasons = tuple(issue.message for issue in validation.issues) or ("validation failed",)
            return PolicyDecision(
                outcome=PolicyOutcome.HUMAN_APPROVAL_REQUIRED,
                reasons=reasons,
                required_approvals=("validation_review",),
                required_tests=(),
            )

        if impact.protected_boundary_crossed:
            return PolicyDecision(
                outcome=PolicyOutcome.HUMAN_APPROVAL_REQUIRED,
                reasons=("change crosses a protected boundary", *impact.reasons),
                required_approvals=("protected_boundary_review",),
                required_tests=impact.required_tests,
            )

        if impact.authority_expanded:
            return PolicyDecision(
                outcome=PolicyOutcome.HUMAN_APPROVAL_REQUIRED,
                reasons=("change expands authority", *impact.reasons),
                required_approvals=("authority_expansion_review",),
                required_tests=impact.required_tests,
            )

        if not impact.compatible:
            return PolicyDecision(
                outcome=PolicyOutcome.HUMAN_APPROVAL_REQUIRED,
                reasons=("change compatibility is unproven", *impact.reasons),
                required_approvals=("compatibility_review",),
                required_tests=impact.required_tests,
            )

        if not evidence_passed:
            return PolicyDecision(
                outcome=PolicyOutcome.HUMAN_APPROVAL_REQUIRED,
                reasons=("required evidence has not passed",),
                required_approvals=("evidence_review",),
                required_tests=impact.required_tests,
            )

        if impact.evidence_weakened:
            return PolicyDecision(
                outcome=PolicyOutcome.HUMAN_APPROVAL_REQUIRED,
                reasons=("change weakens evidence requirements", *impact.reasons),
                required_approvals=("evidence_weakening_review",),
                required_tests=impact.required_tests,
            )

        if impact.affected_components:
            reason = "change touches shared components; serialized integration testing required"
            return PolicyDecision(
                outcome=PolicyOutcome.SERIALIZE_AND_TEST,
                reasons=(reason,),
                required_approvals=(),
                required_tests=impact.required_tests,
            )

        if rollback_available:
            reason = "bounded owned edit with passing evidence and an available rollback target"
            return PolicyDecision(
                outcome=PolicyOutcome.ALLOW_WITH_CHECKPOINT,
                reasons=(reason,),
                required_approvals=(),
                required_tests=(),
            )

        return PolicyDecision(
            outcome=PolicyOutcome.HUMAN_APPROVAL_REQUIRED,
            reasons=("no rollback target is available for an automatic checkpoint",),
            required_approvals=("rollback_availability_review",),
            required_tests=(),
        )
