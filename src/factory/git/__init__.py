"""PH-5 (Task 5.1) — Git, branch/worktree lifecycle & verified checkpoints.

Controlled Git operations from an approved baseline with local protected-ref enforcement, force-push
denial, unexplained-change blocking, owned-path checkpoint commits, and standardized trailers
(CTR-BASELINE-MANIFEST, CTR-COMMIT-TRAILER). Operates on real repositories; the live Promotion
Service that alone may advance protected refs is PH-7 (LIVE_SANDBOX_PENDING for promotion).
"""

from __future__ import annotations

from factory.git.errors import GitError
from factory.git.manager import GitManager
from factory.git.models import (
    BaselineManifest,
    ChangeSet,
    Checkpoint,
    CommitTrailers,
    PromotionMode,
    RepoBaseline,
    VerificationStatus,
    WorktreeHandle,
)
from factory.git.trailers import (
    parse_trailers,
    render_message,
    render_trailers,
    validate_against,
)

__all__ = [
    "BaselineManifest",
    "ChangeSet",
    "Checkpoint",
    "CommitTrailers",
    "GitError",
    "GitManager",
    "PromotionMode",
    "RepoBaseline",
    "VerificationStatus",
    "WorktreeHandle",
    "parse_trailers",
    "render_message",
    "render_trailers",
    "validate_against",
]
