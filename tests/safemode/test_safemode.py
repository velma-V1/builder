"""RPH3-T5 — Diagnostic Safe Mode: no autonomous write, approval+permission-gated repair."""

from __future__ import annotations

import pytest

from factory.approval import (
    ApprovalEngine,
    ApprovalRecord,
    ApprovalRequest,
    DecisionKind,
    OperatorDecision,
    action_fingerprint,
)
from factory.audit import AuditValidator
from factory.permission import (
    ActionRequest,
    PermissionClass,
    PermissionEngine,
    PermissionGrant,
    TaskAuthority,
)
from factory.safemode import (
    AVAILABLE_CAPABILITIES,
    BLOCKED_CAPABILITIES,
    RepairAction,
    SafeMode,
    SafeModeError,
)

pytestmark = pytest.mark.security


def _repair_approval(approval_engine: ApprovalEngine) -> tuple[ApprovalRecord, str]:
    card = approval_engine.enqueue(
        ApprovalRequest(
            task_id="task-1",
            tool="diag",
            action="repair",
            scope="state",
            purpose="fix",
            consequences="repairs state",
            autonomy_level="L2-supervised",
            ttl_seconds=100,
            resource="journal",
            destructive=True,
        )
    )
    record = approval_engine.decide(
        card.approval_id,
        OperatorDecision(decision=DecisionKind.GRANT, operator="op", confirmed_destructive=True),
    )
    assert isinstance(record, ApprovalRecord)
    fingerprint = action_fingerprint(
        task_id="task-1", tool="diag", action="repair", resource="journal", scope="state"
    )
    return record, fingerprint


def _repair_grant(permission_engine: PermissionEngine) -> PermissionGrant:
    authority = TaskAuthority(
        task_id="task-1",
        autonomy_level="L2-supervised",
        allowed_classes=frozenset({PermissionClass.WRITE}),
        project_root="root-x",
    )
    decision = permission_engine.decide(
        ActionRequest(
            task_id="task-1",
            tool="diag",
            action="repair",
            permission_class=PermissionClass.WRITE,
            scope="state",
            purpose="fix",
            resource=None,
        ),
        authority,
    )
    return permission_engine.issue_grant(decision, 100)


def test_enter_declares_capability_scope(safe_mode: SafeMode) -> None:
    session = safe_mode.enter("post-crash integrity check")
    assert session.available_capabilities == AVAILABLE_CAPABILITIES
    assert session.blocked_capabilities == BLOCKED_CAPABILITIES
    assert "approved_repair" in session.available_capabilities
    assert "autonomous_write" in session.blocked_capabilities


def test_inspect_is_read_only(safe_mode: SafeMode) -> None:
    result = safe_mode.inspect("audit_chain")
    assert result.valid is True  # a healthy chain; mutates nothing


def test_export_evidence_is_read_only(
    safe_mode: SafeMode, permission_engine: PermissionEngine
) -> None:
    _repair_grant(permission_engine)  # produce at least one audit record
    export = safe_mode.export_evidence()
    assert export.count >= 1


def test_approved_repair_applies_with_valid_approval_and_permission(
    safe_mode: SafeMode, approval_engine: ApprovalEngine, permission_engine: PermissionEngine
) -> None:
    record, fingerprint = _repair_approval(approval_engine)
    grant = _repair_grant(permission_engine)
    result = safe_mode.approved_repair(
        RepairAction(capability="approved_repair", description="rebuild index", target="journal"),
        record,
        fingerprint,
        grant,
    )
    assert result.applied is True
    assert AuditValidator(database_path=safe_mode.audit_database_path).verify_chain().valid is True


def test_repair_without_valid_approval_denied_no_autonomous_write(
    safe_mode: SafeMode, approval_engine: ApprovalEngine, permission_engine: PermissionEngine
) -> None:
    record, _fingerprint = _repair_approval(approval_engine)
    grant = _repair_grant(permission_engine)
    with pytest.raises(SafeModeError) as exc:
        safe_mode.approved_repair(
            RepairAction(capability="approved_repair", description="x", target="journal"),
            record,
            "wrong-fingerprint",
            grant,
        )
    assert exc.value.code == "SAFEMODE_UNAPPROVED"


def test_repair_without_valid_permission_denied(
    safe_mode: SafeMode, approval_engine: ApprovalEngine, permission_engine: PermissionEngine
) -> None:
    record, fingerprint = _repair_approval(approval_engine)
    grant = _repair_grant(permission_engine)
    permission_engine.revoke(grant.grant_id)  # no valid permission at repair time
    with pytest.raises(SafeModeError) as exc:
        safe_mode.approved_repair(
            RepairAction(capability="approved_repair", description="x", target="journal"),
            record,
            fingerprint,
            grant,
        )
    assert exc.value.code == "SAFEMODE_UNPERMITTED"


def test_out_of_scope_capability_refused(
    safe_mode: SafeMode, approval_engine: ApprovalEngine, permission_engine: PermissionEngine
) -> None:
    record, fingerprint = _repair_approval(approval_engine)
    grant = _repair_grant(permission_engine)
    with pytest.raises(SafeModeError) as exc:
        safe_mode.approved_repair(
            RepairAction(capability="autonomous_write", description="x", target="journal"),
            record,
            fingerprint,
            grant,
        )
    assert exc.value.code == "SAFEMODE_OUT_OF_SCOPE"


def test_safe_mode_error_str() -> None:
    assert str(SafeModeError("C", "m")) == "C: m"


def test_system_clock_shapes() -> None:
    from factory.safemode import SystemClock

    clock = SystemClock()
    assert isinstance(clock.now_ts(), int)
    assert clock.now_iso().endswith("Z")


def test_inspect_detects_tamper(safe_mode: SafeMode, permission_engine: PermissionEngine) -> None:
    import sqlite3

    _repair_grant(permission_engine)  # write an audit record
    tamper = sqlite3.connect(str(safe_mode.audit_database_path))
    tamper.execute("DROP TRIGGER audit_records_no_update")
    tamper.execute("UPDATE audit_records SET actor = 'evil' WHERE sequence = 1")
    tamper.commit()
    tamper.close()
    result = safe_mode.inspect("audit_chain")
    assert result.valid is False  # read-only inspection surfaces the break
