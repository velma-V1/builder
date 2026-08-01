"""Page and widget registries — unknown page/widget is DENIED (fail closed)."""

from __future__ import annotations

from dataclasses import dataclass

from factory.ui_studio.component_registry import ComponentRegistry
from factory.ui_studio.errors import UIStudioError, UIStudioErrorCode
from factory.ui_studio.models import PageDescriptor, WidgetDescriptor


@dataclass(frozen=True, slots=True)
class PageRegistry:
    pages: tuple[PageDescriptor, ...] = ()

    def get(self, name: str) -> PageDescriptor:
        for page in self.pages:
            if page.name == name:
                return page
        raise UIStudioError(UIStudioErrorCode.PAGE_UNKNOWN, f"unknown page {name!r}")

    def validate_components(self, components: ComponentRegistry) -> None:
        for page in self.pages:
            for component_name in page.components:
                components.get(component_name)


@dataclass(frozen=True, slots=True)
class WidgetRegistry:
    widgets: tuple[WidgetDescriptor, ...] = ()

    def get(self, name: str) -> WidgetDescriptor:
        for widget in self.widgets:
            if widget.name == name:
                return widget
        raise UIStudioError(UIStudioErrorCode.WIDGET_UNKNOWN, f"unknown widget {name!r}")

    def validate_components(self, components: ComponentRegistry) -> None:
        for widget in self.widgets:
            components.get(widget.component)


def require_page(registry: PageRegistry, name: str) -> PageDescriptor:
    return registry.get(name)


def require_widget(registry: WidgetRegistry, name: str) -> WidgetDescriptor:
    return registry.get(name)
