"""Shared builders for UI Studio tests (deterministic; no real renderer/build tool)."""

from __future__ import annotations

from factory.ui_studio.component_registry import ComponentRegistry
from factory.ui_studio.design_tokens import default_token_set
from factory.ui_studio.fake_renderer import FakeRenderer, RenderRequest
from factory.ui_studio.models import DesignTokenSet
from factory.ui_studio.requirements_compiler import (
    GenerationPlan,
    UIRequirement,
    compile_requirement,
)
from factory.ui_studio.template_registry import TemplateRegistry


def registries() -> tuple[TemplateRegistry, ComponentRegistry]:
    return TemplateRegistry(), ComponentRegistry()


def plan_for(template_id: str, *, title: str = "Test Project") -> GenerationPlan:
    templates, components = registries()
    requirement = UIRequirement(template_id=template_id, title=title)
    return compile_requirement(requirement, templates=templates, components=components)


def tokens() -> DesignTokenSet:
    return default_token_set()


def render_request(template_id: str = "builder-command-center") -> RenderRequest:
    return RenderRequest(plan_for(template_id), tokens())


def renderer(**over: object) -> FakeRenderer:
    return FakeRenderer(**over)  # type: ignore[arg-type]
