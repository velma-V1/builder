"""Worker Engine (Phase 3B) error type."""

from __future__ import annotations


class WorkerEngineRunError(Exception):
    """Structured Phase 3B worker-run failure with a stable machine-readable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
