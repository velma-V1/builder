"""Value objects for the PH-6 integration coordinator (``01D §3.8/§6``)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from factory.workstream.conflict.models import ChangeManifest, Conflict


class IntegrationVerdict(StrEnum):
    INTEGRATED = "INTEGRATED"
    BLOCKED_LOCAL_GATE = "BLOCKED_LOCAL_GATE"
    BLOCKED_BASELINE = "BLOCKED_BASELINE"
    BLOCKED_CONFLICTS = "BLOCKED_CONFLICTS"


@dataclass(frozen=True, slots=True)
class WorkstreamResult:
    """One workstream's verified local outcome offered to the integration gate."""

    workstream_id: str
    local_gate_passed: bool
    baseline_commit: str
    approved_commit: str
    manifest: ChangeManifest


@dataclass(frozen=True, slots=True)
class RemediationTask:
    """An evidence-backed remediation returned to a named owning lane (never a source edit)."""

    task_id: str
    owning_workstream: str
    conflict: Conflict
    description: str


@dataclass(frozen=True, slots=True)
class IntegrationReport:
    verdict: IntegrationVerdict
    promoted: tuple[str, ...] = field(default_factory=tuple)
    remediation: tuple[RemediationTask, ...] = field(default_factory=tuple)
    conflicts: tuple[Conflict, ...] = field(default_factory=tuple)
    detail: str = ""

    @property
    def integrated(self) -> bool:
        return self.verdict is IntegrationVerdict.INTEGRATED
