"""Requirements compiler: turns a structured requirement into a deterministic generation plan.

Pure and total for a known template: given a template id and optional token/component overrides, it
resolves every referenced page/widget/component through the registries (unknown → denied) and
produces a :class:`GenerationPlan`. It never invents a template, a component, or a page.
"""

from __future__ import annotations

from dataclasses import dataclass

from factory.ui_studio.component_registry import ComponentRegistry
from factory.ui_studio.errors import UIStudioError, UIStudioErrorCode
from factory.ui_studio.models import DesignTokenSet, TemplateDescriptor
from factory.ui_studio.template_registry import TemplateRegistry


@dataclass(frozen=True, slots=True)
class UIRequirement:
    template_id: str
    title: str
    tokens: DesignTokenSet | None = None
    extra_components: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class GenerationPlan:
    requirement: UIRequirement
    template: TemplateDescriptor
    resolved_components: tuple[str, ...]


def compile_requirement(
    requirement: UIRequirement,
    *,
    templates: TemplateRegistry,
    components: ComponentRegistry,
) -> GenerationPlan:
    if not requirement.title.strip():
        raise UIStudioError(UIStudioErrorCode.REQUIREMENT_UNPARSEABLE, "title must not be empty")
    template = templates.get(requirement.template_id)
    resolved = tuple(
        dict.fromkeys((*template.required_components, *requirement.extra_components))
    )
    for name in resolved:
        components.get(name)
    return GenerationPlan(requirement, template, resolved)
