from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from factory.audit import AuditWriter
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
from factory.watchdog.models import Clock, InterventionRequest

AUTH_PROOF = "test-watchdog-token"
FORGED_PROOF = "forged-watchdog-token"


class _Gate:
    def __init__(self, allowed: bool) -> None:
        self.allowed = allowed

    def authorize(self, _request: object) -> bool:
        return self.allowed


class _Controller:
    def restart(self, _service_id: str) -> bool:
        raise AssertionError("an invalid request reached the service controller")

    def state(self, service_id: str) -> str:
        return f"{service_id}:running"


def _receiver(
    security_db_path: Path,
    audit_db_path: Path,
    task_reader: SQLiteOrchestratorStateReader,
    task_writer: _OrchestratorStateWriter,
    clock: Clock,
    *,
    allowed: bool = True,
) -> WatchdogInterventionReceiver:
    return WatchdogInterventionReceiver(
        security_db_path,
        audit_db_path,
        task_reader,
        task_writer,
        _Gate(allowed),
        ServiceSupervisor(_Controller()),
        clock,
        supervised_identity="watchdog-1",
        auth_token=AUTH_PROOF,
    )


@pytest.mark.parametrize(
    ("field", "cause"),
    [
        ("auth", "authentication failed"),
        ("wildcard", "bounded target"),
        ("bulk", "bounded target"),
        ("state", "expected-state mismatch"),
    ],
)
def test_invalid_requests_fail_closed_and_are_audited(
    security_db_path: Path,
    audit_db_path: Path,
    task_reader: SQLiteOrchestratorStateReader,
    task_writer: _OrchestratorStateWriter,
    clock: Clock,
    field: str,
    cause: str,
) -> None:
    receiver = _receiver(security_db_path, audit_db_path, task_reader, task_writer, clock)
    control = WatchdogControl("watchdog-1", AUTH_PROOF, clock)
    request = control.request(
        InterventionCommand.RESTART_SERVICE,
        "svc-1",
        receiver.service_state_hash("svc-1"),
        "test",
        f"op-{cause}",
    )
    changed: InterventionRequest
    if field == "auth":
        changed = replace(request, auth_token=FORGED_PROOF)
    elif field == "wildcard":
        changed = replace(request, target_ref="*")
    elif field == "bulk":
        changed = replace(request, target_ref="a,b")
    else:
        changed = replace(request, expected_state="wrong")
    result = receiver.intervene(changed)
    assert result.outcome is InterventionOutcome.REJECTED
    assert cause in result.cause
    assert result.audit_seq is None
    assert any(
        record.op_key == request.idempotency_key for record in AuditWriter(audit_db_path).export()
    )


def test_permission_or_approval_gate_cannot_be_bypassed(
    security_db_path: Path,
    audit_db_path: Path,
    task_reader: SQLiteOrchestratorStateReader,
    task_writer: _OrchestratorStateWriter,
    clock: Clock,
) -> None:
    receiver = _receiver(
        security_db_path, audit_db_path, task_reader, task_writer, clock, allowed=False
    )
    control = WatchdogControl("watchdog-1", AUTH_PROOF, clock)
    result = receiver.intervene(
        control.request(
            InterventionCommand.RESTART_SERVICE,
            "svc-1",
            receiver.service_state_hash("svc-1"),
            "test",
            "op-denied",
        )
    )
    assert result.outcome is InterventionOutcome.REJECTED
    assert "authority gate" in result.cause


def test_forward_bound_commands_are_inert_and_never_execute(
    security_db_path: Path,
    audit_db_path: Path,
    task_reader: SQLiteOrchestratorStateReader,
    task_writer: _OrchestratorStateWriter,
    clock: Clock,
) -> None:
    receiver = _receiver(security_db_path, audit_db_path, task_reader, task_writer, clock)
    control = WatchdogControl("watchdog-1", AUTH_PROOF, clock)
    for command in (
        InterventionCommand.RESTORE_APPROVED_STATE,
        InterventionCommand.ACTIVATE_VERIFIED_SNAPSHOT,
    ):
        result = receiver.intervene(
            control.request(command, "snapshot-1", "inert", "future phase", f"op-{command}")
        )
        assert result.outcome is InterventionOutcome.INERT
        assert result.audit_seq is None

    non_task = receiver.intervene(
        control.request(
            InterventionCommand.QUARANTINE_RESOURCE,
            "worktree-1",
            "inert",
            "future phase",
            "op-non-task-quarantine",
        )
    )
    assert non_task.outcome is InterventionOutcome.INERT


def test_unknown_command_is_default_denied(
    security_db_path: Path,
    audit_db_path: Path,
    task_reader: SQLiteOrchestratorStateReader,
    task_writer: _OrchestratorStateWriter,
    clock: Clock,
) -> None:
    receiver = _receiver(security_db_path, audit_db_path, task_reader, task_writer, clock)
    request = WatchdogControl("watchdog-1", AUTH_PROOF, clock).request(
        InterventionCommand.RESTART_SERVICE,
        "svc-1",
        receiver.service_state_hash("svc-1"),
        "test",
        "op-unknown",
    )
    result = receiver.intervene(replace(request, command="DROP_DATABASE"))
    assert result.outcome is InterventionOutcome.REJECTED
    assert "allowlist" in result.cause


def test_unknown_task_is_rejected_without_authoritative_write(
    security_db_path: Path,
    audit_db_path: Path,
    task_reader: SQLiteOrchestratorStateReader,
    task_writer: _OrchestratorStateWriter,
    clock: Clock,
) -> None:
    receiver = _receiver(security_db_path, audit_db_path, task_reader, task_writer, clock)
    result = receiver.intervene(
        WatchdogControl("watchdog-1", AUTH_PROOF, clock).request(
            InterventionCommand.PAUSE_TASK,
            "missing-task",
            task_state_hash(None),
            "test",
            "op-missing-task",
        )
    )
    assert result.outcome is InterventionOutcome.REJECTED
    assert "does not exist" in result.cause


def test_caller_cannot_expand_the_immutable_allowlist() -> None:
    assert "DROP_DATABASE" not in InterventionCommand.__members__
