from __future__ import annotations

from pathlib import Path

import pytest

from factory.approval import ApprovalEngine
from factory.fileops import FileOpError, FileOpService
from factory.permission import (
    ActionRequest,
    PermissionClass,
    PermissionEngine,
    PermissionGrant,
    TaskAuthority,
)
from factory.tools import Denial, ToolCall, ToolGateway
from factory.watchdog import CrossLaneOutcome, RPH3CrossLaneBridge
from factory.watchdog.models import Clock


def _grant(
    permission_engine: PermissionEngine,
    project_root: Path,
    permission_class: PermissionClass,
    tool: str,
    action: str,
) -> tuple[PermissionGrant, TaskAuthority]:
    authority = TaskAuthority(
        task_id="task-1",
        autonomy_level="L2-supervised",
        allowed_classes=frozenset({permission_class}),
        project_root=str(project_root),
        allowed_paths=("**",),
    )
    decision = permission_engine.decide(
        ActionRequest("task-1", tool, action, permission_class, "repo", "integration", None),
        authority,
    )
    return permission_engine.issue_grant(decision, 100), authority


def test_tool_gateway_denial_propagates_without_bypass(
    bridge: RPH3CrossLaneBridge,
    gateway: ToolGateway,
    permission_engine: PermissionEngine,
    tmp_path: Path,
) -> None:
    grant, _authority = _grant(
        permission_engine, tmp_path, PermissionClass.EXECUTE, "missing", "run"
    )
    result = gateway.invoke(ToolCall("missing", "1", (), "task-1"), grant)
    assert isinstance(result, Denial)
    propagated = bridge.from_tool_gateway(result, "task-1", "op-tool-denied")
    assert propagated.outcome is CrossLaneOutcome.DENIED
    assert result.reason_code in propagated.detail


def test_fileop_revoked_permission_propagates_terminal_denial(
    bridge: RPH3CrossLaneBridge,
    permission_engine: PermissionEngine,
    approval_engine: ApprovalEngine,
    databases: tuple[Path, Path, Path],
    clock: Clock,
    tmp_path: Path,
) -> None:
    target = tmp_path / "input.txt"
    target.write_text("safe")
    grant, authority = _grant(permission_engine, tmp_path, PermissionClass.READ, "fileop", "read")
    permission_engine.revoke(grant.grant_id)
    service = FileOpService(permission_engine, approval_engine, databases[1], clock)
    with pytest.raises(FileOpError) as caught:
        service.read("input.txt", authority, grant)
    propagated = bridge.from_fileop(caught.value, "task-1", "op-fileop-denied")
    assert propagated.outcome is CrossLaneOutcome.DENIED
    assert "FILEOP_DENIED" in propagated.detail
