"""CMP-WATCH public API. The journal writer is intentionally not exported."""

from factory.watchdog.control import WatchdogControl
from factory.watchdog.errors import WatchdogError
from factory.watchdog.failures import (
    RecoveryPolicy,
    ServiceSupervisor,
    stable_failure_identity,
)
from factory.watchdog.heartbeat import HeartbeatMonitor
from factory.watchdog.interventions import WatchdogInterventionReceiver
from factory.watchdog.models import (
    ALL_INTERVENTION_COMMANDS,
    DegradationRoute,
    FailureObservation,
    HealthState,
    Heartbeat,
    HighRiskDecision,
    InterventionCommand,
    InterventionOutcome,
    InterventionRequest,
    InterventionResult,
    SensorSample,
    task_state_hash,
)
from factory.watchdog.process import WatchdogProcess, decide_high_risk_admission
from factory.watchdog.store import SQLiteInterventionReader, apply_watchdog_migration
from factory.watchdog.thresholds import ThresholdPolicy, ThresholdStateMachine

__all__ = [
    "ALL_INTERVENTION_COMMANDS",
    "DegradationRoute",
    "FailureObservation",
    "HealthState",
    "Heartbeat",
    "HeartbeatMonitor",
    "HighRiskDecision",
    "InterventionCommand",
    "InterventionOutcome",
    "InterventionRequest",
    "InterventionResult",
    "RecoveryPolicy",
    "SQLiteInterventionReader",
    "SensorSample",
    "ServiceSupervisor",
    "ThresholdPolicy",
    "ThresholdStateMachine",
    "WatchdogControl",
    "WatchdogError",
    "WatchdogInterventionReceiver",
    "WatchdogProcess",
    "apply_watchdog_migration",
    "decide_high_risk_admission",
    "stable_failure_identity",
    "task_state_hash",
]
