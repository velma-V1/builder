"""Value objects for the PH-5 quarantined-staging subsystem (``01E §3.7``).

Sandbox output leaves only through a quarantined staging area and is non-authoritative until it
passes the inspection gate and receives explicit promotion authorization.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class FindingKind(StrEnum):
    PATH_ESCAPE = "PATH_ESCAPE"
    SECRET = "SECRET"  # noqa: S105 - finding-kind label, not a credential
    UNEXPECTED_EXECUTABLE = "UNEXPECTED_EXECUTABLE"
    ARCHIVE_BOMB = "ARCHIVE_BOMB"
    SCOPE_VIOLATION = "SCOPE_VIOLATION"


@dataclass(frozen=True, slots=True)
class StagedFile:
    """A single sandbox-output file staged for inspection."""

    path: str
    content: bytes
    provenance: str
    declared_uncompressed_size: int = 0


@dataclass(frozen=True, slots=True)
class InspectionFinding:
    kind: FindingKind
    path: str
    detail: str


@dataclass(frozen=True, slots=True)
class FileRecord:
    """Recorded inventory entry (``01E §3.7`` steps 1/3): path, size, hash, provenance."""

    path: str
    size: int
    content_hash: str
    provenance: str


@dataclass(frozen=True, slots=True)
class InspectionResult:
    records: tuple[FileRecord, ...]
    findings: tuple[InspectionFinding, ...] = field(default_factory=tuple)

    @property
    def clean(self) -> bool:
        return not self.findings


@dataclass(frozen=True, slots=True)
class PromotionResult:
    promoted: bool
    reason: str
    staging_id: str
