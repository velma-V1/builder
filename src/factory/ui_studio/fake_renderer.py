"""Deterministic fake renderer — no real build tool is ever invoked here.

Given a :class:`~factory.ui_studio.requirements_compiler.GenerationPlan` and a token set, produces a
content-addressed source-file inventory, a test inventory across the four frontend test tools
(Vitest, Testing Library, Playwright, axe-core), and evidence — deterministically, offline. Failure
and timeout are scripted per template id, exactly like
:class:`~factory.integrations.agent_zero.fake_transport.FakeAgentZeroTransport`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from factory.ui_studio.models import (
    BuildStatus,
    DesignTokenSet,
    EvidenceBundle,
    EvidenceItem,
    SourceFileRef,
    TestInventoryItem,
    content_digest,
)
from factory.ui_studio.requirements_compiler import GenerationPlan


class RenderTimeout(Exception):
    """The fake renderer was scripted to time out — maps to RENDER_TIMED_OUT."""


class RenderFailure(Exception):
    """The fake renderer was scripted to fail — maps to RENDER_FAILED."""


@dataclass(frozen=True, slots=True)
class RenderRequest:
    plan: GenerationPlan
    tokens: DesignTokenSet


@dataclass(frozen=True, slots=True)
class RenderResult:
    source_files: tuple[SourceFileRef, ...]
    tests: tuple[TestInventoryItem, ...]
    evidence: EvidenceBundle
    build_status: BuildStatus
    detail: str = ""


def _tokens_digest(tokens: DesignTokenSet) -> str:
    return content_digest(
        *sorted(f"{k}={v}" for k, v in tokens.colors.items()),
        *sorted(f"{k}={v}" for k, v in tokens.spacing.items()),
    )


@dataclass(slots=True)
class FakeRenderer:
    """Deterministic, offline renderer. Scripted failure/timeout by template id."""

    fail_template_ids: frozenset[str] = field(default_factory=frozenset)
    timeout_template_ids: frozenset[str] = field(default_factory=frozenset)

    def render(self, request: RenderRequest) -> RenderResult:
        template = request.plan.template
        if template.template_id in self.timeout_template_ids:
            raise RenderTimeout(f"render timed out for template {template.template_id!r}")
        if template.template_id in self.fail_template_ids:
            raise RenderFailure(f"render failed for template {template.template_id!r}")

        source_files = (
            tuple(
                SourceFileRef(
                    path=f"ui/src/pages/{page}.tsx",
                    content_digest=content_digest(template.template_id, "page", page),
                    purpose="page",
                )
                for page in template.pages
            )
            + tuple(
                SourceFileRef(
                    path=f"ui/src/widgets/{widget}.tsx",
                    content_digest=content_digest(template.template_id, "widget", widget),
                    purpose="widget",
                )
                for widget in template.widgets
            )
            + (
                SourceFileRef(
                    path=f"ui/src/tokens/{template.template_id}.tokens.json",
                    content_digest=_tokens_digest(request.tokens),
                    purpose="tokens",
                ),
            )
        )

        tests = (
            tuple(
                TestInventoryItem("vitest", f"{page}.test.tsx", covers=page)
                for page in template.pages
            )
            + tuple(
                TestInventoryItem("testing-library", f"{widget}.render.test.tsx", covers=widget)
                for widget in template.widgets
            )
            + (
                TestInventoryItem(
                    "playwright", f"{template.template_id}.e2e.spec.ts", covers=template.template_id
                ),
                TestInventoryItem(
                    "axe-core", f"{template.template_id}.a11y.spec.ts", covers=template.template_id
                ),
            )
        )

        evidence = EvidenceBundle(
            (
                EvidenceItem(
                    "render_plan",
                    f"deterministic fake render produced {len(source_files)} source file(s) and "
                    f"{len(tests)} test(s) for template {template.template_id!r}; no build tool "
                    "invoked",
                ),
            )
        )
        return RenderResult(source_files, tests, evidence, BuildStatus.DRY_RUN_OK)
