"""PH-4 (Task 4.2) — Aider coding-worker adapter.

Ships the deterministic preinstallation fake (:class:`FakeAiderWorker`) implementing the bounded
coding-worker contract: owned-path-enforced edits, no self-certification, no scope expansion. The
live adapter driving real Aider over Ollama is LIVE_RUNTIME_PENDING. This subpackage is deliberately
decoupled from the PH-2 Worker Execution Substrate that shares the ``factory.workers`` namespace.
"""

from __future__ import annotations

from factory.workers.aider_adapter.fake_aider import (
    FakeAiderWorker,
    ProposedEdit,
    WorkerPacket,
)

__all__ = ["FakeAiderWorker", "ProposedEdit", "WorkerPacket"]
