"""End-to-end artifact assembly for all 16 templates + the per-artifact completeness gate."""

from __future__ import annotations

import dataclasses

import pytest

from factory.ui_studio.artifact_package import assemble_artifact_package
from factory.ui_studio.component_registry import ComponentRegistry
from factory.ui_studio.data_contracts import builder_task_snapshot_contract
from factory.ui_studio.design_tokens import default_token_set
from factory.ui_studio.errors import UIStudioError, UIStudioErrorCode
from factory.ui_studio.fake_renderer import FakeRenderer, RenderRequest
from factory.ui_studio.models import (
    ArtifactPackage,
    BuildStatus,
    RealtimeChannelContract,
    RiskSeverity,
    RollbackRecord,
    UnresolvedRisk,
)
from factory.ui_studio.requirements_compiler import UIRequirement, compile_requirement
from factory.ui_studio.state_contracts import builder_command_center_workflow
from factory.ui_studio.template_registry import TEMPLATES, TemplateRegistry
from factory.ui_studio.verification import require_complete_artifact, verify_artifact_package


def _package_for(template_id: str) -> ArtifactPackage:
    templates, components = TemplateRegistry(), ComponentRegistry()
    plan = compile_requirement(
        UIRequirement(template_id=template_id, title="Test Project"),
        templates=templates, components=components,
    )
    tokens = default_token_set()
    render_result = FakeRenderer().render(RenderRequest(plan, tokens))
    return assemble_artifact_package(
        plan, tokens, render_result, components=components, project_id="proj-1", created_at=1000,
        state_contracts=(builder_command_center_workflow(),),
        data_contracts=(builder_task_snapshot_contract(),),
        realtime_contracts=(
            (RealtimeChannelContract(template_id, event_types=("PROGRESS",)),)
            if plan.template.realtime else ()
        ),
    )


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda t: t.template_id)
def test_every_template_produces_a_complete_artifact(template) -> None:  # type: ignore[no-untyped-def]
    package = _package_for(template.template_id)
    require_complete_artifact(package)  # must not raise
    assert package.build_status is BuildStatus.DRY_RUN_OK


def test_artifact_carries_source_manifest_tokens_and_every_inventory() -> None:
    package = _package_for("builder-command-center")
    assert package.source_files
    assert package.project_manifest.project_id == "proj-1"
    assert package.tokens.colors
    assert package.component_inventory
    assert package.page_inventory
    assert package.state_contracts
    assert package.data_contracts
    assert package.tests
    assert not package.evidence.is_empty
    assert package.rollback.detail


def test_missing_state_contracts_fails_verification() -> None:
    package = _package_for("builder-command-center")
    incomplete = dataclasses.replace(package, state_contracts=())
    findings = verify_artifact_package(incomplete)
    failed = {f.name for f in findings if not f.passed}
    assert "state contracts present" in failed
    with pytest.raises(UIStudioError) as excinfo:
        require_complete_artifact(incomplete)
    assert excinfo.value.code is UIStudioErrorCode.ARTIFACT_INCOMPLETE


def test_unacknowledged_high_severity_risk_blocks_the_gate() -> None:
    package = _package_for("builder-command-center")
    risky = dataclasses.replace(
        package,
        unresolved_risks=(
            UnresolvedRisk("R1", RiskSeverity.HIGH, "unvetted dependency", acknowledged=False),
        ),
    )
    with pytest.raises(UIStudioError) as excinfo:
        require_complete_artifact(risky)
    assert excinfo.value.code is UIStudioErrorCode.UNRESOLVED_RISK_UNACKNOWLEDGED


def test_acknowledged_high_severity_risk_does_not_block_the_gate() -> None:
    package = _package_for("builder-command-center")
    risky = dataclasses.replace(
        package,
        unresolved_risks=(
            UnresolvedRisk("R1", RiskSeverity.HIGH, "unvetted dependency", acknowledged=True),
        ),
    )
    require_complete_artifact(risky)  # must not raise


def test_low_severity_unacknowledged_risk_does_not_block_the_gate() -> None:
    package = _package_for("builder-command-center")
    risky = dataclasses.replace(
        package,
        unresolved_risks=(
            UnresolvedRisk("R1", RiskSeverity.LOW, "minor styling nit", acknowledged=False),
        ),
    )
    require_complete_artifact(risky)  # must not raise


def test_rollback_record_reflects_no_prior_generation_by_default() -> None:
    package = _package_for("builder-command-center")
    assert not package.rollback.rollback_available


def test_rollback_record_can_reference_a_prior_manifest() -> None:
    package = _package_for("builder-command-center")
    rolled = dataclasses.replace(
        package,
        rollback=RollbackRecord(
            previous_project_manifest_ref="proj-0", rollback_available=True,
            detail="reverted to proj-0 after a failed render",
        ),
    )
    require_complete_artifact(rolled)  # must not raise
    assert rolled.rollback.rollback_available
