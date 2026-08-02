from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Protocol

from factory.audit import AuditEvent, AuditValidator, AuditWriter, RecordKind
from factory.orchestrator.models import TaskState
from factory.orchestrator.store.runtime_state import SQLiteOrchestratorStateReader
from factory.safemode import SafeMode
from factory.watchdog import (
    CrossLaneOutcome,
    RPH3CrossLaneBridge,
    task_state_hash,
)
from factory.watchdog.interventions import WatchdogInterventionReceiver
from factory.watchdog.models import Clock


class CrossLaneClock(Clock, Protocol):
    pass


def _seed_and_break(audit_path: Path, clock: CrossLaneClock) -> None:
    AuditWriter(audit_path).append(
        AuditEvent(
            op_key="seed",
            record_kind=RecordKind.COMPLETION,
            operation_class=1,
            actor="test",
            action_class="test",
            payload_hash="payload",
            occurred_at=clock.now_iso(),
        )
    )
    connection = sqlite3.connect(audit_path)
    try:
        connection.execute("DROP TRIGGER audit_records_no_update")
        connection.execute("DROP TRIGGER audit_records_no_delete")
        connection.execute("UPDATE audit_records SET actor = 'tampered' WHERE sequence = 1")
        connection.commit()
    finally:
        connection.close()


def test_healthy_lane_b_has_no_intervention(
    bridge: RPH3CrossLaneBridge,
    task_reader: SQLiteOrchestratorStateReader,
    running_task: str,
) -> None:
    expected = task_state_hash(task_reader.get_task(running_task))
    result = bridge.audit_health(running_task, expected, "op-audit-healthy")
    assert result.outcome is CrossLaneOutcome.HEALTHY
    current = task_reader.get_task(running_task)
    assert current is not None and current.current_state is TaskState.RUNNING


def test_audit_break_is_observed_contained_and_idempotent(
    bridge: RPH3CrossLaneBridge,
    databases: tuple[Path, Path, Path],
    task_reader: SQLiteOrchestratorStateReader,
    running_task: str,
    clock: CrossLaneClock,
) -> None:
    expected = task_state_hash(task_reader.get_task(running_task))
    _seed_and_break(databases[1], clock)
    first = bridge.audit_health(running_task, expected, "op-audit-break")
    second = bridge.audit_health(running_task, expected, "op-audit-break")
    assert first.outcome is CrossLaneOutcome.INTERVENED
    assert second == first
    current = task_reader.get_task(running_task)
    assert current is not None and current.current_state is TaskState.QUARANTINED


def test_restart_duplicate_delivery_uses_wir_durable_result(
    bridge: RPH3CrossLaneBridge,
    receiver: WatchdogInterventionReceiver,
    safe_mode: SafeMode,
    databases: tuple[Path, Path, Path],
    task_reader: SQLiteOrchestratorStateReader,
    running_task: str,
    clock: CrossLaneClock,
) -> None:
    expected = task_state_hash(task_reader.get_task(running_task))
    _seed_and_break(databases[1], clock)
    first = bridge.audit_health(running_task, expected, "op-restart-replay")
    restarted_bridge = RPH3CrossLaneBridge(
        receiver=receiver,
        control=bridge.control,
        task_reader=task_reader,
        safe_mode=safe_mode,
        audit_validator=AuditValidator(databases[1]),
        clock=clock,
    )
    replay = restarted_bridge.audit_health(running_task, expected, "op-restart-replay")
    assert replay.outcome is CrossLaneOutcome.INTERVENED
    assert replay.intervention == first.intervention


def test_dependency_failure_pauses_and_safe_mode_escalation_is_read_only(
    bridge: RPH3CrossLaneBridge,
    task_reader: SQLiteOrchestratorStateReader,
    running_task: str,
) -> None:
    expected = task_state_hash(task_reader.get_task(running_task))
    paused = bridge.dependency_failure(
        source="CMP-PERM",
        target_ref=running_task,
        expected_state=expected,
        detail="permission store unavailable",
        op_key="op-dependency-down",
    )
    assert paused.outcome is CrossLaneOutcome.INTERVENED
    current = task_reader.get_task(running_task)
    assert current is not None and current.current_state is TaskState.PAUSED

    safe = bridge.request_safe_mode(
        target_ref=running_task,
        detail="reduced monitoring",
        op_key="op-safe-mode",
    )
    assert safe.outcome is CrossLaneOutcome.SAFE_MODE
    assert safe.safe_mode_session is not None
    assert "autonomous_write" in safe.safe_mode_session.blocked_capabilities
