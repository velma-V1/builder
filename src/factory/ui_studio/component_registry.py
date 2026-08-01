"""Component registry — unknown component is DENIED (fail closed).

Every component a template references must be discovered here first. This registry enumerates the
components UI Studio knows how to describe across the approved technology profile (shadcn/ui,
Apache ECharts, React Flow, MapLibre, deck.gl, Three.js/React Three Fiber, Monaco, Motion) — it does
not install any of them.
"""

from __future__ import annotations

from dataclasses import dataclass

from factory.ui_studio.errors import UIStudioError, UIStudioErrorCode
from factory.ui_studio.models import ComponentDescriptor

_COMPONENTS: tuple[ComponentDescriptor, ...] = (
    ComponentDescriptor("Button", "shadcn/ui", "form"),
    ComponentDescriptor("Card", "shadcn/ui", "layout"),
    ComponentDescriptor("Dialog", "shadcn/ui", "overlay"),
    ComponentDescriptor("DataTable", "shadcn/ui", "data"),
    ComponentDescriptor("Tabs", "shadcn/ui", "navigation"),
    ComponentDescriptor("Sheet", "shadcn/ui", "overlay"),
    ComponentDescriptor("Badge", "shadcn/ui", "status"),
    ComponentDescriptor("Toast", "shadcn/ui", "feedback"),
    ComponentDescriptor("CommandPalette", "shadcn/ui", "navigation"),
    ComponentDescriptor("EChartLine", "echarts", "chart", requires_props=("series", "xAxis")),
    ComponentDescriptor("EChartHeatmap", "echarts", "chart", requires_props=("matrix",)),
    ComponentDescriptor("EChartSankey", "echarts", "chart", requires_props=("nodes", "links")),
    ComponentDescriptor("FlowCanvas", "react-flow", "diagram", requires_props=("nodes", "edges")),
    ComponentDescriptor("MapView", "maplibre", "map", requires_props=("center", "zoom")),
    ComponentDescriptor("DeckOverlay", "deck.gl", "map", requires_props=("layers",)),
    ComponentDescriptor("Scene3D", "react-three-fiber", "3d", requires_props=("camera",)),
    ComponentDescriptor("Orb", "react-three-fiber", "3d", requires_props=("state",)),
    ComponentDescriptor("CodeEditor", "monaco", "editor", requires_props=("language", "value")),
    ComponentDescriptor("MotionPanel", "motion", "layout"),
    ComponentDescriptor("EventTimeline", "internal", "realtime", requires_props=("events",)),
    ComponentDescriptor("ApprovalCard", "internal", "workflow", requires_props=("evidence",)),
    ComponentDescriptor("ResourceGauge", "internal", "monitor", requires_props=("value", "limit")),
)

_BY_NAME: dict[str, ComponentDescriptor] = {c.name: c for c in _COMPONENTS}


@dataclass(frozen=True, slots=True)
class ComponentRegistry:
    components: tuple[ComponentDescriptor, ...] = _COMPONENTS

    def names(self) -> frozenset[str]:
        return frozenset(c.name for c in self.components)

    def get(self, name: str) -> ComponentDescriptor:
        found = _BY_NAME.get(name)
        if found is None:
            raise UIStudioError(UIStudioErrorCode.COMPONENT_UNKNOWN, f"unknown component {name!r}")
        return found


def require_component(registry: ComponentRegistry, name: str) -> ComponentDescriptor:
    return registry.get(name)
