"""Narrow authenticated request factory used by the independent Watchdog process."""

from __future__ import annotations

from dataclasses import dataclass

from factory.watchdog.models import Clock, InterventionCommand, InterventionRequest


@dataclass(frozen=True, slots=True)
class WatchdogControl:
    identity: str
    auth_token: str
    clock: Clock

    def request(
        self,
        command: InterventionCommand,
        target_ref: str,
        expected_state: str,
        reason: str,
        idempotency_key: str,
    ) -> InterventionRequest:
        return InterventionRequest(
            command=command,
            target_ref=target_ref,
            expected_state=expected_state,
            reason=reason,
            requestor=self.identity,
            idempotency_key=idempotency_key,
            monotonic_ts=int(self.clock.monotonic()),
            auth_token=self.auth_token,
        )


__all__ = ["WatchdogControl"]
