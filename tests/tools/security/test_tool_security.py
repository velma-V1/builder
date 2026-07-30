"""RPH3-T5 security — no-bypass default-deny, quarantine, output-failure quarantine, isolation."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path

import pytest

import factory.tools as tools_pkg
from factory.permission import PermissionGrant
from factory.tools import (
    Denial,
    OutputSchema,
    ResourceLimits,
    SQLiteToolReader,
    ToolCall,
    ToolDeclaration,
    ToolGateway,
    ToolRegistry,
)
from factory.tools.writer import _ToolWriter

pytestmark = pytest.mark.security

RegisterTool = Callable[..., ToolDeclaration]
GrantFactory = Callable[..., PermissionGrant]


class _Exec:
    def __init__(self, output: bytes) -> None:
        self.output = output

    def run(self, call: ToolCall, limits: ResourceLimits) -> bytes:
        return self.output


def _call(tool_id: str = "formatter") -> ToolCall:
    return ToolCall(tool_id=tool_id, version="1.0", args=(), task_id="task-1")


def test_no_bypass_unregistered_cannot_execute(
    gateway: ToolGateway, execute_grant: GrantFactory
) -> None:
    # the only call path is invoke(); an unregistered tool is denied (default-deny, 01K-AC-01)
    result = gateway.invoke(_call("ghost"), execute_grant(tool="ghost"), executor=_Exec(b"{}"))
    assert isinstance(result, Denial) and result.reason_code == "TOOL_NOT_REGISTERED"


def test_quarantined_tool_denied_at_gateway(
    gateway: ToolGateway, registry: ToolRegistry, register_tool: RegisterTool,
    execute_grant: GrantFactory,
) -> None:
    register_tool()
    registry.quarantine("formatter", "1.0", "unsafe")
    result = gateway.invoke(_call(), execute_grant(), executor=_Exec(b'{"ok":1}'))
    assert isinstance(result, Denial) and result.reason_code == "TOOL_NOT_REGISTERED"


def test_repeated_output_failure_quarantines_tool(
    gateway: ToolGateway, registry: ToolRegistry, register_tool: RegisterTool,
    execute_grant: GrantFactory,
) -> None:
    register_tool(output_schema=OutputSchema(kind="json", max_bytes=100, required_keys=("ok",)))
    for _ in range(3):
        grant = execute_grant()
        result = gateway.invoke(_call(), grant, executor=_Exec(b'{"bad": 1}'))
        assert isinstance(result, Denial)
    # after the threshold of equivalent output failures the tool is quarantined (uncallable)
    assert registry.lookup("formatter", "1.0") is None


def test_writer_denied_writes_outside_tool_tables(security_db_path: Path) -> None:
    connection = _ToolWriter(database_path=security_db_path)._connect()
    try:
        # the authorizer denies any INSERT to a non-tool table at prepare time
        with pytest.raises(sqlite3.DatabaseError):
            connection.execute("INSERT INTO permission_grants (grant_id) VALUES ('g')")
    finally:
        connection.close()


def test_reader_connection_denies_every_write(security_db_path: Path) -> None:
    connection = SQLiteToolReader(database_path=security_db_path)._connect()
    try:
        with pytest.raises(sqlite3.DatabaseError):
            connection.execute("UPDATE tool_registry SET state = 'X'")
    finally:
        connection.close()


def test_writer_is_not_publicly_exported() -> None:
    assert "_ToolWriter" not in tools_pkg.__all__
    assert not hasattr(tools_pkg, "_ToolWriter")
