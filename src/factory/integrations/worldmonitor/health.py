"""WorldMonitor health probe (brokered; read-only)."""

from __future__ import annotations

import json

from factory.integrations.worldmonitor.errors import WorldMonitorError
from factory.integrations.worldmonitor.models import HealthState, WorldMonitorHealth
from factory.integrations.worldmonitor.policy import BrokeredWorldMonitorHttp

_STATE = {
    "healthy": HealthState.HEALTHY,
    "ok": HealthState.HEALTHY,
    "degraded": HealthState.DEGRADED,
}


def check_health(brokered: BrokeredWorldMonitorHttp, base_url: str, now: int) -> WorldMonitorHealth:
    """Probe ``GET {base_url}/health``. Any error → UNAVAILABLE (fail closed)."""
    try:
        response = brokered.request("GET", f"{base_url}/health")
    except WorldMonitorError as exc:
        return WorldMonitorHealth(HealthState.UNAVAILABLE, brokered.redact(exc.detail), now)
    if response.status != 200:
        return WorldMonitorHealth(HealthState.UNAVAILABLE, f"HTTP {response.status}", now)
    try:
        data = json.loads(response.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return WorldMonitorHealth(HealthState.DEGRADED, "unparseable health payload", now)
    status = str(data.get("status", "")).lower() if isinstance(data, dict) else ""
    return WorldMonitorHealth(_STATE.get(status, HealthState.DEGRADED), status or "unknown", now)
