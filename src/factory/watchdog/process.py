"""Read-only Watchdog process policy and Watchdog-loss fail-closed admission."""

from __future__ import annotations

from dataclasses import dataclass

from factory.watchdog.models import (
    DegradationRoute,
    HealthState,
    HighRiskDecision,
    InterventionCommand,
    SensorSample,
)
from factory.watchdog.thresholds import ThresholdStateMachine


def decide_high_risk_admission(
    watchdog_available: bool, already_running: bool, risk_class: int
) -> HighRiskDecision:
    if watchdog_available or risk_class < 5:
        return HighRiskDecision.ALLOW
    return HighRiskDecision.PAUSE_EXISTING if already_running else HighRiskDecision.BLOCK_NEW


@dataclass(frozen=True, slots=True)
class WatchdogProcess:
    """One-cycle observer with no writable DB, shell, filesystem, or policy interface."""

    thresholds: ThresholdStateMachine
    auto_launch: bool = False

    def observe(self, sample: SensorSample) -> HealthState:
        return self.thresholds.observe(sample)

    @staticmethod
    def intervention_for(state: HealthState, *, high_risk: bool) -> InterventionCommand | None:
        if state is HealthState.CRITICAL_CONTAINMENT:
            return InterventionCommand.CONTAIN_TASK
        if state is HealthState.PAUSE or (state is HealthState.REDUCED_MONITORING and high_risk):
            return InterventionCommand.PAUSE_TASK
        return None

    @staticmethod
    def degradation_route(state: HealthState) -> DegradationRoute:
        if state is HealthState.CRITICAL_CONTAINMENT:
            return DegradationRoute.QUARANTINE
        if state is HealthState.REDUCED_MONITORING:
            return DegradationRoute.SAFE_MODE
        return DegradationRoute.CONTINUE


__all__ = ["WatchdogProcess", "decide_high_risk_admission"]
