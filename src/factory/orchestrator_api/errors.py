"""Orchestrator-API error type (Phase 3A, CMP-ORCH-API)."""

from __future__ import annotations


class OrchestratorApiError(Exception):
    """Structured Phase 3A orchestrator-API failure with a stable machine-readable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
