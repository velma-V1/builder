"""PH-5 (Task 5.4) — quarantined staging (preinstallation).

The only exit for sandbox output: inventory + hash + provenance, path-escape / secret / executable /
archive-bomb / scope inspection, and promotion denied without a clean gate AND explicit
authorization. Includes complete process-tree termination (``01E §3.7/§3.9``).
"""

from __future__ import annotations

from factory.staging.errors import StagingError
from factory.staging.inspection import inspect
from factory.staging.manager import QuarantinedStaging, terminate_process_tree
from factory.staging.models import (
    FileRecord,
    FindingKind,
    InspectionFinding,
    InspectionResult,
    PromotionResult,
    StagedFile,
)

__all__ = [
    "FileRecord",
    "FindingKind",
    "InspectionFinding",
    "InspectionResult",
    "PromotionResult",
    "QuarantinedStaging",
    "StagedFile",
    "StagingError",
    "inspect",
    "terminate_process_tree",
]
