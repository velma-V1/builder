"""Shared value types for Stage-3 live-gate *preparation*.

These types describe **read-only readiness findings** and **acceptance criteria**. Nothing in this
package installs, starts, or configures anything: a :class:`ReadinessCheck` is a *record of an
observation*, and a :class:`ReadinessReport` is a redaction-safe roll-up of such observations. The
distinction between a *blocking* gate and an *advisory* one is explicit so a single failed mandatory
gate (e.g. the SQLite engine floor) deterministically fails the whole readiness roll-up.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class CheckStatus(StrEnum):
    """Outcome of a single read-only readiness observation."""

    PASS = "PASS"  # noqa: S105 - status enum value, not a credential
    FAIL = "FAIL"
    #: The probed component is absent / not running. For a *mandatory* check this is a blocker;
    #: for an advisory check it is informational (the operator installs it during live integration).
    UNAVAILABLE = "UNAVAILABLE"
    #: Not evaluated on this host (e.g. a Windows-only probe on the Linux builder container).
    SKIPPED = "SKIPPED"
    #: The probe itself could not be executed (unexpected error); never silently treated as PASS.
    ERROR = "ERROR"


@dataclass(frozen=True, slots=True)
class ReadinessCheck:
    """A single read-only finding. ``mandatory`` gates must be ``PASS`` for the roll-up to pass."""

    check_id: str
    title: str
    status: CheckStatus
    detail: str
    mandatory: bool = False
    #: Structured, already-redacted facts (versions, flags). Never raw secrets or absolute paths.
    facts: tuple[tuple[str, str], ...] = ()

    @property
    def is_blocking_failure(self) -> bool:
        """A mandatory check that is not ``PASS`` blocks the live gate."""
        return self.mandatory and self.status is not CheckStatus.PASS


@dataclass(frozen=True, slots=True)
class ReadinessReport:
    """Redaction-safe roll-up of readiness findings for one target environment."""

    environment: str
    checks: tuple[ReadinessCheck, ...] = field(default_factory=tuple)

    @property
    def blocking_failures(self) -> tuple[ReadinessCheck, ...]:
        return tuple(c for c in self.checks if c.is_blocking_failure)

    @property
    def ready(self) -> bool:
        """Ready only when **every mandatory** gate passed. Advisory gaps do not block readiness."""
        return not self.blocking_failures

    def by_status(self, status: CheckStatus) -> tuple[ReadinessCheck, ...]:
        return tuple(c for c in self.checks if c.status is status)
