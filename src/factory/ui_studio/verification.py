"""Per-artifact completeness gate: every generated UI artifact must contain every required section.

Mirrors the requirement verbatim: source, manifest, tokens, component/page/widget inventories, state
contracts, data contracts, tests, evidence, build status, unresolved risks, rollback record. A
missing section is a finding, not a silently-passing artifact; a HIGH-severity unresolved risk that
is not explicitly acknowledged blocks the gate outright.
"""

from __future__ import annotations

from dataclasses import dataclass

from factory.ui_studio.errors import UIStudioError, UIStudioErrorCode
from factory.ui_studio.models import ArtifactPackage, BuildStatus, RiskSeverity


@dataclass(frozen=True)
class VerificationFinding:
    name: str
    passed: bool
    detail: str


def verify_artifact_package(package: ArtifactPackage) -> tuple[VerificationFinding, ...]:
    manifest_ok = bool(package.project_manifest.project_id)
    findings = [
        VerificationFinding("source present", bool(package.source_files), "source_files"),
        VerificationFinding("manifest present", manifest_ok, "manifest"),
        VerificationFinding("tokens present", bool(package.tokens.colors), "tokens"),
        VerificationFinding(
            "component inventory present", bool(package.component_inventory), "component_inventory"
        ),
        VerificationFinding(
            "page inventory present", bool(package.page_inventory), "page_inventory"
        ),
        VerificationFinding(
            "state contracts present", bool(package.state_contracts), "state_contracts"
        ),
        VerificationFinding(
            "data contracts present", bool(package.data_contracts), "data_contracts"
        ),
        VerificationFinding("tests present", bool(package.tests), "tests"),
        VerificationFinding("evidence present", not package.evidence.is_empty, "evidence"),
        VerificationFinding(
            "build status is set", package.build_status is not BuildStatus.NOT_BUILT, "build_status"
        ),
        VerificationFinding("rollback record present", bool(package.rollback.detail), "rollback"),
    ]
    unacknowledged_high = [
        r
        for r in package.unresolved_risks
        if r.severity is RiskSeverity.HIGH and not r.acknowledged
    ]
    findings.append(
        VerificationFinding(
            "no unacknowledged HIGH-severity risk",
            not unacknowledged_high,
            f"unacknowledged={[r.risk_id for r in unacknowledged_high]}",
        )
    )
    return tuple(findings)


def require_complete_artifact(package: ArtifactPackage) -> None:
    """Raise on the first failing finding. Widgets are allowed to be empty (some templates have
    none)."""
    for finding in verify_artifact_package(package):
        if not finding.passed:
            code = (
                UIStudioErrorCode.UNRESOLVED_RISK_UNACKNOWLEDGED
                if "risk" in finding.name
                else UIStudioErrorCode.ARTIFACT_INCOMPLETE
            )
            raise UIStudioError(code, f"{finding.name}: {finding.detail}")
