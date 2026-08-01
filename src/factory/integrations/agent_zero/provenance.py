"""Immutable provenance chain for Agent Zero-produced patches, artifacts, and evidence."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProvenanceStep:
    stage: str
    detail: str


def build_provenance(
    *, work_order_id: str, run_id: str, submitted_at: int, worker_reported_version: str = "",
) -> tuple[ProvenanceStep, ...]:
    """Build the ordered, immutable provenance chain: order → run → worker → (pending) verification.

    The chain never asserts a verification step happened — that step is appended by Builder's own
    staging/approval pipeline after inspecting the worker's output, not by this package.
    """
    steps = [
        ProvenanceStep("work_order", work_order_id),
        ProvenanceStep("run", f"run_id={run_id} submitted_at={submitted_at}"),
        ProvenanceStep(
            "worker", f"agent_zero version={worker_reported_version or 'UNKNOWN'} "
            "(a managed external worker; its output is an unverified claim until Builder inspects "
            "it)",
        ),
    ]
    return tuple(steps)
