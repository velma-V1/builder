"""Assemble the composite :class:`ArtifactPackage` every generated UI artifact must produce."""

from __future__ import annotations

from factory.ui_studio.component_registry import ComponentRegistry
from factory.ui_studio.fake_renderer import RenderResult
from factory.ui_studio.manifest import build_project_manifest
from factory.ui_studio.models import (
    ArtifactPackage,
    ComponentDescriptor,
    DataContract,
    DesignTokenSet,
    PageDescriptor,
    RealtimeChannelContract,
    RollbackRecord,
    StateContract,
    UnresolvedRisk,
    WidgetDescriptor,
)
from factory.ui_studio.requirements_compiler import GenerationPlan

#: Default rollback record for a first-ever generation (nothing to roll back to yet).
_FIRST_GENERATION_ROLLBACK = RollbackRecord(
    previous_project_manifest_ref="", rollback_available=False, detail="first generation"
)


def assemble_artifact_package(
    plan: GenerationPlan,
    tokens: DesignTokenSet,
    render_result: RenderResult,
    *,
    components: ComponentRegistry,
    project_id: str,
    created_at: int,
    state_contracts: tuple[StateContract, ...] = (),
    data_contracts: tuple[DataContract, ...] = (),
    realtime_contracts: tuple[RealtimeChannelContract, ...] = (),
    unresolved_risks: tuple[UnresolvedRisk, ...] = (),
    rollback: RollbackRecord = _FIRST_GENERATION_ROLLBACK,
) -> ArtifactPackage:
    manifest = build_project_manifest(plan, tokens, project_id=project_id, created_at=created_at)
    component_inventory = tuple(components.get(name) for name in plan.resolved_components)
    page_inventory = tuple(
        PageDescriptor(name, route=f"/{name.lower()}", components=plan.resolved_components)
        for name in plan.template.pages
    )
    widget_inventory = tuple(
        WidgetDescriptor(name, component=_widget_component(component_inventory))
        for name in plan.template.widgets
    )
    return ArtifactPackage(
        project_manifest=manifest,
        source_files=render_result.source_files,
        tokens=tokens,
        component_inventory=component_inventory,
        page_inventory=page_inventory,
        widget_inventory=widget_inventory,
        state_contracts=state_contracts,
        data_contracts=data_contracts,
        realtime_contracts=realtime_contracts,
        tests=render_result.tests,
        evidence=render_result.evidence,
        build_status=render_result.build_status,
        unresolved_risks=unresolved_risks,
        rollback=rollback,
    )


def _widget_component(component_inventory: tuple[ComponentDescriptor, ...]) -> str:
    # A widget is backed by the first registered component; falling back to empty keeps this
    # deterministic and total when a template declares no components.
    return component_inventory[0].name if component_inventory else ""
