"""PH-4 (Task 4.4) — Resource Scheduler + quota ledger.

Owns the executable admission-control logic: versioned reservations with a single-active GPU-heavy
policy, VRAM/RAM/CPU/storage ceilings, anti-thrash cooldown, deterministic resource-pressure order,
REDUCED_MONITORING on missing sensors, restart reconciliation, and the quota/usage ledger. Consumes
the shared PH-4 model-neutral vocabulary from ``factory.routing.models``.
"""

from __future__ import annotations

from factory.scheduler.quota import QuotaLedger
from factory.scheduler.scheduler import (
    AdmissionOutcome,
    AdmissionResult,
    ResourceScheduler,
)

__all__ = [
    "AdmissionOutcome",
    "AdmissionResult",
    "QuotaLedger",
    "ResourceScheduler",
]
