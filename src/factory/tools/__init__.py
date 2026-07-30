"""Roadmap PH-3 Tool Registry + Gateway (CMP-TOOLREG / CMP-TOOLGW, RPH3-T5).

Default-DENY registry of fully-declared, provenance-checked tools; a single no-bypass gateway that
default-denies, revalidates permission (TOCTOU), enforces resource/termination request contracts;
validates untrusted output. RPH3 performs no direct host execution (PH-5 sandbox seam). The writable
connection lives inside a private, un-exported writer; the public surface is the engines + read-only
models + reader.
"""

from __future__ import annotations

from factory.tools.errors import ToolError
from factory.tools.gateway import ToolGateway
from factory.tools.models import (
    Clock,
    CommitState,
    Denial,
    OutputSchema,
    Provenance,
    RegistrationRequest,
    RegistrationVerdict,
    ResourceLimits,
    ResourceVerdict,
    SandboxExecutor,
    ToolCall,
    ToolDeclaration,
    ToolRecord,
    ToolResult,
    ToolState,
    ValidatedOutput,
)
from factory.tools.registry import QUARANTINE_FAILURE_THRESHOLD, SystemClock, ToolRegistry
from factory.tools.store import SQLiteToolReader, apply_tool_migrations, audit_completion_seq

__all__ = [
    "QUARANTINE_FAILURE_THRESHOLD",
    "Clock",
    "CommitState",
    "Denial",
    "OutputSchema",
    "Provenance",
    "RegistrationRequest",
    "RegistrationVerdict",
    "ResourceLimits",
    "ResourceVerdict",
    "SQLiteToolReader",
    "SandboxExecutor",
    "SystemClock",
    "ToolCall",
    "ToolDeclaration",
    "ToolError",
    "ToolGateway",
    "ToolRecord",
    "ToolRegistry",
    "ToolResult",
    "ToolState",
    "ValidatedOutput",
    "apply_tool_migrations",
    "audit_completion_seq",
]
