from __future__ import annotations

from pathlib import Path

from factory.approval import (
    ApprovalEngine,
    ApprovalRecord,
    ApprovalRequest,
    OperatorDecision,
    action_fingerprint,
)
from factory.approval import (
    DecisionKind as ApprovalDecisionKind,
)
from factory.audit import AuditValidator
from factory.fileops import FileOpService
from factory.orchestrator.store.runtime_state import SQLiteOrchestratorStateReader
from factory.permission import (
    ActionRequest,
    PermissionClass,
    PermissionEngine,
    TaskAuthority,
)
from factory.permission import (
    DecisionKind as PermissionDecisionKind,
)
from factory.watchdog import CrossLaneOutcome, RPH3CrossLaneBridge, task_state_hash
from factory.watchdog.models import Clock


def test_full_permission_approval_fileop_audit_watchdog_flow(
    bridge: RPH3CrossLaneBridge,
    permission_engine: PermissionEngine,
    approval_engine: ApprovalEngine,
    databases: tuple[Path, Path, Path],
    task_reader: SQLiteOrchestratorStateReader,
    running_task: str,
    clock: Clock,
    tmp_path: Path,
) -> None:
    target = tmp_path / "old.txt"
    target.write_text("delete me")
    authority = TaskAuthority(
        task_id=running_task,
        autonomy_level="L2-supervised",
        allowed_classes=frozenset({PermissionClass.DELETE}),
        project_root=str(tmp_path),
        allowed_paths=("**",),
    )
    permission = permission_engine.decide(
        ActionRequest(
            running_task,
            "fileop",
            "delete",
            PermissionClass.DELETE,
            "repo",
            "approved cleanup",
            "old.txt",
        ),
        authority,
    )
    assert permission.decision is PermissionDecisionKind.REQUIRES_APPROVAL
    assert (
        bridge.from_permission(permission, "flow-permission").outcome
        is CrossLaneOutcome.APPROVAL_REQUIRED
    )

    card = approval_engine.enqueue(
        ApprovalRequest(
            task_id=running_task,
            tool="fileop",
            action="delete",
            scope="repo",
            purpose="approved cleanup",
            consequences="deletes old.txt",
            autonomy_level="L2-supervised",
            ttl_seconds=100,
            resource="old.txt",
            destructive=True,
        )
    )
    approval = approval_engine.decide(
        card.approval_id,
        OperatorDecision(
            ApprovalDecisionKind.GRANT,
            "operator",
            confirmed_destructive=True,
        ),
    )
    assert isinstance(approval, ApprovalRecord)
    assert bridge.from_approval(approval, "flow-approval").outcome is CrossLaneOutcome.HEALTHY
    fingerprint = action_fingerprint(
        task_id=running_task,
        tool="fileop",
        action="delete",
        resource="old.txt",
        scope="repo",
    )
    deleted = FileOpService(permission_engine, approval_engine, databases[1], clock).delete(
        "old.txt", authority, approval, fingerprint
    )
    assert deleted.deleted
    assert not target.exists()
    assert AuditValidator(databases[1]).verify_chain().valid

    expected = task_state_hash(task_reader.get_task(running_task))
    observed = bridge.audit_health(running_task, expected, "flow-watchdog")
    assert observed.outcome is CrossLaneOutcome.HEALTHY
