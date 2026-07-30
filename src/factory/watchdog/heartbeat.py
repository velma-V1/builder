"""Authenticated monotonic heartbeat tracking."""

from __future__ import annotations

import hmac
from dataclasses import dataclass

from factory.watchdog.errors import WatchdogError
from factory.watchdog.models import Heartbeat


@dataclass(slots=True)
class HeartbeatMonitor:
    supervised_identity: str
    auth_token: str
    timeout_seconds: float
    _last_sequence: int = -1
    _last_seen: float | None = None

    def observe(self, heartbeat: Heartbeat, now_monotonic: float) -> None:
        identity_ok = hmac.compare_digest(heartbeat.identity, self.supervised_identity)
        token_ok = hmac.compare_digest(heartbeat.auth_token, self.auth_token)
        if not identity_ok or not token_ok:
            raise WatchdogError(
                "HEARTBEAT_UNAUTHENTICATED", "heartbeat identity or token did not authenticate"
            )
        if heartbeat.sequence <= self._last_sequence:
            raise WatchdogError("HEARTBEAT_REPLAY", "heartbeat sequence was not increasing")
        if heartbeat.monotonic_ts > now_monotonic:
            raise WatchdogError("HEARTBEAT_FROM_FUTURE", "heartbeat timestamp is in the future")
        self._last_sequence = heartbeat.sequence
        self._last_seen = now_monotonic

    def is_stalled(self, now_monotonic: float) -> bool:
        return self._last_seen is None or now_monotonic - self._last_seen >= self.timeout_seconds


__all__ = ["HeartbeatMonitor"]
