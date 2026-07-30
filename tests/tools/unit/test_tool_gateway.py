"""RPH3-T5 unit — Tool Gateway: no-bypass, default-deny, TOCTOU, limits, output validation."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from factory.permission import PermissionEngine, PermissionGrant
from factory.tools import (
    Denial,
    OutputSchema,
    ResourceLimits,
    ToolCall,
    ToolDeclaration,
    ToolGateway,
    ToolRegistry,
    ToolResult,
)
from factory.tools.gateway import _NoSandbox

RegisterTool = Callable[..., ToolDeclaration]
GrantFactory = Callable[..., PermissionGrant]


class _Exec:
    def __init__(self, output: bytes) -> None:
        self.output = output

    def run(self, call: ToolCall, limits: ResourceLimits) -> bytes:
        return self.output


def _call(**kw: object) -> ToolCall:
    return ToolCall(
        tool_id=str(kw.get("tool_id", "formatter")), version=str(kw.get("version", "1.0")),
        args=(), task_id="task-1",
        requested_limits=kw.get("requested_limits"),  # type: ignore[arg-type]
    )


def test_invoke_happy_path(
    gateway: ToolGateway, register_tool: RegisterTool, execute_grant: GrantFactory
) -> None:
    register_tool()
    result = gateway.invoke(_call(), execute_grant(), executor=_Exec(b'{"ok": true}'))
    assert isinstance(result, ToolResult)
    assert result.output.payload == '{"ok": true}'


def test_no_executor_fails_closed(
    gateway: ToolGateway, register_tool: RegisterTool, execute_grant: GrantFactory
) -> None:
    register_tool()
    result = gateway.invoke(_call(), execute_grant(), executor=None)
    assert isinstance(result, Denial)
    assert result.reason_code == "NO_SANDBOX_EXECUTOR"


def test_unregistered_denied(
    gateway: ToolGateway, execute_grant: GrantFactory
) -> None:
    result = gateway.invoke(_call(tool_id="ghost"), execute_grant(tool="ghost"),
                            executor=_Exec(b"{}"))
    assert isinstance(result, Denial)
    assert result.reason_code == "TOOL_NOT_REGISTERED"


def test_grant_bound_to_other_tool_denied(
    gateway: ToolGateway, register_tool: RegisterTool, execute_grant: GrantFactory
) -> None:
    register_tool()
    result = gateway.invoke(_call(), execute_grant(tool="different"), executor=_Exec(b"{}"))
    assert isinstance(result, Denial)
    assert result.reason_code == "PERMISSION_MISMATCH"


def test_revoked_grant_denied_toctou(
    gateway: ToolGateway, register_tool: RegisterTool, execute_grant: GrantFactory,
    permission_engine: PermissionEngine,
) -> None:
    register_tool()
    grant = execute_grant()
    permission_engine.revoke(grant.grant_id)  # state changes between grant and use
    result = gateway.invoke(_call(), grant, executor=_Exec(b"{}"))
    assert isinstance(result, Denial)
    assert result.reason_code == "PERMISSION_DENIED"


def test_limit_increase_routes_to_approval(
    gateway: ToolGateway, register_tool: RegisterTool, execute_grant: GrantFactory
) -> None:
    register_tool()
    over = ResourceLimits(
        wall_clock_s=99999, idle_s=10, cpu_s=30, ram_mb=512, storage_mb=100,
        max_processes=4, max_files=100, max_output_bytes=4096, max_download_bytes=0,
    )
    result = gateway.invoke(_call(requested_limits=over), execute_grant(), executor=_Exec(b"{}"))
    assert isinstance(result, Denial)
    assert result.reason_code == "LIMIT_INCREASE_REQUIRES_APPROVAL"


def test_output_validation_rejects_oversized(
    gateway: ToolGateway, registry: ToolRegistry, register_tool: RegisterTool,
    execute_grant: GrantFactory,
) -> None:
    register_tool(output_schema=OutputSchema(kind="text", max_bytes=4, required_keys=()))
    result = gateway.invoke(_call(), execute_grant(), executor=_Exec(b"way too long output"))
    assert isinstance(result, Denial)
    assert result.reason_code == "OUTPUT_VALIDATION_FAILED"


def test_output_validation_rejects_missing_keys(
    gateway: ToolGateway, register_tool: RegisterTool, execute_grant: GrantFactory
) -> None:
    register_tool(output_schema=OutputSchema(kind="json", max_bytes=100, required_keys=("ok",)))
    result = gateway.invoke(_call(), execute_grant(), executor=_Exec(b'{"nope": 1}'))
    assert isinstance(result, Denial)
    assert result.reason_code == "OUTPUT_VALIDATION_FAILED"


def test_enforce_limits_within_and_over(gateway: ToolGateway) -> None:
    assert gateway.enforce_limits(None).within_limits is True
    over = ResourceLimits(
        wall_clock_s=1, idle_s=1, cpu_s=1, ram_mb=1, storage_mb=1, max_processes=1, max_files=1,
        max_output_bytes=99999, max_download_bytes=0,
    )
    assert gateway.enforce_limits(over).within_limits is False


def test_terminate_tree_fails_closed_without_executor(gateway: ToolGateway) -> None:
    with pytest.raises(_NoSandbox):
        gateway.terminate_tree(None)
