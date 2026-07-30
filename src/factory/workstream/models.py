"""Value objects for the PH-6 workstream engine (``01D``).

Encodes CTR-WORKSTREAM and the admission/independence vocabulary. Independence is proven from
contracts, dependencies, ownership, and baselines — not from path-disjointness alone (``01D §3.4``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


@dataclass(frozen=True, slots=True)
class WorkstreamContract:
    """A declared major-stage workstream (CTR-WORKSTREAM, ``01D §2.4``)."""

    workstream_id: str
    owner: str
    scope_paths: tuple[str, ...]
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    dependencies: tuple[str, ...]
    owned_contracts: tuple[str, ...]
    completion_gate: str
    baseline_commit: str


class AdmissionOutcome(StrEnum):
    ADMITTED = "ADMITTED"
    DENIED_CAP = "DENIED_CAP"
    DENIED_NOT_INDEPENDENT = "DENIED_NOT_INDEPENDENT"
    DENIED_UNSTABLE = "DENIED_UNSTABLE"


class IndependenceKind(StrEnum):
    SCOPE_OVERLAP = "SCOPE_OVERLAP"
    SHARED_CONTRACT = "SHARED_CONTRACT"
    UNRESOLVED_DEPENDENCY = "UNRESOLVED_DEPENDENCY"
    BASELINE_MISMATCH = "BASELINE_MISMATCH"


@dataclass(frozen=True, slots=True)
class IndependenceFinding:
    kind: IndependenceKind
    workstream_id: str
    detail: str


@dataclass(frozen=True, slots=True)
class AdmissionResult:
    outcome: AdmissionOutcome
    reason: str
    findings: tuple[IndependenceFinding, ...] = field(default_factory=tuple)

    @property
    def admitted(self) -> bool:
        return self.outcome is AdmissionOutcome.ADMITTED


@dataclass(frozen=True, slots=True)
class OwnershipLease:
    """A single-write-owner lease over a file path or a shared contract (``01D §2.5/§3.2``)."""

    resource_id: str
    workstream_id: str
    is_contract: bool
