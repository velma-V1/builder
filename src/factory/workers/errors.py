"""Worker Engine error type (PH-3, CMP-WORKER)."""

from __future__ import annotations


class WorkerEngineError(Exception):
    """Structured Worker Engine failure with a stable machine-readable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
