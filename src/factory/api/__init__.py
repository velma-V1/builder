"""Read-only HTTP API surface (Phase 2B, CMP-API) — currently one route: task snapshots."""

from factory.api.app import create_app
from factory.api.mapping import TaskSnapshot, to_task_snapshot

__all__ = ["TaskSnapshot", "create_app", "to_task_snapshot"]
