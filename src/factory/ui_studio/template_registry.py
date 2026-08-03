"""The 16 UI Studio templates — unknown template is DENIED (fail closed).

Each :class:`TemplateDescriptor` names the pages/widgets/components it needs; the registry does not
generate anything by itself — :mod:`fake_renderer` does that, deterministically, from a descriptor.
"""

from __future__ import annotations

from dataclasses import dataclass

from factory.ui_studio.errors import UIStudioError, UIStudioErrorCode
from factory.ui_studio.models import TemplateDescriptor

TEMPLATES: tuple[TemplateDescriptor, ...] = (
    TemplateDescriptor(
        "builder-command-center",
        "Builder Command Center",
        "Task/workstream orchestration overview with live approvals.",
        pages=("Dashboard",),
        widgets=("TaskQueueWidget", "ApprovalQueueWidget"),
        required_components=(
            "DataTable",
            "Badge",
            "ApprovalCard",
            "EventTimeline",
            "CommandPalette",
        ),
        realtime=True,
    ),
    TemplateDescriptor(
        "agent-zero-workstream-board",
        "Agent Zero Workstream Board",
        "Work-order board tracking managed-worker runs and evidence.",
        pages=("WorkstreamBoard",),
        widgets=("WorkOrderCardWidget", "EvidenceWidget"),
        required_components=("DataTable", "Badge", "ApprovalCard", "EventTimeline"),
        realtime=True,
    ),
    TemplateDescriptor(
        "ai-operations-hub",
        "AI Operations Hub",
        "Model routing, quota, and execution health overview.",
        pages=("OperationsHub",),
        widgets=("ModelRouteWidget", "QuotaWidget"),
        required_components=("EChartLine", "DataTable", "Badge", "ResourceGauge"),
        realtime=True,
    ),
    TemplateDescriptor(
        "worldmonitor-workspace",
        "WorldMonitor Workspace",
        "Intelligence feed and map panel for the WorldMonitor integration.",
        pages=("WorldMonitorWorkspace",),
        widgets=("IntelligenceFeedWidget", "MapPanelWidget"),
        required_components=("MapView", "DeckOverlay", "DataTable", "EventTimeline"),
        realtime=True,
    ),
    TemplateDescriptor(
        "analytics-dashboard",
        "Analytics Dashboard",
        "KPI and trend charts over backend-sourced snapshots.",
        pages=("AnalyticsDashboard",),
        widgets=("KpiWidget", "TrendWidget"),
        required_components=("EChartLine", "EChartHeatmap", "Card"),
    ),
    TemplateDescriptor(
        "repository-intelligence",
        "Repository Intelligence",
        "Dependency graph and hotspot analysis over a repository snapshot.",
        pages=("RepositoryIntelligence",),
        widgets=("DependencyGraphWidget", "HotspotWidget"),
        required_components=("FlowCanvas", "EChartHeatmap", "DataTable"),
    ),
    TemplateDescriptor(
        "system-architecture-canvas",
        "System Architecture Canvas",
        "Interactive service/dependency diagram.",
        pages=("ArchitectureCanvas",),
        widgets=("ServiceNodeWidget",),
        required_components=("FlowCanvas", "Dialog", "Badge"),
    ),
    TemplateDescriptor(
        "resource-monitor",
        "Resource Monitor",
        "Live CPU/memory/disk gauges over a bounded resource snapshot stream.",
        pages=("ResourceMonitor",),
        widgets=("CpuGaugeWidget", "MemoryGaugeWidget"),
        required_components=("ResourceGauge", "EChartLine"),
        realtime=True,
    ),
    TemplateDescriptor(
        "approval-evidence-console",
        "Approval / Evidence Console",
        "Operator console for reviewing evidence and approval decisions.",
        pages=("ApprovalConsole",),
        widgets=("ApprovalQueueWidget", "EvidenceWidget"),
        required_components=("ApprovalCard", "DataTable", "Dialog"),
        realtime=True,
    ),
    TemplateDescriptor(
        "map-intelligence-center",
        "Map Intelligence Center",
        "Layered map intelligence view.",
        pages=("MapIntelligenceCenter",),
        widgets=("MapLayerWidget",),
        required_components=("MapView", "DeckOverlay", "Sheet"),
        realtime=True,
    ),
    TemplateDescriptor(
        "3d-orb-interface",
        "3D Orb Interface",
        "A 3D ambient status orb reflecting live system state.",
        pages=("OrbInterface",),
        widgets=("OrbStateWidget",),
        required_components=("Orb", "Scene3D", "MotionPanel"),
        realtime=True,
    ),
    TemplateDescriptor(
        "admin-dashboard",
        "Admin Dashboard",
        "User/permission administration surface.",
        pages=("AdminDashboard",),
        widgets=("UserTableWidget", "PermissionWidget"),
        required_components=("DataTable", "Dialog", "Badge"),
    ),
    TemplateDescriptor(
        "saas-shell",
        "SaaS Shell",
        "Billing/onboarding shell for a multi-tenant product.",
        pages=("SaasShell",),
        widgets=("BillingWidget", "OnboardingWidget"),
        required_components=("Card", "Tabs", "Toast"),
    ),
    TemplateDescriptor(
        "product-landing-page",
        "Product Landing Page",
        "A static marketing landing page.",
        pages=("LandingPage",),
        widgets=(),
        required_components=("Card", "MotionPanel", "Button"),
    ),
    TemplateDescriptor(
        "portfolio-showcase",
        "Portfolio / Showcase",
        "A static portfolio/showcase page.",
        pages=("Showcase",),
        widgets=(),
        required_components=("Card", "MotionPanel"),
    ),
    TemplateDescriptor(
        "custom-realtime-interface",
        "Custom Real-Time Interface",
        "A minimal scaffold for a bespoke real-time interface.",
        pages=("CustomRealtime",),
        widgets=("CustomEventWidget",),
        required_components=("EventTimeline", "DataTable"),
        realtime=True,
    ),
)

_BY_ID: dict[str, TemplateDescriptor] = {t.template_id: t for t in TEMPLATES}


@dataclass(frozen=True, slots=True)
class TemplateRegistry:
    templates: tuple[TemplateDescriptor, ...] = TEMPLATES

    def ids(self) -> frozenset[str]:
        return frozenset(t.template_id for t in self.templates)

    def get(self, template_id: str) -> TemplateDescriptor:
        found = _BY_ID.get(template_id)
        if found is None:
            raise UIStudioError(
                UIStudioErrorCode.TEMPLATE_UNKNOWN, f"unknown template {template_id!r}"
            )
        return found


def require_template(registry: TemplateRegistry, template_id: str) -> TemplateDescriptor:
    return registry.get(template_id)
