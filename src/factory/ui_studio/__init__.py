"""UI Studio — deterministic UI generation engine (STRUCTURE_COMPLETE_NOT_INSTALLED).

Compiles a structured requirement into a generation plan (template + registries: components, pages,
widgets), renders it through a **deterministic fake renderer** (no build tool is ever invoked, no
frontend package is installed, no preview server starts), and assembles a complete, verifiable
:class:`ArtifactPackage` — source, manifest, tokens, inventories, state/data/real-time contracts,
tests, evidence, build status, unresolved risks, and a rollback record.

State ownership is typed and enforced, not just documented: XState owns workflows/legal
transitions, TanStack Query owns backend snapshots, Zustand owns presentation-only state, and only
the backend may claim authoritative truth (:mod:`state_contracts`, :mod:`data_contracts`). The
real-time layer (:mod:`realtime_contracts`) is contract-complete — monotonic sequencing, idempotent
duplicates, out-of-order rejection, gap detection, bounded replay, reconnect cursors, snapshot
reconciliation, staleness, pending optimistic commands, and restart reconstruction — with no
connection ever opened. Nothing here connects, installs, or activates anything.
"""

from __future__ import annotations

from factory.ui_studio.artifact_package import assemble_artifact_package
from factory.ui_studio.component_registry import ComponentRegistry, require_component
from factory.ui_studio.data_contracts import (
    builder_task_snapshot_contract,
    sidebar_presentation_contract,
    validate_data_contract,
)
from factory.ui_studio.design_tokens import (
    MIN_CONTRAST_RATIO,
    contrast_ratio,
    default_token_set,
    relative_luminance,
    validate_token_set,
)
from factory.ui_studio.errors import UIStudioError, UIStudioErrorCode
from factory.ui_studio.fake_renderer import (
    FakeRenderer,
    RenderFailure,
    RenderRequest,
    RenderResult,
    RenderTimeout,
)
from factory.ui_studio.manifest import COMPATIBILITY_VERSION, build_project_manifest
from factory.ui_studio.models import (
    ArtifactPackage,
    BuildStatus,
    ComponentDescriptor,
    DataContract,
    DesignTokenSet,
    EvidenceBundle,
    EvidenceItem,
    PageDescriptor,
    PreviewState,
    ProjectManifest,
    RealtimeChannelContract,
    RiskSeverity,
    RollbackRecord,
    SourceFileRef,
    StateContract,
    StateOwner,
    TemplateDescriptor,
    TestInventoryItem,
    UnresolvedRisk,
    WidgetDescriptor,
    content_digest,
)
from factory.ui_studio.page_widget_registry import (
    PageRegistry,
    WidgetRegistry,
    require_page,
    require_widget,
)
from factory.ui_studio.preview_lifecycle import (
    PreviewSession,
    build_preview_lifecycle,
    transition,
)
from factory.ui_studio.realtime_contracts import (
    OptimisticCommand,
    RealtimeEvent,
    ReconnectCursor,
    ReplayBuffer,
    RestartReconstructionPlan,
    SnapshotReconciliationResult,
    StaleIndicator,
    ValidatedRealtimeStream,
    compute_staleness,
    deny_client_invented_state,
    issue_reconnect_cursor,
    plan_restart_reconstruction,
    reconcile_snapshot,
    validate_realtime_stream,
)
from factory.ui_studio.requirements_compiler import (
    GenerationPlan,
    UIRequirement,
    compile_requirement,
)
from factory.ui_studio.state_contracts import (
    builder_command_center_workflow,
    is_transition_legal,
    validate_state_contract,
)
from factory.ui_studio.template_registry import TEMPLATES, TemplateRegistry, require_template
from factory.ui_studio.verification import (
    VerificationFinding,
    require_complete_artifact,
    verify_artifact_package,
)

__all__ = [
    "COMPATIBILITY_VERSION",
    "MIN_CONTRAST_RATIO",
    "TEMPLATES",
    "ArtifactPackage",
    "BuildStatus",
    "ComponentDescriptor",
    "ComponentRegistry",
    "DataContract",
    "DesignTokenSet",
    "EvidenceBundle",
    "EvidenceItem",
    "FakeRenderer",
    "GenerationPlan",
    "OptimisticCommand",
    "PageDescriptor",
    "PageRegistry",
    "PreviewSession",
    "PreviewState",
    "ProjectManifest",
    "RealtimeChannelContract",
    "RealtimeEvent",
    "ReconnectCursor",
    "RenderFailure",
    "RenderRequest",
    "RenderResult",
    "RenderTimeout",
    "ReplayBuffer",
    "RestartReconstructionPlan",
    "RiskSeverity",
    "RollbackRecord",
    "SnapshotReconciliationResult",
    "SourceFileRef",
    "StaleIndicator",
    "StateContract",
    "StateOwner",
    "TemplateDescriptor",
    "TemplateRegistry",
    "TestInventoryItem",
    "UIRequirement",
    "UIStudioError",
    "UIStudioErrorCode",
    "UnresolvedRisk",
    "ValidatedRealtimeStream",
    "VerificationFinding",
    "WidgetDescriptor",
    "WidgetRegistry",
    "assemble_artifact_package",
    "build_preview_lifecycle",
    "build_project_manifest",
    "builder_command_center_workflow",
    "builder_task_snapshot_contract",
    "compile_requirement",
    "compute_staleness",
    "content_digest",
    "contrast_ratio",
    "default_token_set",
    "deny_client_invented_state",
    "is_transition_legal",
    "issue_reconnect_cursor",
    "plan_restart_reconstruction",
    "reconcile_snapshot",
    "relative_luminance",
    "require_complete_artifact",
    "require_component",
    "require_page",
    "require_template",
    "require_widget",
    "sidebar_presentation_contract",
    "transition",
    "validate_data_contract",
    "validate_realtime_stream",
    "validate_state_contract",
    "validate_token_set",
    "verify_artifact_package",
]
