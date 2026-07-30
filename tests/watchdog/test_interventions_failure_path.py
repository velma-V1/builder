from __future__ import annotations

from pathlib import Path

import pytest

from factory.audit import AuditError, AuditEvent, AuditRecord, AuditWriter, RecordKind
from factory.orchestrator.models import TaskState
from factory.orchestrator.store.runtime_state import (
    SQLiteOrchestratorStateReader,
    _OrchestratorStateWriter,
)
from factory.watchdog import (
    HighRiskDecision,
    InterventionCommand,
    InterventionOutcome,
    ServiceSupervisor,
    WatchdogControl,
    WatchdogError,
    WatchdogInterventionReceiver,
    decide_high_risk_admission,
    task_state_hash,
)
from factory.watchdog.models import Clock
from factory.watchdog.writer import _InterventionWriter

AUTH_PROOF = "test-watchdog-token"


class _Allow:
    def authorize(self, _request: object) -> bool:
        return True


class _FailingController:
    def restart(self, _service_id: str) -> bool:
        return False

    def state(self, service_id: str) -> str:
        return f"{service_id}:degraded"


class _ExplodingController:
    def restart(self, _service_id: str) -> bool:
        raise AssertionError("restart must not be retried during reconciliation")

    def state(self, service_id: str) -> str:
        return f"{service_id}:unknown"


def test_watchdog_or_receiver_loss_blocks_new_and_pauses_existing_high_risk() -> None:
    assert decide_high_risk_admission(False, False, 5) is HighRiskDecision.BLOCK_NEW
    assert decide_high_risk_admission(False, True, 5) is HighRiskDecision.PAUSE_EXISTING
    assert decide_high_risk_admission(True, True, 5) is HighRiskDecision.ALLOW
    assert decide_high_risk_admission(False, True, 2) is HighRiskDecision.ALLOW


def test_failed_restart_is_audited_but_never_reported_applied(
    security_db_path: Path,
    audit_db_path: Path,
    task_reader: SQLiteOrchestratorStateReader,
    task_writer: _OrchestratorStateWriter,
    clock: Clock,
) -> None:
    supervisor = ServiceSupervisor(_FailingController())
    receiver = WatchdogInterventionReceiver(
        security_db_path,
        audit_db_path,
        task_reader,
        task_writer,
        _Allow(),
        supervisor,
        clock,
        supervised_identity="watchdog-1",
        auth_token=AUTH_PROOF,
    )
    request = WatchdogControl("watchdog-1", AUTH_PROOF, clock).request(
        InterventionCommand.RESTART_SERVICE,
        "svc-1",
        supervisor.state_hash("svc-1"),
        "stalled",
        "op-failed-restart",
    )
    result = receiver.intervene(request)
    assert result.outcome is InterventionOutcome.FAILED
    assert result.audit_seq is None


def test_reconcile_state_uses_journal_outcome_and_legal_transition(
    security_db_path: Path,
    audit_db_path: Path,
    task_reader: SQLiteOrchestratorStateReader,
    task_writer: _OrchestratorStateWriter,
    clock: Clock,
) -> None:
    task_writer.create_task(task_id="task-1", project_id="p", contract_version=1)
    task_writer.apply_transition(
        task_id="task-1",
        expected_current_state=TaskState.QUEUED,
        new_state=TaskState.PLANNING,
        cause="test",
        actor="test",
    )
    task_writer.apply_transition(
        task_id="task-1",
        expected_current_state=TaskState.PLANNING,
        new_state=TaskState.RUNNING,
        cause="test",
        actor="test",
    )
    receiver = WatchdogInterventionReceiver(
        security_db_path,
        audit_db_path,
        task_reader,
        task_writer,
        _Allow(),
        ServiceSupervisor(_FailingController()),
        clock,
        supervised_identity="watchdog-1",
        auth_token=AUTH_PROOF,
    )
    request = WatchdogControl("watchdog-1", AUTH_PROOF, clock).request(
        InterventionCommand.RECONCILE_STATE,
        "task-1",
        task_state_hash(task_reader.get_task("task-1")),
        "startup",
        "op-reconcile",
    )
    assert receiver.intervene(request).outcome is InterventionOutcome.APPLIED
    reconciled = task_reader.get_task("task-1")
    assert reconciled is not None
    assert reconciled.current_state is TaskState.BLOCKED


def test_class2_crash_windows_roll_forward_or_back(
    security_db_path: Path,
    audit_db_path: Path,
    task_reader: SQLiteOrchestratorStateReader,
    task_writer: _OrchestratorStateWriter,
    clock: Clock,
) -> None:
    task_id = "task-forward"
    task_writer.create_task(task_id=task_id, project_id="p", contract_version=1)
    task_writer.apply_transition(
        task_id=task_id,
        expected_current_state=TaskState.QUEUED,
        new_state=TaskState.PLANNING,
        cause="test",
        actor="test",
    )
    task_writer.apply_transition(
        task_id=task_id,
        expected_current_state=TaskState.PLANNING,
        new_state=TaskState.RUNNING,
        cause="test",
        actor="test",
    )
    current = task_reader.get_task(task_id)
    assert current is not None
    forward = WatchdogControl("watchdog-1", AUTH_PROOF, clock).request(
        InterventionCommand.PAUSE_TASK,
        task_id,
        task_state_hash(current),
        "crash-window",
        "op-roll-forward",
    )
    writer = _InterventionWriter(security_db_path)
    writer.stage(forward, 2, clock.now_ts(), desired_state=str(TaskState.PAUSED))
    task_writer.apply_transition(
        task_id=task_id,
        expected_current_state=TaskState.RUNNING,
        new_state=TaskState.PAUSED,
        cause="crash-window",
        actor="watchdog-intervention-receiver",
        idempotency_key=forward.idempotency_key,
    )

    rollback = WatchdogControl("watchdog-1", AUTH_PROOF, clock).request(
        InterventionCommand.PAUSE_TASK,
        "missing-task",
        task_state_hash(None),
        "crash-window",
        "op-roll-back",
    )
    writer.stage(rollback, 2, clock.now_ts(), desired_state=str(TaskState.PAUSED))

    receiver = WatchdogInterventionReceiver(
        security_db_path,
        audit_db_path,
        task_reader,
        task_writer,
        _Allow(),
        ServiceSupervisor(_FailingController()),
        clock,
        supervised_identity="watchdog-1",
        auth_token=AUTH_PROOF,
    )
    receiver.reconcile_startup()
    rolled_forward = receiver.reader.get("op-roll-forward")
    rolled_back = receiver.reader.get("op-roll-back")
    assert rolled_forward is not None
    assert rolled_forward.result_outcome is InterventionOutcome.APPLIED
    assert rolled_back is not None
    assert rolled_back.result_outcome is InterventionOutcome.FAILED


def test_class2_crash_after_completion_reuses_durable_audit(
    security_db_path: Path,
    audit_db_path: Path,
    task_reader: SQLiteOrchestratorStateReader,
    task_writer: _OrchestratorStateWriter,
    clock: Clock,
) -> None:
    task_writer.create_task(task_id="task-1", project_id="p", contract_version=1)
    task_writer.apply_transition(
        task_id="task-1",
        expected_current_state=TaskState.QUEUED,
        new_state=TaskState.PLANNING,
        cause="test",
        actor="test",
    )
    task_writer.apply_transition(
        task_id="task-1",
        expected_current_state=TaskState.PLANNING,
        new_state=TaskState.RUNNING,
        cause="test",
        actor="test",
    )
    current = task_reader.get_task("task-1")
    assert current is not None
    request = WatchdogControl("watchdog-1", AUTH_PROOF, clock).request(
        InterventionCommand.PAUSE_TASK,
        "task-1",
        task_state_hash(current),
        "crash-window",
        "op-after-audit",
    )
    _InterventionWriter(security_db_path).stage(
        request, 2, clock.now_ts(), desired_state=str(TaskState.PAUSED)
    )
    task_writer.apply_transition(
        task_id="task-1",
        expected_current_state=TaskState.RUNNING,
        new_state=TaskState.PAUSED,
        cause="crash-window",
        actor="watchdog-intervention-receiver",
        idempotency_key=request.idempotency_key,
    )
    AuditWriter(audit_db_path).append(
        AuditEvent(
            op_key=request.idempotency_key,
            record_kind=RecordKind.COMPLETION,
            operation_class=2,
            actor="watchdog-intervention-receiver",
            action_class="watchdog.pause_task",
            payload_hash=request.request_hash(),
            occurred_at=clock.now_iso(),
            target_ref=request.target_ref,
        )
    )
    receiver = WatchdogInterventionReceiver(
        security_db_path,
        audit_db_path,
        task_reader,
        task_writer,
        _Allow(),
        ServiceSupervisor(_ExplodingController()),
        clock,
        supervised_identity="watchdog-1",
        auth_token=AUTH_PROOF,
    )
    receiver.reconcile_startup()
    record = receiver.reader.get(request.idempotency_key)
    assert record is not None
    assert record.result_outcome is InterventionOutcome.APPLIED
    assert len(AuditWriter(audit_db_path).export()) == 1


def test_class3_crash_before_audit_intent_is_aborted_without_restart(
    security_db_path: Path,
    audit_db_path: Path,
    task_reader: SQLiteOrchestratorStateReader,
    task_writer: _OrchestratorStateWriter,
    clock: Clock,
) -> None:
    request = WatchdogControl("watchdog-1", AUTH_PROOF, clock).request(
        InterventionCommand.RESTART_SERVICE,
        "svc-1",
        "state",
        "crash-window",
        "op-uncertain",
    )
    _InterventionWriter(security_db_path).stage(request, 3, clock.now_ts())
    receiver = WatchdogInterventionReceiver(
        security_db_path,
        audit_db_path,
        task_reader,
        task_writer,
        _Allow(),
        ServiceSupervisor(_ExplodingController()),
        clock,
        supervised_identity="watchdog-1",
        auth_token=AUTH_PROOF,
    )
    receiver.reconcile_startup()
    record = receiver.reader.get("op-uncertain")
    assert record is not None
    assert record.status.value == "ABORTED"
    assert record.failure_code == "RESTART_NOT_ISSUED"


def test_class3_crash_after_intent_is_quarantined_without_retry(
    security_db_path: Path,
    audit_db_path: Path,
    task_reader: SQLiteOrchestratorStateReader,
    task_writer: _OrchestratorStateWriter,
    clock: Clock,
) -> None:
    request = WatchdogControl("watchdog-1", AUTH_PROOF, clock).request(
        InterventionCommand.RESTART_SERVICE,
        "svc-1",
        "state",
        "crash-window",
        "op-intent-only",
    )
    writer = _InterventionWriter(security_db_path)
    writer.stage(request, 3, clock.now_ts())
    intent = AuditWriter(audit_db_path).append(
        AuditEvent(
            op_key=request.idempotency_key,
            record_kind=RecordKind.INTENT,
            operation_class=3,
            actor="watchdog-intervention-receiver",
            action_class="watchdog.restart_service",
            payload_hash=request.request_hash(),
            occurred_at=clock.now_iso(),
            target_ref=request.target_ref,
        )
    )
    writer.mark_audit_intent(request.idempotency_key, intent.sequence, clock.now_ts())
    receiver = WatchdogInterventionReceiver(
        security_db_path,
        audit_db_path,
        task_reader,
        task_writer,
        _Allow(),
        ServiceSupervisor(_ExplodingController()),
        clock,
        supervised_identity="watchdog-1",
        auth_token=AUTH_PROOF,
    )
    receiver.reconcile_startup()
    record = receiver.reader.get(request.idempotency_key)
    assert record is not None
    assert record.status.value == "QUARANTINED"
    assert record.failure_code == "RESTART_OUTCOME_UNPROVEN"


def test_class3_crash_after_completion_rolls_forward_without_restart(
    security_db_path: Path,
    audit_db_path: Path,
    task_reader: SQLiteOrchestratorStateReader,
    task_writer: _OrchestratorStateWriter,
    clock: Clock,
) -> None:
    request = WatchdogControl("watchdog-1", AUTH_PROOF, clock).request(
        InterventionCommand.RESTART_SERVICE,
        "svc-1",
        "state",
        "crash-window",
        "op-complete",
    )
    writer = _InterventionWriter(security_db_path)
    writer.stage(request, 3, clock.now_ts())
    audit = AuditWriter(audit_db_path)
    intent = audit.append(
        AuditEvent(
            op_key=request.idempotency_key,
            record_kind=RecordKind.INTENT,
            operation_class=3,
            actor="watchdog-intervention-receiver",
            action_class="watchdog.restart_service",
            payload_hash=request.request_hash(),
            occurred_at=clock.now_iso(),
            target_ref=request.target_ref,
        )
    )
    writer.mark_audit_intent(request.idempotency_key, intent.sequence, clock.now_ts())
    audit.append(
        AuditEvent(
            op_key=request.idempotency_key,
            record_kind=RecordKind.COMPLETION,
            operation_class=3,
            actor="watchdog-intervention-receiver",
            action_class="watchdog.restart_service",
            payload_hash=request.request_hash(),
            occurred_at=clock.now_iso(),
            target_ref=request.target_ref,
        )
    )
    receiver = WatchdogInterventionReceiver(
        security_db_path,
        audit_db_path,
        task_reader,
        task_writer,
        _Allow(),
        ServiceSupervisor(_ExplodingController()),
        clock,
        supervised_identity="watchdog-1",
        auth_token=AUTH_PROOF,
    )
    receiver.reconcile_startup()
    record = receiver.reader.get(request.idempotency_key)
    assert record is not None
    assert record.status.value == "COMMITTED"
    assert record.result_outcome is InterventionOutcome.APPLIED


def test_illegal_transition_is_failed_not_applied(
    security_db_path: Path,
    audit_db_path: Path,
    task_reader: SQLiteOrchestratorStateReader,
    task_writer: _OrchestratorStateWriter,
    clock: Clock,
) -> None:
    task_writer.create_task(task_id="task-1", project_id="p", contract_version=1)
    task_writer.apply_transition(
        task_id="task-1",
        expected_current_state=TaskState.QUEUED,
        new_state=TaskState.PLANNING,
        cause="test",
        actor="test",
    )
    current = task_reader.get_task("task-1")
    assert current is not None
    receiver = WatchdogInterventionReceiver(
        security_db_path,
        audit_db_path,
        task_reader,
        task_writer,
        _Allow(),
        ServiceSupervisor(_FailingController()),
        clock,
        supervised_identity="watchdog-1",
        auth_token=AUTH_PROOF,
    )
    request = WatchdogControl("watchdog-1", AUTH_PROOF, clock).request(
        InterventionCommand.PAUSE_TASK,
        "task-1",
        task_state_hash(current),
        "test",
        "op-illegal",
    )
    assert receiver.intervene(request).outcome is InterventionOutcome.FAILED


def test_audit_finalize_outage_never_reports_class2_applied(
    monkeypatch: pytest.MonkeyPatch,
    security_db_path: Path,
    audit_db_path: Path,
    task_reader: SQLiteOrchestratorStateReader,
    task_writer: _OrchestratorStateWriter,
    clock: Clock,
) -> None:
    task_writer.create_task(task_id="task-1", project_id="p", contract_version=1)
    task_writer.apply_transition(
        task_id="task-1",
        expected_current_state=TaskState.QUEUED,
        new_state=TaskState.PLANNING,
        cause="test",
        actor="test",
    )
    current = task_reader.get_task("task-1")
    assert current is not None
    receiver = WatchdogInterventionReceiver(
        security_db_path,
        audit_db_path,
        task_reader,
        task_writer,
        _Allow(),
        ServiceSupervisor(_FailingController()),
        clock,
        supervised_identity="watchdog-1",
        auth_token=AUTH_PROOF,
    )

    def unavailable(_writer: AuditWriter, _event: AuditEvent) -> AuditRecord:
        raise AuditError("AUDIT_DOWN", "unavailable")

    monkeypatch.setattr(AuditWriter, "append", unavailable)
    request = WatchdogControl("watchdog-1", AUTH_PROOF, clock).request(
        InterventionCommand.PAUSE_TASK,
        "task-1",
        task_state_hash(current),
        "test",
        "op-audit-down",
    )
    with pytest.raises(WatchdogError, match="WIR_AUDIT_UNAVAILABLE"):
        receiver.intervene(request)


def test_crash_before_intent_persist_has_no_effect_or_audit(
    monkeypatch: pytest.MonkeyPatch,
    security_db_path: Path,
    audit_db_path: Path,
    task_reader: SQLiteOrchestratorStateReader,
    task_writer: _OrchestratorStateWriter,
    clock: Clock,
) -> None:
    task_writer.create_task(task_id="task-1", project_id="p", contract_version=1)
    task_writer.apply_transition(
        task_id="task-1",
        expected_current_state=TaskState.QUEUED,
        new_state=TaskState.PLANNING,
        cause="test",
        actor="test",
    )
    task_writer.apply_transition(
        task_id="task-1",
        expected_current_state=TaskState.PLANNING,
        new_state=TaskState.RUNNING,
        cause="test",
        actor="test",
    )
    current = task_reader.get_task("task-1")
    assert current is not None
    receiver = WatchdogInterventionReceiver(
        security_db_path,
        audit_db_path,
        task_reader,
        task_writer,
        _Allow(),
        ServiceSupervisor(_FailingController()),
        clock,
        supervised_identity="watchdog-1",
        auth_token=AUTH_PROOF,
    )

    def fail_stage(
        _writer: _InterventionWriter,
        _request: object,
        _operation_class: int,
        _now: int,
        *,
        desired_state: str | None = None,
    ) -> None:
        del desired_state
        raise WatchdogError("INTERVENTION_STAGE_FAILED", "simulated store outage")

    monkeypatch.setattr(_InterventionWriter, "stage", fail_stage)
    request = WatchdogControl("watchdog-1", AUTH_PROOF, clock).request(
        InterventionCommand.PAUSE_TASK,
        "task-1",
        task_state_hash(current),
        "test",
        "op-store-down",
    )
    with pytest.raises(WatchdogError, match="INTERVENTION_STAGE_FAILED"):
        receiver.intervene(request)
    unchanged = task_reader.get_task("task-1")
    assert unchanged is not None
    assert unchanged.current_state is TaskState.RUNNING
    assert AuditWriter(audit_db_path).export() == ()
