"""Stable failure identity and bounded recovery policy."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass

from factory.watchdog.errors import WatchdogError
from factory.watchdog.models import FailureObservation, ServiceController

_SEP = "\x1f"


def stable_failure_identity(observation: FailureObservation) -> str:
    canonical = _SEP.join(
        (
            observation.exception_type,
            observation.action_class,
            observation.target_ref,
            observation.stable_code,
        )
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class RecoveryPolicy:
    max_attempts: int = 3
    initial_backoff: float = 0.0
    multiplier: float = 2.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1 or self.initial_backoff < 0 or self.multiplier < 1:
            raise WatchdogError("RECOVERY_POLICY_INVALID", "recovery bounds are invalid")


class ServiceSupervisor:
    """Bounded service-control adapter; it has no shell, DB, file, or policy mutation path."""

    def __init__(
        self,
        controller: ServiceController,
        policy: RecoveryPolicy | None = None,
        backoff: Callable[[float], None] | None = None,
    ) -> None:
        self._controller = controller
        self._policy = policy or RecoveryPolicy()
        self._backoff = backoff
        self._open_circuits: set[str] = set()

    def state_hash(self, service_id: str) -> str:
        state = self._controller.state(service_id)
        return hashlib.sha256(f"{service_id}{_SEP}{state}".encode()).hexdigest()

    def circuit_open(self, service_id: str) -> bool:
        return service_id in self._open_circuits

    def restart(self, service_id: str) -> bool:
        if self.circuit_open(service_id):
            raise WatchdogError(
                "RECOVERY_CIRCUIT_OPEN", f"restart circuit is open for {service_id}"
            )
        delay = self._policy.initial_backoff
        for attempt in range(self._policy.max_attempts):
            if self._controller.restart(service_id):
                return True
            if attempt + 1 < self._policy.max_attempts and self._backoff is not None:
                self._backoff(delay)
                delay *= self._policy.multiplier
        self._open_circuits.add(service_id)
        return False


__all__ = ["RecoveryPolicy", "ServiceSupervisor", "stable_failure_identity"]
