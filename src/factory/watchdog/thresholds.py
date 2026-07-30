"""Deterministic staged health thresholds driven only by monotonic time."""

from __future__ import annotations

from dataclasses import dataclass

from factory.watchdog.errors import WatchdogError
from factory.watchdog.models import HealthState, SensorSample


@dataclass(frozen=True, slots=True)
class ThresholdPolicy:
    warning_after: float
    pause_after: float
    critical_after: float
    recovery_after: float

    def __post_init__(self) -> None:
        if not (
            0 <= self.warning_after <= self.pause_after <= self.critical_after
            and self.recovery_after >= 0
        ):
            raise WatchdogError("THRESHOLD_POLICY_INVALID", "threshold ordering is invalid")


@dataclass(slots=True)
class ThresholdStateMachine:
    policy: ThresholdPolicy
    state: HealthState = HealthState.NORMAL
    _unhealthy_since: float | None = None
    _healthy_since: float | None = None
    _last_observed: float | None = None

    def observe(self, sample: SensorSample) -> HealthState:
        if self._last_observed is not None and sample.monotonic_ts < self._last_observed:
            raise WatchdogError("SENSOR_TIME_REGRESSION", "monotonic sensor time regressed")
        self._last_observed = sample.monotonic_ts

        if sample.healthy is None:
            self._healthy_since = None
            self._unhealthy_since = None
            self.state = HealthState.REDUCED_MONITORING
            return self.state

        if sample.healthy:
            self._unhealthy_since = None
            if self.state is HealthState.NORMAL:
                self._healthy_since = sample.monotonic_ts
                return self.state
            if self._healthy_since is None:
                self._healthy_since = sample.monotonic_ts
            if sample.monotonic_ts - self._healthy_since >= self.policy.recovery_after:
                self.state = HealthState.NORMAL
            return self.state

        self._healthy_since = None
        if self._unhealthy_since is None:
            self._unhealthy_since = sample.monotonic_ts
        elapsed = sample.monotonic_ts - self._unhealthy_since
        if elapsed >= self.policy.critical_after:
            self.state = HealthState.CRITICAL_CONTAINMENT
        elif elapsed >= self.policy.pause_after:
            self.state = HealthState.PAUSE
        elif elapsed >= self.policy.warning_after:
            self.state = HealthState.WARNING
        return self.state


__all__ = ["ThresholdPolicy", "ThresholdStateMachine"]
