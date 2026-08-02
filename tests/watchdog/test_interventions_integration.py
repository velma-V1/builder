from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

from factory.audit import AuditWriter, RecordKind
from factory.orchestrator.models import TaskState
from factory.orchestrator.store.runtime_state import (
    SQLiteOrchestratorStateReader,
    _OrchestratorStateWriter,
)
from factory.watchdog import (
    InterventionCommand,
    InterventionOutcome,
    ServiceSupervisor,
    WatchdogControl,
    WatchdogInterventionReceiver,
    task_state_hash,
)
from factory.watchdog.models import Clock

AUTH_PROOF = "test-watchdog-token"


class _AllowAuthority:
    def authorize(self, _request: object) -> bool:
        return True


class _Controller:
    def __init__(self) -> None:
        self.restarts = 0

    def restart(self, _service_id: str) -> bool:
        self.restarts += 1
        return True

    def state(self, service_id: str) -> str:
        return f"{service_id}:running"


def _running_task(
    task_writer: _OrchestratorStateWriter,
    task_reader: SQLiteOrchestratorStateReader,
) -> str:
    task_id = "task-1"
    task_writer.create_task(task_id=task_id, project_id="project-1", contract_version=1)
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
    running = task_reader.get_task(task_id)
    assert running is not None
    assert running.current_state is TaskState.RUNNING
    return task_id


def test_pause_is_durable_audited_and_idempotent(
    security_db_path: Path,
    audit_db_path: Path,
    task_writer: _OrchestratorStateWriter,
    task_reader: SQLiteOrchestratorStateReader,
    clock: Clock,
) -> None:
    task_id = _running_task(task_writer, task_reader)
    controller = _Controller()
    receiver = WatchdogInterventionReceiver(
        security_db_path,
        audit_db_path,
        task_reader,
        task_writer,
        _AllowAuthority(),
        ServiceSupervisor(controller),
        clock,
        supervised_identity="watchdog-1",
        auth_token=AUTH_PROOF,
    )
    control = WatchdogControl("watchdog-1", AUTH_PROOF, clock)
    expected = task_state_hash(task_reader.get_task(task_id))
    request = control.request(
        InterventionCommand.PAUSE_TASK, task_id, expected, "event loop stalled", "op-pause-1"
    )
    first = receiver.intervene(request)
    second = receiver.intervene(request)

    assert first.outcome is InterventionOutcome.APPLIED
    assert second == first
    paused = task_reader.get_task(task_id)
    assert paused is not None
    assert paused.current_state is TaskState.PAUSED
    records = AuditWriter(audit_db_path).export()
    assert len(records) == 1
    assert records[0].record_kind is RecordKind.COMPLETION
    assert records[0].operation_class == 2
    assert first.audit_seq == records[0].sequence
    collision = receiver.intervene(replace(request, reason="different request"))
    assert collision.outcome is InterventionOutcome.REJECTED
    assert "idempotency-key collision" in collision.cause


def test_concurrent_duplicate_request_has_one_effect_and_one_audit(
    security_db_path: Path,
    audit_db_path: Path,
    task_writer: _OrchestratorStateWriter,
    task_reader: SQLiteOrchestratorStateReader,
    clock: Clock,
) -> None:
    task_id = _running_task(task_writer, task_reader)
    receiver = WatchdogInterventionReceiver(
        security_db_path,
        audit_db_path,
        task_reader,
        task_writer,
        _AllowAuthority(),
        ServiceSupervisor(_Controller()),
        clock,
        supervised_identity="watchdog-1",
        auth_token=AUTH_PROOF,
    )
    request = WatchdogControl("watchdog-1", AUTH_PROOF, clock).request(
        InterventionCommand.PAUSE_TASK,
        task_id,
        task_state_hash(task_reader.get_task(task_id)),
        "concurrent",
        "op-concurrent",
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = tuple(pool.map(receiver.intervene, (request, request)))
    assert all(result.outcome is InterventionOutcome.APPLIED for result in results)
    assert (
        len(
            [
                record
                for record in AuditWriter(audit_db_path).export()
                if record.op_key == request.idempotency_key
            ]
        )
        == 1
    )


def test_containment_and_service_restart_use_their_real_interfaces(
    security_db_path: Path,
    audit_db_path: Path,
    task_writer: _OrchestratorStateWriter,
    task_reader: SQLiteOrchestratorStateReader,
    clock: Clock,
) -> None:
    task_id = _running_task(task_writer, task_reader)
    controller = _Controller()
    supervisor = ServiceSupervisor(controller)
    receiver = WatchdogInterventionReceiver(
        security_db_path,
        audit_db_path,
        task_reader,
        task_writer,
        _AllowAuthority(),
        supervisor,
        clock,
        supervised_identity="watchdog-1",
        auth_token=AUTH_PROOF,
    )
    control = WatchdogControl("watchdog-1", AUTH_PROOF, clock)
    contained = receiver.intervene(
        control.request(
            InterventionCommand.CONTAIN_TASK,
            task_id,
            task_state_hash(task_reader.get_task(task_id)),
            "integrity risk",
            "op-contain-1",
        )
    )
    restarted = receiver.intervene(
        control.request(
            InterventionCommand.RESTART_SERVICE,
            "svc-1",
            supervisor.state_hash("svc-1"),
            "service stalled",
            "op-restart-1",
        )
    )

    assert contained.outcome is InterventionOutcome.APPLIED
    quarantined = task_reader.get_task(task_id)
    assert quarantined is not None
    assert quarantined.current_state is TaskState.QUARANTINED
    assert restarted.outcome is InterventionOutcome.APPLIED
    assert controller.restarts == 1
    restart_records = [
        record for record in AuditWriter(audit_db_path).export() if record.op_key == "op-restart-1"
    ]
    assert [record.record_kind for record in restart_records] == [
        RecordKind.INTENT,
        RecordKind.COMPLETION,
    ]
