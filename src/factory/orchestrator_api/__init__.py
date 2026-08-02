"""Orchestrator write-authorized API surface (Phase 3A, CMP-ORCH-API).

Holds the single authoritative writer (R1) for task submission and cancellation. Separate from
``factory.api`` (the read-only snapshot API), which never imports a writer. No approval or
promotion logic exists here yet — that's Phase 3C.
"""

from factory.orchestrator_api.app import create_app
from factory.orchestrator_api.errors import OrchestratorApiError
from factory.orchestrator_api.lifecycle import Phase3BDetail, Phase3BLifecycleService
from factory.orchestrator_api.service import TaskDetail, TaskOperatorService

__all__ = [
    "OrchestratorApiError",
    "Phase3BDetail",
    "Phase3BLifecycleService",
    "TaskDetail",
    "TaskOperatorService",
    "create_app",
]
