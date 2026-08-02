from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest

from factory.approval import ApprovalEngine, ApprovalRequest, ApprovalState
from factory.audit import AuditValidator
from factory.orchestrator.store.runtime_state import SQLiteOrchestratorStateReader
from factory.tools import ToolResult, ValidatedOutput
from factory.watchdog import (
    CrossLaneOutcome,
    LaneBSignal,
    LaneBSignalKind,
    RPH3CrossLaneBridge,
    WatchdogError,
    task_state_hash,
)
from factory.watchdog.interventions import WatchdogInterventionReceiver


def test_unbounded_or_wildcard_cross_lane_message_is_rejected(
    bridge: RPH3CrossLaneBridge,
) -> None:
    signal = LaneBSignal(
        LaneBSignalKind.TERMINAL_FAILURE,
        "CMP-PERM",
        "*",
        "state",
        "bad target",
        "op-invalid",
    )
    result = bridge.handle(signal)
    assert result.outcome is CrossLaneOutcome.FAILED
    assert "unbounded" in result.detail


def test_denied_approval_state_and_validated_tool_result_propagate(
    bridge: RPH3CrossLaneBridge,
    approval_engine: ApprovalEngine,
) -> None:
    card = approval_engine.enqueue(
        ApprovalRequest(
            task_id="task-1",
            tool="tool",
            action="act",
            scope="repo",
            purpose="test",
            consequences="none",
            autonomy_level="L2-supervised",
            ttl_seconds=10,
        )
    )
    pending = approval_engine.reader.get_record(card.approval_id)
    assert pending is not None
    denied = replace(pending, state=ApprovalState.DENIED)
    assert bridge.from_approval(denied, "op-approval-denied").outcome is CrossLaneOutcome.DENIED
    tool_result = ToolResult("formatter", "1", ValidatedOutput("text", 2, "ok"))
    assert (
        bridge.from_tool_gateway(tool_result, "task-1", "op-tool-ok").outcome
        is CrossLaneOutcome.HEALTHY
    )


def test_audit_validator_outage_and_missing_task_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    bridge: RPH3CrossLaneBridge,
    task_reader: SQLiteOrchestratorStateReader,
    running_task: str,
) -> None:
    expected = task_state_hash(task_reader.get_task(running_task))

    def unavailable(_validator: AuditValidator) -> object:
        raise OSError("audit store unavailable")

    monkeypatch.setattr(AuditValidator, "verify_chain", unavailable)
    contained = bridge.audit_health(running_task, expected, "op-validator-down")
    assert contained.outcome is CrossLaneOutcome.INTERVENED

    missing = bridge.dependency_failure(
        source="CMP-PERM",
        target_ref="missing-task",
        expected_state=task_state_hash(None),
        detail="store unavailable",
        op_key="op-missing-task",
    )
    assert missing.outcome is CrossLaneOutcome.FAILED
    assert "does not exist" in missing.detail


def test_stale_intervention_and_wir_outage_are_explicit_terminal_results(
    monkeypatch: pytest.MonkeyPatch,
    bridge: RPH3CrossLaneBridge,
    task_reader: SQLiteOrchestratorStateReader,
    running_task: str,
) -> None:
    stale = bridge.dependency_failure(
        source="CMP-PERM",
        target_ref=running_task,
        expected_state="stale-state",
        detail="permission store unavailable",
        op_key="op-stale",
    )
    assert stale.outcome is CrossLaneOutcome.DENIED

    def unavailable(_receiver: WatchdogInterventionReceiver, _request: object) -> object:
        raise WatchdogError("WIR_UNAVAILABLE", "receiver down")

    monkeypatch.setattr(WatchdogInterventionReceiver, "intervene", unavailable)
    expected = task_state_hash(task_reader.get_task(running_task))
    failed = bridge.dependency_failure(
        source="CMP-PERM",
        target_ref=running_task,
        expected_state=expected,
        detail="permission store unavailable",
        op_key="op-wir-down",
    )
    assert failed.outcome is CrossLaneOutcome.FAILED
    assert "WIR_UNAVAILABLE" in failed.detail


def test_concurrent_domain_signals_are_isolated_and_no_bypass_surface_exists(
    bridge: RPH3CrossLaneBridge,
) -> None:
    signals = (
        LaneBSignal(
            LaneBSignalKind.PERMISSION_DENIED,
            "CMP-PERM",
            "task-1",
            "state",
            "denied",
            "op-domain-permission",
        ),
        LaneBSignal(
            LaneBSignalKind.TOOL_GATEWAY_DENIED,
            "CMP-TOOLGW",
            "task-2",
            "state",
            "denied",
            "op-domain-tool",
        ),
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = tuple(pool.map(bridge.handle, signals))
    assert all(result.outcome is CrossLaneOutcome.DENIED for result in results)
    assert {result.target_ref for result in results} == {"task-1", "task-2"}
    assert not hasattr(bridge, "invoke")
    assert not hasattr(bridge, "write")
    assert not hasattr(bridge, "delete")
