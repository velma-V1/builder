"""PH-6 (Section 6) — three parallel major-stage workstreams — simulated core.

Deterministic, offline workstream engine built from ``01D``: CTR-WORKSTREAM declarations, the
independence-before-parallel admission gate (≤3 cap), single-writer ownership leases, the lane
lifecycle state machine with isolated checkouts, conflict detection beyond files with an immutable
integration baseline, the priority/interruption/resume scheduler with three-failure quarantine, and
(in ``factory.integration``) an integration coordinator that never edits source. Live sandbox/router
assignment is simulated via the PH-4/PH-5 fakes; live integration (IP-3) is
LIVE_INTEGRATION_PENDING.
"""

from __future__ import annotations

from factory.workstream.admission import AdmissionController
from factory.workstream.errors import WorkstreamError
from factory.workstream.models import (
    AdmissionOutcome,
    AdmissionResult,
    IndependenceFinding,
    IndependenceKind,
    OwnershipLease,
    WorkstreamContract,
)
from factory.workstream.ownership import OwnershipRegistry

__all__ = [
    "AdmissionController",
    "AdmissionOutcome",
    "AdmissionResult",
    "IndependenceFinding",
    "IndependenceKind",
    "OwnershipLease",
    "OwnershipRegistry",
    "WorkstreamContract",
    "WorkstreamError",
]
