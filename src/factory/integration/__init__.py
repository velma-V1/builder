"""PH-6 (Task 6.5) — integration coordinator + simulated three-workstream demonstration.

The coordinator compares baselines/manifests, validates local gates, detects conflicts, combines
approved commits, and assigns evidence-backed remediation to owning lanes — never editing source.
The demo runs three independent workstreams end-to-end against the PH-4/PH-5 fakes (simulated IP-3).
"""

from __future__ import annotations

from factory.integration.coordinator import COORDINATOR_EDITS_SOURCE, IntegrationCoordinator
from factory.integration.demo import SimulatedIP3Report, run_simulated_ip3
from factory.integration.errors import IntegrationError
from factory.integration.models import (
    IntegrationReport,
    IntegrationVerdict,
    RemediationTask,
    WorkstreamResult,
)

__all__ = [
    "COORDINATOR_EDITS_SOURCE",
    "IntegrationCoordinator",
    "IntegrationError",
    "IntegrationReport",
    "IntegrationVerdict",
    "RemediationTask",
    "SimulatedIP3Report",
    "WorkstreamResult",
    "run_simulated_ip3",
]
