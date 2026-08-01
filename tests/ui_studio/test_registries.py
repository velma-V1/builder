"""Component, page, widget, and template registries — unknown reference is denied."""

from __future__ import annotations

import pytest

from factory.ui_studio.component_registry import ComponentRegistry, require_component
from factory.ui_studio.errors import UIStudioError, UIStudioErrorCode
from factory.ui_studio.models import PageDescriptor, WidgetDescriptor
from factory.ui_studio.page_widget_registry import PageRegistry, WidgetRegistry
from factory.ui_studio.template_registry import TEMPLATES, TemplateRegistry, require_template


def test_all_sixteen_templates_are_registered() -> None:
    assert len(TEMPLATES) == 16
    assert len(TemplateRegistry().ids()) == 16


def test_unknown_template_is_denied() -> None:
    with pytest.raises(UIStudioError) as excinfo:
        require_template(TemplateRegistry(), "does-not-exist")
    assert excinfo.value.code is UIStudioErrorCode.TEMPLATE_UNKNOWN


def test_every_template_required_component_is_registered() -> None:
    components = ComponentRegistry()
    for template in TEMPLATES:
        for name in template.required_components:
            components.get(name)  # must not raise


def test_unknown_component_is_denied() -> None:
    with pytest.raises(UIStudioError) as excinfo:
        require_component(ComponentRegistry(), "DoesNotExist")
    assert excinfo.value.code is UIStudioErrorCode.COMPONENT_UNKNOWN


def test_unknown_page_is_denied() -> None:
    registry = PageRegistry((PageDescriptor("Dashboard", "/dashboard"),))
    with pytest.raises(UIStudioError) as excinfo:
        registry.get("NotAPage")
    assert excinfo.value.code is UIStudioErrorCode.PAGE_UNKNOWN


def test_unknown_widget_is_denied() -> None:
    registry = WidgetRegistry((WidgetDescriptor("TaskQueueWidget", component="DataTable"),))
    with pytest.raises(UIStudioError) as excinfo:
        registry.get("NotAWidget")
    assert excinfo.value.code is UIStudioErrorCode.WIDGET_UNKNOWN


def test_page_registry_validates_its_own_components() -> None:
    components = ComponentRegistry()
    registry = PageRegistry((PageDescriptor("Dashboard", "/dashboard", components=("Button",)),))
    registry.validate_components(components)  # must not raise


def test_page_registry_rejects_undiscovered_component() -> None:
    components = ComponentRegistry()
    registry = PageRegistry(
        (PageDescriptor("Dashboard", "/dashboard", components=("NotRegistered",)),)
    )
    with pytest.raises(UIStudioError):
        registry.validate_components(components)
