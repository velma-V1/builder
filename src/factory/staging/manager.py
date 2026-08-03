"""Quarantined staging manager (Task 5.4, ``01E §3.7``).

The staging area is the *only* exit for sandbox output and is non-authoritative: staged content can
be promoted only after the inspection gate is clean **and** explicit authorization is supplied. The
manager also models complete process-tree termination (``01E §3.9`` / process-tree control): a root
and every descendant are terminated together.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from factory.staging.errors import StagingError
from factory.staging.inspection import inspect
from factory.staging.models import (
    InspectionResult,
    PromotionResult,
    StagedFile,
)


class QuarantinedStaging:
    """A single task's quarantined staging area with an inspection + authorization gate."""

    __slots__ = ("_approved_scope", "_files", "_project_root", "_promoted", "_staging_id")

    def __init__(self, staging_id: str, project_root: Path, approved_scope: Sequence[str]) -> None:
        self._staging_id = staging_id
        self._project_root = project_root
        self._approved_scope = tuple(approved_scope)
        self._files: list[StagedFile] = []
        self._promoted = False

    def stage(self, staged: StagedFile) -> None:
        """Deposit sandbox output into quarantine (the only permitted exit)."""
        if self._promoted:
            raise StagingError("STAGING_SEALED", "cannot stage into an already-promoted area")
        self._files.append(staged)

    def files(self) -> tuple[StagedFile, ...]:
        return tuple(self._files)

    def inspect(self, secret_values: Sequence[str] = ()) -> InspectionResult:
        return inspect(self._files, self._project_root, self._approved_scope, secret_values)

    def promote(self, *, authorized: bool, secret_values: Sequence[str] = ()) -> PromotionResult:
        """Promote staged output only when inspection is clean AND promotion is authorized."""
        result = self.inspect(secret_values)
        if not result.clean:
            codes = sorted({f.kind.value for f in result.findings})
            raise StagingError("STAGING_UNCLEAN", f"inspection findings block promotion: {codes}")
        if not authorized:
            raise StagingError(
                "PROMOTION_UNAUTHORIZED", "staged output cannot be promoted without authorization"
            )
        self._promoted = True
        return PromotionResult(
            promoted=True, reason="inspection clean + authorized", staging_id=self._staging_id
        )


def terminate_process_tree(tree: Mapping[int, Sequence[int]], root: int) -> tuple[int, ...]:
    """Return every pid terminated when killing ``root``: the root + all descendants (``§3.9``)."""
    terminated: list[int] = []
    stack = [root]
    seen: set[int] = set()
    while stack:
        pid = stack.pop()
        if pid in seen:
            continue
        seen.add(pid)
        terminated.append(pid)
        stack.extend(tree.get(pid, ()))
    return tuple(sorted(terminated))
