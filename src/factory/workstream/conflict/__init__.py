"""PH-6 (Task 6.3) — conflict detection beyond files + immutable integration baseline."""

from __future__ import annotations

from factory.workstream.conflict.baseline import BaselineTracker
from factory.workstream.conflict.detector import ConflictDetector
from factory.workstream.conflict.models import (
    ChangeManifest,
    Conflict,
    ConflictKind,
    IntegrationBaseline,
)

__all__ = [
    "BaselineTracker",
    "ChangeManifest",
    "Conflict",
    "ConflictDetector",
    "ConflictKind",
    "IntegrationBaseline",
]
