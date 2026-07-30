"""Models for the roadmap PH-3 safe file-op service (CMP-FILEOP)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WriteResult:
    canonical_path: str
    bytes_written: int


@dataclass(frozen=True, slots=True)
class DeleteResult:
    canonical_path: str
    deleted: bool


@dataclass(frozen=True, slots=True)
class ExtractResult:
    dest: str
    entries: int
    total_bytes: int


@dataclass(frozen=True, slots=True)
class ArchiveLimits:
    """Archive-bomb caps (01K-AC-11): entry count, nesting depth, total decompressed size."""

    max_entries: int
    max_depth: int
    max_total_bytes: int


__all__ = ["ArchiveLimits", "DeleteResult", "ExtractResult", "WriteResult"]
