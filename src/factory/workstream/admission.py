"""Independence-before-parallel admission gate (``01D §2.1-8/§3.4``).

Admission enforces the ≤3 active-workstream cap and proves *independence* — not path-disjointness
alone — before allowing parallel execution. A candidate is denied when it would exceed the cap, when
its baseline differs from the shared integration baseline, when a declared dependency is not yet
complete, when its scope overlaps an active workstream, or when it shares an owned contract.
"""

from __future__ import annotations

from collections.abc import Sequence

from factory.workstream.models import (
    AdmissionOutcome,
    AdmissionResult,
    IndependenceFinding,
    IndependenceKind,
    WorkstreamContract,
)


def _static_prefix(pattern: str) -> str:
    head = pattern.split("*", 1)[0]
    return head.rstrip("/")


def _path_prefix_overlap(a: str, b: str) -> bool:
    if a == b:
        return True
    if not a or not b:  # an unrestricted (root) scope overlaps every other scope
        return True
    shorter, longer = sorted((a, b), key=len)
    return longer.startswith(shorter + "/")


def _scopes_overlap(a: WorkstreamContract, b: WorkstreamContract) -> bool:
    a_prefixes = [_static_prefix(p) for p in a.scope_paths]
    b_prefixes = [_static_prefix(p) for p in b.scope_paths]
    return any(_path_prefix_overlap(pa, pb) for pa in a_prefixes for pb in b_prefixes)


class AdmissionController:
    """Deterministic parallel-admission gate with a configurable ≤3 cap."""

    __slots__ = ("_max_active",)

    def __init__(self, max_active: int = 3) -> None:
        self._max_active = max_active

    @property
    def max_active(self) -> int:
        return self._max_active

    def admit(
        self,
        candidate: WorkstreamContract,
        active: Sequence[WorkstreamContract],
        integration_baseline: str,
        completed: frozenset[str] = frozenset(),
    ) -> AdmissionResult:
        if len(active) >= self._max_active:
            return AdmissionResult(
                AdmissionOutcome.DENIED_CAP,
                f"active-workstream cap ({self._max_active}) reached",
            )

        findings: list[IndependenceFinding] = []
        unstable = False

        if candidate.baseline_commit != integration_baseline:
            unstable = True
            findings.append(
                IndependenceFinding(
                    IndependenceKind.BASELINE_MISMATCH,
                    candidate.workstream_id,
                    f"baseline {candidate.baseline_commit} != {integration_baseline}",
                )
            )
        for dep in candidate.dependencies:
            if dep not in completed:
                unstable = True
                findings.append(
                    IndependenceFinding(
                        IndependenceKind.UNRESOLVED_DEPENDENCY,
                        candidate.workstream_id,
                        f"dependency {dep} is not complete",
                    )
                )

        for other in active:
            if _scopes_overlap(candidate, other):
                findings.append(
                    IndependenceFinding(
                        IndependenceKind.SCOPE_OVERLAP,
                        other.workstream_id,
                        f"scope overlaps {other.workstream_id}",
                    )
                )
            shared = set(candidate.owned_contracts) & set(other.owned_contracts)
            if shared:
                findings.append(
                    IndependenceFinding(
                        IndependenceKind.SHARED_CONTRACT,
                        other.workstream_id,
                        f"shares contracts {sorted(shared)}",
                    )
                )

        if not findings:
            return AdmissionResult(AdmissionOutcome.ADMITTED, "independent; admitted")
        outcome = (
            AdmissionOutcome.DENIED_UNSTABLE
            if unstable
            else AdmissionOutcome.DENIED_NOT_INDEPENDENT
        )
        return AdmissionResult(outcome, "admission denied", tuple(findings))
