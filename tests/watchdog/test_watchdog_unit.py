from __future__ import annotations

from dataclasses import replace

import pytest

from factory.watchdog import (
    ALL_INTERVENTION_COMMANDS,
    DegradationRoute,
    FailureObservation,
    HealthState,
    Heartbeat,
    HeartbeatMonitor,
    InterventionCommand,
    RecoveryPolicy,
    SensorSample,
    ServiceSupervisor,
    ThresholdPolicy,
    ThresholdStateMachine,
    WatchdogError,
    WatchdogProcess,
    stable_failure_identity,
)

AUTH_PROOF = "test-watchdog-token"
FORGED_PROOF = "forged-watchdog-token"


def test_allowlist_is_exactly_the_seven_governed_commands() -> None:
    assert frozenset(InterventionCommand) == ALL_INTERVENTION_COMMANDS
    assert {str(command) for command in InterventionCommand} == {
        "PAUSE_TASK",
        "CONTAIN_TASK",
        "RESTART_SERVICE",
        "RECONCILE_STATE",
        "QUARANTINE_RESOURCE",
        "RESTORE_APPROVED_STATE",
        "ACTIVATE_VERIFIED_SNAPSHOT",
    }


def test_heartbeat_uses_monotonic_time_and_rejects_replay() -> None:
    monitor = HeartbeatMonitor(
        supervised_identity="watchdog-1", auth_token=AUTH_PROOF, timeout_seconds=5
    )
    heartbeat = Heartbeat("watchdog-1", 1, 1_000_000.0, AUTH_PROOF)
    monitor.observe(heartbeat, now_monotonic=1_000_000.0)
    assert not monitor.is_stalled(now_monotonic=1_000_004.9)
    assert monitor.is_stalled(now_monotonic=1_000_005.0)
    with pytest.raises(WatchdogError, match="HEARTBEAT_REPLAY"):
        monitor.observe(heartbeat, now_monotonic=1_000_001.0)
    with pytest.raises(WatchdogError, match="HEARTBEAT_UNAUTHENTICATED"):
        monitor.observe(replace(heartbeat, sequence=2, auth_token=FORGED_PROOF), 1_000_001.0)
    with pytest.raises(WatchdogError, match="HEARTBEAT_FROM_FUTURE"):
        monitor.observe(replace(heartbeat, sequence=2, monotonic_ts=1_000_002.0), 1_000_001.0)


def test_wall_clock_rollback_cannot_fabricate_a_stall() -> None:
    monitor = HeartbeatMonitor("watchdog-1", AUTH_PROOF, 10)
    monitor.observe(Heartbeat("watchdog-1", 1, 100.0, AUTH_PROOF), 100.0)
    assert not monitor.is_stalled(109.0)


def test_thresholds_stage_and_recover_with_hysteresis() -> None:
    machine = ThresholdStateMachine(
        ThresholdPolicy(warning_after=2, pause_after=4, critical_after=6, recovery_after=3)
    )
    assert machine.observe(SensorSample(0, True, "ok")) is HealthState.NORMAL
    assert machine.observe(SensorSample(1, False, "event-loop")) is HealthState.NORMAL
    assert machine.observe(SensorSample(3, False, "event-loop")) is HealthState.WARNING
    assert machine.observe(SensorSample(5, False, "event-loop")) is HealthState.PAUSE
    assert machine.observe(SensorSample(7, False, "event-loop")) is HealthState.CRITICAL_CONTAINMENT
    assert machine.observe(SensorSample(8, True, "ok")) is HealthState.CRITICAL_CONTAINMENT
    assert machine.observe(SensorSample(11, True, "ok")) is HealthState.NORMAL


def test_missing_sensor_enters_reduced_monitoring_without_fabrication() -> None:
    machine = ThresholdStateMachine(ThresholdPolicy(1, 2, 3, 1))
    assert (
        machine.observe(SensorSample(0, None, "sensor-missing")) is HealthState.REDUCED_MONITORING
    )
    assert machine.observe(SensorSample(1, True, "restored")) is HealthState.REDUCED_MONITORING
    assert machine.observe(SensorSample(2, True, "restored")) is HealthState.NORMAL


def test_invalid_threshold_and_monotonic_regression_fail_closed() -> None:
    with pytest.raises(WatchdogError, match="THRESHOLD_POLICY_INVALID"):
        ThresholdPolicy(3, 2, 1, 0)
    process = WatchdogProcess(ThresholdStateMachine(ThresholdPolicy(1, 2, 3, 1)))
    assert process.observe(SensorSample(10, True, "ok")) is HealthState.NORMAL
    with pytest.raises(WatchdogError, match="SENSOR_TIME_REGRESSION"):
        process.observe(SensorSample(9, True, "regressed"))


def test_process_is_not_auto_launched_and_selects_deterministic_interventions() -> None:
    process = WatchdogProcess(ThresholdStateMachine(ThresholdPolicy(1, 2, 3, 1)))
    assert not process.auto_launch
    assert (
        process.intervention_for(HealthState.CRITICAL_CONTAINMENT, high_risk=False)
        is InterventionCommand.CONTAIN_TASK
    )
    assert (
        process.intervention_for(HealthState.PAUSE, high_risk=False)
        is InterventionCommand.PAUSE_TASK
    )
    assert (
        process.intervention_for(HealthState.REDUCED_MONITORING, high_risk=True)
        is InterventionCommand.PAUSE_TASK
    )
    assert process.intervention_for(HealthState.WARNING, high_risk=True) is None
    assert process.degradation_route(HealthState.REDUCED_MONITORING) is DegradationRoute.SAFE_MODE
    assert (
        process.degradation_route(HealthState.CRITICAL_CONTAINMENT) is DegradationRoute.QUARANTINE
    )
    assert process.degradation_route(HealthState.NORMAL) is DegradationRoute.CONTINUE


def test_failure_identity_excludes_volatile_fields_and_is_deterministic() -> None:
    left = FailureObservation("TimeoutError", "tool.invoke", "task-1", "E_TIMEOUT", 10, 111)
    right = FailureObservation("TimeoutError", "tool.invoke", "task-1", "E_TIMEOUT", 99, 222)
    assert stable_failure_identity(left) == stable_failure_identity(right)
    assert stable_failure_identity(left) != stable_failure_identity(
        replace(right, stable_code="E_OTHER")
    )


class _Controller:
    def __init__(self, outcomes: list[bool]) -> None:
        self.outcomes = outcomes
        self.calls: list[str] = []

    def restart(self, service_id: str) -> bool:
        self.calls.append(service_id)
        return self.outcomes.pop(0)

    def state(self, service_id: str) -> str:
        return f"{service_id}:running"


def test_service_supervisor_bounds_retries_and_opens_circuit() -> None:
    controller = _Controller([False, False, False])
    delays: list[float] = []
    supervisor = ServiceSupervisor(
        controller,
        RecoveryPolicy(max_attempts=3, initial_backoff=0.1, multiplier=2),
        delays.append,
    )
    assert not supervisor.restart("svc-1")
    assert controller.calls == ["svc-1", "svc-1", "svc-1"]
    assert delays == [0.1, 0.2]
    assert supervisor.circuit_open("svc-1")
    with pytest.raises(WatchdogError, match="RECOVERY_CIRCUIT_OPEN"):
        supervisor.restart("svc-1")


@pytest.mark.parametrize(
    "arguments",
    [
        {"max_attempts": 0},
        {"initial_backoff": -1},
        {"multiplier": 0.5},
    ],
)
def test_invalid_recovery_policy_is_rejected(arguments: dict[str, float]) -> None:
    with pytest.raises(WatchdogError, match="RECOVERY_POLICY_INVALID"):
        RecoveryPolicy(**arguments)  # type: ignore[arg-type]
