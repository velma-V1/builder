from __future__ import annotations

from pathlib import Path

from factory.permission import (
    ActionRequest,
    DecisionKind,
    PermissionClass,
    PermissionEngine,
    TaskAuthority,
)
from factory.watchdog import CrossLaneOutcome, RPH3CrossLaneBridge


def _authority(project_root: Path) -> TaskAuthority:
    return TaskAuthority(
        task_id="task-1",
        autonomy_level="L2-supervised",
        allowed_classes=frozenset({PermissionClass.READ, PermissionClass.DELETE}),
        project_root=str(project_root),
        allowed_paths=("**",),
    )


def test_real_permission_results_propagate_allow_deny_and_approval_required(
    bridge: RPH3CrossLaneBridge,
    permission_engine: PermissionEngine,
    tmp_path: Path,
) -> None:
    authority = _authority(tmp_path)
    allowed = permission_engine.decide(
        ActionRequest("task-1", "reader", "read", PermissionClass.READ, "repo", "inspect"),
        authority,
    )
    requires = permission_engine.decide(
        ActionRequest("task-1", "fileop", "delete", PermissionClass.DELETE, "repo", "cleanup"),
        authority,
    )
    denied = permission_engine.decide(
        ActionRequest("task-1", "writer", "write", PermissionClass.WRITE, "repo", "modify"),
        authority,
    )
    assert allowed.decision is DecisionKind.ALLOW
    assert requires.decision is DecisionKind.REQUIRES_APPROVAL
    assert denied.decision is DecisionKind.DENY
    assert bridge.from_permission(allowed, "op-perm-allow").outcome is CrossLaneOutcome.HEALTHY
    assert (
        bridge.from_permission(requires, "op-perm-card").outcome
        is CrossLaneOutcome.APPROVAL_REQUIRED
    )
    assert bridge.from_permission(denied, "op-perm-deny").outcome is CrossLaneOutcome.DENIED


def test_duplicate_pure_denial_is_deterministic_and_conflict_fails_closed(
    bridge: RPH3CrossLaneBridge,
    permission_engine: PermissionEngine,
    tmp_path: Path,
) -> None:
    authority = _authority(tmp_path)
    denied = permission_engine.decide(
        ActionRequest("task-1", "writer", "write", PermissionClass.WRITE, "repo", "modify"),
        authority,
    )
    first = bridge.from_permission(denied, "op-conflict")
    assert bridge.from_permission(denied, "op-conflict") == first

    allowed = permission_engine.decide(
        ActionRequest("task-1", "reader", "read", PermissionClass.READ, "repo", "inspect"),
        authority,
    )
    conflict = bridge.from_permission(allowed, "op-conflict")
    assert conflict.outcome is CrossLaneOutcome.FAILED
    assert "conflicting" in conflict.detail
