"""Quarantined-staging inspection gate (``01E §3.7``).

Deterministic inspection of staged sandbox output: inventory + hash + provenance, path
canonicalization with traversal/escape rejection (reusing the tested ``PathAuthority``), secret
scanning, unexpected-executable detection, archive-bomb detection, and scope comparison against the
approved task scope. Any finding makes the result non-clean and blocks promotion.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from pathlib import Path

from factory.contracts.errors import ContractError
from factory.contracts.validation.paths import PathAuthority
from factory.secret.redaction import contains_secret
from factory.staging.models import (
    FileRecord,
    FindingKind,
    InspectionFinding,
    InspectionResult,
    StagedFile,
)

_EXECUTABLE_SUFFIXES = frozenset({".sh", ".bash", ".exe", ".bat", ".cmd", ".ps1", ".com", ".scr"})
_ARCHIVE_BOMB_RATIO = 100


def _is_executable(staged: StagedFile) -> bool:
    suffix = Path(staged.path).suffix.lower()
    if suffix in _EXECUTABLE_SUFFIXES:
        return True
    return staged.content[:2] == b"#!"


def _is_archive_bomb(staged: StagedFile) -> bool:
    actual = len(staged.content)
    if staged.declared_uncompressed_size <= 0 or actual == 0:
        return False
    return staged.declared_uncompressed_size // actual >= _ARCHIVE_BOMB_RATIO


def inspect(
    staged_files: Sequence[StagedFile],
    project_root: Path,
    approved_scope: Sequence[str],
    secret_values: Sequence[str] = (),
) -> InspectionResult:
    authority = PathAuthority(project_root)
    records: list[FileRecord] = []
    findings: list[InspectionFinding] = []

    for staged in staged_files:
        records.append(
            FileRecord(
                path=staged.path,
                size=len(staged.content),
                content_hash=hashlib.sha256(staged.content).hexdigest(),
                provenance=staged.provenance,
            )
        )
        try:
            result = authority.evaluate(
                staged.path,
                operation="write",
                allowed=list(approved_scope),
                forbidden=[],
                read_only=[],
                active_exclusive_paths=[],
            )
        except ContractError as exc:  # pragma: no cover - evaluate normalizes internally
            findings.append(InspectionFinding(FindingKind.PATH_ESCAPE, staged.path, str(exc)))
            continue
        if not result.allowed:
            # A normalization failure (traversal/reserved) yields no normalized path; else in-root
            # but outside the approved task scope.
            kind = (
                FindingKind.PATH_ESCAPE
                if not result.normalized_relative
                else FindingKind.SCOPE_VIOLATION
            )
            findings.append(InspectionFinding(kind, staged.path, result.reason))
        if contains_secret(staged.content.decode("utf-8", errors="ignore"), secret_values):
            findings.append(InspectionFinding(FindingKind.SECRET, staged.path, "secret material"))
        if _is_executable(staged):
            findings.append(
                InspectionFinding(FindingKind.UNEXPECTED_EXECUTABLE, staged.path, "executable")
            )
        if _is_archive_bomb(staged):
            findings.append(
                InspectionFinding(FindingKind.ARCHIVE_BOMB, staged.path, "archive bomb")
            )

    return InspectionResult(tuple(records), tuple(findings))
