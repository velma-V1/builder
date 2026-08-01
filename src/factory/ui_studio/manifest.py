"""Project manifest — one per generated UI artifact. Never carries a guessed dependency version."""

from __future__ import annotations

from factory.ui_studio.models import DesignTokenSet, ProjectManifest, content_digest
from factory.ui_studio.requirements_compiler import GenerationPlan

COMPATIBILITY_VERSION = "0.1-ui-studio"


def build_project_manifest(
    plan: GenerationPlan, tokens: DesignTokenSet, *, project_id: str, created_at: int
) -> ProjectManifest:
    tokens_digest = content_digest(
        *sorted(f"{k}={v}" for k, v in tokens.colors.items()),
        *sorted(f"{k}={v}" for k, v in tokens.spacing.items()),
        *sorted(f"{k}={v}" for k, v in tokens.typography.items()),
        *sorted(f"{k}={v}" for k, v in tokens.radii.items()),
        *sorted(f"{k}={v}" for k, v in tokens.motion.items()),
    )
    return ProjectManifest(
        project_id=project_id,
        title=plan.requirement.title,
        template_id=plan.template.template_id,
        tokens_digest=tokens_digest,
        created_at=created_at,
        compatibility_version=COMPATIBILITY_VERSION,
    )
