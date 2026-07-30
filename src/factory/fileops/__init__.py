"""Roadmap PH-3 safe file-op service (CMP-FILEOP, RPH3-T5).

Single safe path for file operations: canonicalize + contain every path (escape classes blocked),
Decision-B approval-gated delete (Class-3 audited), atomic bounded writes, and archive-bomb/zip-slip
capped extraction. Consumes CMP-PERM / CMP-APPROVAL decisions; owns no new contract.
"""

from __future__ import annotations

from factory.fileops.errors import FileOpError
from factory.fileops.models import ArchiveLimits, DeleteResult, ExtractResult, WriteResult
from factory.fileops.service import FileOpService

__all__ = [
    "ArchiveLimits",
    "DeleteResult",
    "ExtractResult",
    "FileOpError",
    "FileOpService",
    "WriteResult",
]
