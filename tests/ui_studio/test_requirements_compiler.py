"""Requirements compiler: resolves a known template + components, denies unknowns."""

from __future__ import annotations

import pytest
from us_support import registries

from factory.ui_studio.errors import UIStudioError, UIStudioErrorCode
from factory.ui_studio.requirements_compiler import UIRequirement, compile_requirement


def test_compiles_a_known_template() -> None:
    templates, components = registries()
    plan = compile_requirement(
        UIRequirement(template_id="analytics-dashboard", title="My Dashboard"),
        templates=templates,
        components=components,
    )
    assert plan.template.template_id == "analytics-dashboard"
    assert "EChartLine" in plan.resolved_components


def test_unknown_template_is_denied() -> None:
    templates, components = registries()
    with pytest.raises(UIStudioError) as excinfo:
        compile_requirement(
            UIRequirement(template_id="not-a-template", title="X"),
            templates=templates,
            components=components,
        )
    assert excinfo.value.code is UIStudioErrorCode.TEMPLATE_UNKNOWN


def test_empty_title_is_denied() -> None:
    templates, components = registries()
    with pytest.raises(UIStudioError) as excinfo:
        compile_requirement(
            UIRequirement(template_id="analytics-dashboard", title="   "),
            templates=templates,
            components=components,
        )
    assert excinfo.value.code is UIStudioErrorCode.REQUIREMENT_UNPARSEABLE


def test_unknown_extra_component_is_denied() -> None:
    templates, components = registries()
    with pytest.raises(UIStudioError) as excinfo:
        compile_requirement(
            UIRequirement(template_id="analytics-dashboard", title="X", extra_components=("Nope",)),
            templates=templates,
            components=components,
        )
    assert excinfo.value.code is UIStudioErrorCode.COMPONENT_UNKNOWN


def test_extra_components_are_deduplicated_against_required() -> None:
    templates, components = registries()
    plan = compile_requirement(
        UIRequirement(
            template_id="analytics-dashboard",
            title="X",
            extra_components=("EChartLine", "Card"),
        ),
        templates=templates,
        components=components,
    )
    assert plan.resolved_components.count("EChartLine") == 1
