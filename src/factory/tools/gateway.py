"""The Tool Gateway (CMP-TOOLGW, roadmap PH-3 / RPH3-T5).

The single controlled path to invoke an approved tool. Before any call it confirms the tool is
registered (CMP-TOOLREG, **default-deny**) and permitted (CMP-PERM grant, **revalidated**
at call time — TOCTOU); it applies the resource **request contract** (a limit increase is a
permission change routed to CMP-PERM/APPROVAL); and it treats tool OUTPUT as untrusted, validating
any consumer sees it. **RPH3 performs no direct host execution:** without an injected PH-5 sandbox
executor the gateway fails closed. Actual OS resource/process-tree enforcement is PH-5.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from factory.audit import AuditEvent, AuditWriter, RecordKind
from factory.permission import PermissionEngine, PermissionGrant
from factory.tools.models import (
    Clock,
    Denial,
    OutputSchema,
    ResourceLimits,
    ResourceVerdict,
    SandboxExecutor,
    ToolCall,
    ToolResult,
    ValidatedOutput,
)
from factory.tools.registry import ToolRegistry

_SEP = "\x1f"


class SystemClock:
    def now_ts(self) -> int:
        return int(datetime.now(UTC).timestamp())

    def now_iso(self) -> str:
        return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _within(requested: ResourceLimits, ceiling: ResourceLimits) -> bool:
    return (
        requested.wall_clock_s <= ceiling.wall_clock_s
        and requested.idle_s <= ceiling.idle_s
        and requested.cpu_s <= ceiling.cpu_s
        and requested.ram_mb <= ceiling.ram_mb
        and requested.storage_mb <= ceiling.storage_mb
        and requested.max_processes <= ceiling.max_processes
        and requested.max_files <= ceiling.max_files
        and requested.max_output_bytes <= ceiling.max_output_bytes
        and requested.max_download_bytes <= ceiling.max_download_bytes
    )


@dataclass(frozen=True, slots=True)
class ToolGateway:
    """Single runtime tool-call path (no state, R1). No writable store; audits privileged calls."""

    registry: ToolRegistry
    permission_engine: PermissionEngine
    audit_database_path: Path
    default_limits: ResourceLimits
    clock: Clock

    @property
    def _audit(self) -> AuditWriter:
        return AuditWriter(database_path=self.audit_database_path)

    def enforce_limits(self, requested: ResourceLimits | None) -> ResourceVerdict:
        """Resource REQUEST CONTRACT: within the policy ceiling is admissible; over it is a
        limit increase (a permission change), not silently allowed. OS enforcement is PH-5."""
        if requested is None:
            return ResourceVerdict(True, "within policy ceiling (declared defaults)")
        if _within(requested, self.default_limits):
            return ResourceVerdict(True, "within policy ceiling")
        return ResourceVerdict(False, "requested limits exceed the policy ceiling (limit increase)")

    def validate_output(self, raw: bytes, schema: OutputSchema) -> ValidatedOutput:
        """Tool output is untrusted until validated: size + kind + scope checks (fail closed)."""
        if len(raw) > schema.max_bytes:
            raise _OutputInvalid("output exceeds the declared max size")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise _OutputInvalid("output is not valid UTF-8") from exc
        if schema.kind == "json":
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError as exc:
                raise _OutputInvalid("output is not valid JSON") from exc
            if not isinstance(parsed, dict):
                raise _OutputInvalid("JSON output must be an object")
            missing = [k for k in schema.required_keys if k not in parsed]
            if missing:
                raise _OutputInvalid(f"output missing required keys: {missing}")
        return ValidatedOutput(kind=schema.kind, size_bytes=len(raw), payload=text)

    def terminate_tree(self, executor: SandboxExecutor | None) -> None:
        """Termination REQUEST CONTRACT. Fails closed when no valid sandbox executor exists; actual
        complete process-tree termination is PH-5 (RPH3 performs no direct host execution)."""
        if executor is None:
            raise _NoSandbox("no sandbox executor: cannot terminate (no direct host execution)")

    def invoke(
        self, call: ToolCall, grant: PermissionGrant, *, executor: SandboxExecutor | None = None
    ) -> ToolResult | Denial:
        """Registry + permission + limits + no-direct-exec + output validation, in that order."""
        declaration = self.registry.lookup(call.tool_id, call.version)
        if declaration is None:
            return Denial("TOOL_NOT_REGISTERED", "unregistered or quarantined tool (default-deny)")

        if grant.tool != call.tool_id:
            return Denial("PERMISSION_MISMATCH", "grant is not bound to this tool")
        if not self.permission_engine.revalidate(grant, self.clock.now_ts()):
            return Denial("PERMISSION_DENIED", "no valid permission grant at call time (TOCTOU)")

        verdict = self.enforce_limits(call.requested_limits)
        if not verdict.within_limits:
            # a limit increase is a permission change — never silently granted here
            return Denial("LIMIT_INCREASE_REQUIRES_APPROVAL", verdict.reason)

        if executor is None:
            # RPH3 has no direct host execution path; without a PH-5 sandbox executor, fail closed.
            return Denial("NO_SANDBOX_EXECUTOR", "no sandbox executor (no direct host execution)")

        schema = self.registry.reader.get_output_schema(call.tool_id, call.version)
        if schema is None:  # pragma: no cover - a registered tool always has a schema
            return Denial("TOOL_NOT_REGISTERED", "no output schema for tool")
        limits = call.requested_limits or self.default_limits
        raw = executor.run(call, limits)
        try:
            validated = self.validate_output(raw, schema)
        except _OutputInvalid as exc:
            self.registry.record_failure(call.tool_id, call.version)
            return Denial("OUTPUT_VALIDATION_FAILED", str(exc))

        self._audit_invoke(call, grant)
        return ToolResult(tool_id=call.tool_id, version=call.version, output=validated)

    def _audit_invoke(self, call: ToolCall, grant: PermissionGrant) -> None:
        op_key = hashlib.sha256(
            f"invoke{_SEP}{call.tool_id}@{call.version}{_SEP}{uuid.uuid4().hex}".encode()
        ).hexdigest()
        payload = hashlib.sha256(
            _SEP.join((call.tool_id, call.version, grant.grant_id)).encode()
        ).hexdigest()
        self._audit.append(
            AuditEvent(
                op_key=op_key,
                record_kind=RecordKind.COMPLETION,
                operation_class=1,
                actor="cmp-toolgw",
                action_class="tool.invoke",
                payload_hash=payload,
                occurred_at=self.clock.now_iso(),
                target_ref=f"{call.tool_id}@{call.version}",
            )
        )


class _OutputInvalid(Exception):
    """Internal: tool output failed schema validation (surfaced as a Denial)."""


class _NoSandbox(Exception):
    """Internal: no valid sandbox executor (fail-closed termination request contract)."""


__all__ = ["SystemClock", "ToolGateway"]
