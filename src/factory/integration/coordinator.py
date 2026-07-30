"""Integration coordinator (``01D §3.8``).

The coordinator compares baselines and manifests, validates that each workstream passed its local
gate, detects conflicts, combines already-approved commits, and — on failure — produces
evidence-backed remediation tasks assigned to named owning lanes. It **never edits source, resolves
conflicts by writing code, changes tests, or weakens contracts**: that invariant is structural — the
class exposes no write/edit method, only compare/validate/assign operations.
"""

from __future__ import annotations

from collections.abc import Sequence

from factory.integration.models import (
    IntegrationReport,
    IntegrationVerdict,
    RemediationTask,
    WorkstreamResult,
)
from factory.workstream.conflict.detector import ConflictDetector

#: Explicit, test-checkable declaration: the integration gate is not a source-writing component.
COORDINATOR_EDITS_SOURCE = False


class IntegrationCoordinator:
    """Read-only integration gate: compare, validate, combine commits, assign remediation."""

    __slots__ = ("_detector", "_seq")

    def __init__(self, detector: ConflictDetector | None = None) -> None:
        self._detector = detector if detector is not None else ConflictDetector()
        self._seq = 0

    def integrate(self, results: Sequence[WorkstreamResult]) -> IntegrationReport:
        # (1) Every participating workstream must pass its own local verification first (§6.18).
        failed_local = [r.workstream_id for r in results if not r.local_gate_passed]
        if failed_local:
            return IntegrationReport(
                IntegrationVerdict.BLOCKED_LOCAL_GATE,
                detail=f"local gate not passed: {sorted(failed_local)}",
            )

        # (2) All participants must share one immutable integration baseline (§3.3).
        baselines = {r.baseline_commit for r in results}
        if len(baselines) > 1:
            return IntegrationReport(
                IntegrationVerdict.BLOCKED_BASELINE,
                detail=f"divergent baselines: {sorted(baselines)}",
            )

        # (3) Conflicts beyond files block integration and produce remediation (§3.4/§6.20).
        conflicts = self._detector.detect([r.manifest for r in results])
        if conflicts:
            remediation = tuple(
                RemediationTask(
                    task_id=self._next_task_id(),
                    owning_workstream=c.left,  # named probable owner; the gate never edits source
                    conflict=c,
                    description=f"resolve {c.kind.value} conflict with {c.right}: {c.detail}",
                )
                for c in conflicts
            )
            return IntegrationReport(
                IntegrationVerdict.BLOCKED_CONFLICTS, remediation=remediation, conflicts=conflicts,
                detail="conflicts detected before integration",
            )

        # (4) Clean: combine already-approved commits (simulated Promotion/Integration Service).
        promoted = tuple(sorted(r.workstream_id for r in results))
        return IntegrationReport(
            IntegrationVerdict.INTEGRATED, promoted=promoted,
            detail="baselines consistent; no conflicts; local gates passed",
        )

    def _next_task_id(self) -> str:
        self._seq += 1
        return f"remediate-{self._seq}"
