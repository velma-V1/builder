"""The Tool Registry (CMP-TOOLREG, roadmap PH-3 / RPH3-T5).

The one authoritative, **default-DENY** registry: a tool absent here (or quarantined) is uncallable.
``register`` demands a **complete declaration** + **provenance** (source/checksum/license) for
downloads and rejects anything incomplete. ``quarantine``/``release`` are durable (survive restart;
auto-release). Every registration/quarantine/release is a XSC-RPH3 **Class-1** operation audited via
CMP-AUDITW (fail closed on audit failure). Repeated equivalent failure quarantines (01K-AC-18).
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from factory.audit import (
    AuditError,
    AuditEvent,
    AuditRecord,
    AuditValidator,
    AuditWriter,
    RecordKind,
)
from factory.tools.errors import ToolError
from factory.tools.models import (
    Clock,
    CommitState,
    RegistrationRequest,
    RegistrationVerdict,
    ToolDeclaration,
    ToolState,
)
from factory.tools.store import SQLiteToolReader, audit_completion_seq
from factory.tools.writer import _ToolWriter

_SEP = "\x1f"

# Equivalent-failure count at which a tool is auto-quarantined (01K-AC-18).
QUARANTINE_FAILURE_THRESHOLD = 3


class SystemClock:
    def now_ts(self) -> int:
        return int(datetime.now(UTC).timestamp())

    def now_iso(self) -> str:
        return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_op_key(verb: str, subject: str) -> str:
    return hashlib.sha256(f"{verb}{_SEP}{subject}{_SEP}{uuid.uuid4().hex}".encode()).hexdigest()


def _payload_hash(*parts: str) -> str:
    return hashlib.sha256(_SEP.join(parts).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ToolRegistry:
    security_database_path: Path
    audit_database_path: Path
    clock: Clock

    @property
    def _writer(self) -> _ToolWriter:
        return _ToolWriter(database_path=self.security_database_path)

    @property
    def reader(self) -> SQLiteToolReader:
        return SQLiteToolReader(database_path=self.security_database_path)

    @property
    def _audit(self) -> AuditWriter:
        return AuditWriter(database_path=self.audit_database_path)

    @property
    def _validator(self) -> AuditValidator:
        return AuditValidator(database_path=self.audit_database_path)

    def _audit_completion(
        self, *, op_key: str, actor: str, action_class: str, payload_hash: str, target_ref: str
    ) -> AuditRecord:
        return self._audit.append(
            AuditEvent(
                op_key=op_key, record_kind=RecordKind.COMPLETION, operation_class=1, actor=actor,
                action_class=action_class, payload_hash=payload_hash,
                occurred_at=self.clock.now_iso(), target_ref=target_ref,
            )
        )

    # --- register --------------------------------------------------------------------------------

    def register(self, request: RegistrationRequest) -> RegistrationVerdict:
        """Register a tool iff declaration + (download) provenance are complete (fail closed)."""
        declaration = request.declaration
        tool_id, version = declaration.tool_id, declaration.version
        if not declaration.is_complete():
            return RegistrationVerdict(False, "incomplete tool declaration", tool_id, version)
        if request.downloaded and not request.provenance.is_complete():
            return RegistrationVerdict(
                False, "incomplete provenance for a downloaded component", tool_id, version
            )
        if self.reader.get_record(tool_id, version) is not None:
            return RegistrationVerdict(False, "tool@version already registered", tool_id, version)

        ts = self.clock.now_ts()
        op_key = _new_op_key("register", f"{tool_id}@{version}")
        self._writer.stage_register(
            tool_id=tool_id, version=version, op_key=op_key,
            declaration_hash=declaration.canonical_hash(),
            provenance_source=request.provenance.source,
            provenance_checksum=request.provenance.checksum, license=request.provenance.license,
            declaration_json=declaration.to_json(),
            output_schema_json=request.output_schema.to_json(), ts=ts,
        )
        payload = _payload_hash(tool_id, version, declaration.canonical_hash())
        try:
            audit = self._audit_completion(
                op_key=op_key, actor=request.actor, action_class="tool.register",
                payload_hash=payload, target_ref=f"{tool_id}@{version}",
            )
        except AuditError as exc:
            self._writer.rollback_operation(
                tool_id=tool_id, version=version, op_key=op_key, verb="register",
                failure_code="AUDIT_APPEND_FAILED", ts=self.clock.now_ts(),
            )
            raise ToolError(
                "TOOL_AUDIT_FAILED", f"registration failed closed (audit unavailable): {exc}"
            ) from exc
        self._writer.commit_operation(
            tool_id=tool_id, version=version, op_key=op_key, audit_seq=audit.sequence, ts=ts
        )
        return RegistrationVerdict(True, "registered", tool_id, version)

    # --- lookup (default-deny) -------------------------------------------------------------------

    def lookup(self, tool_id: str, version: str) -> ToolDeclaration | None:
        """Return the declaration iff registered, COMMITTED and not quarantined; else None."""
        record = self.reader.get_record(tool_id, version)
        if record is None:
            return None  # default-deny: unregistered ⇒ uncallable
        if record.commit_state is not CommitState.COMMITTED:
            return None  # non-authoritative (in-flight)
        if record.state is ToolState.QUARANTINED:
            return None  # quarantined ⇒ uncallable until released
        return self.reader.get_declaration(tool_id, version)

    def is_registered(self, tool_id: str, version: str) -> bool:
        return self.lookup(tool_id, version) is not None

    # --- quarantine / release --------------------------------------------------------------------

    def quarantine(self, tool_id: str, version: str, reason: str) -> None:
        record = self.reader.get_record(tool_id, version)
        if record is None:
            raise ToolError("TOOL_NOT_FOUND", f"no tool {tool_id}@{version}")
        if record.commit_state is not CommitState.COMMITTED:
            raise ToolError("TOOL_INFLIGHT", f"tool {tool_id}@{version} is not settled")
        if record.state is ToolState.QUARANTINED:
            raise ToolError("TOOL_ALREADY_QUARANTINED", f"tool {tool_id}@{version} already held")
        self._run_transition(
            tool_id=tool_id, version=version, verb="quarantine", new_state=ToolState.QUARANTINED,
            actor="cmp-toolgw", action_class="tool.quarantine", detail=reason,
        )

    def release(self, tool_id: str, version: str, review_ref: str) -> None:
        record = self.reader.get_record(tool_id, version)
        if record is None:
            raise ToolError("TOOL_NOT_FOUND", f"no tool {tool_id}@{version}")
        if record.state is not ToolState.QUARANTINED:
            raise ToolError(
                "TOOL_NOT_QUARANTINED", f"tool {tool_id}@{version} is not quarantined"
            )
        if not review_ref:
            raise ToolError("TOOL_RELEASE_NEEDS_REVIEW", "release requires an explicit review_ref")
        self._run_transition(
            tool_id=tool_id, version=version, verb="release", new_state=ToolState.RELEASED,
            actor="operator", action_class="tool.release", detail=review_ref,
        )

    def record_failure(self, tool_id: str, version: str) -> bool:
        """Count an equivalent failure; quarantine at threshold. True if now quarantined."""
        record = self.reader.get_record(tool_id, version)
        if record is None:
            raise ToolError("TOOL_NOT_FOUND", f"no tool {tool_id}@{version}")
        count = self._writer.increment_failure(
            tool_id=tool_id, version=version, ts=self.clock.now_ts()
        )
        if count >= QUARANTINE_FAILURE_THRESHOLD and record.state is not ToolState.QUARANTINED:
            self.quarantine(tool_id, version, reason=f"repeated equivalent failure (x{count})")
            return True
        return False

    # --- startup reconciliation ------------------------------------------------------------------

    def reconcile_startup(self) -> None:
        verdict = self._validator.verify_chain()
        if not verdict.valid:
            raise ToolError(
                "TOOL_AUDIT_CHAIN_INVALID",
                f"audit chain not authoritative ({verdict.break_class}); refusing roll-forward",
            )
        now = self.clock.now_ts()
        for intent in self.reader.list_pending_intents():
            tool_id, _, version = intent.target_ref.partition(_SEP)
            seq = audit_completion_seq(self.audit_database_path, intent.op_key)
            if seq is not None:
                self._writer.commit_operation(
                    tool_id=tool_id, version=version, op_key=intent.op_key, audit_seq=seq, ts=now
                )
            else:
                self._writer.rollback_operation(
                    tool_id=tool_id, version=version, op_key=intent.op_key, verb=intent.verb,
                    failure_code="RECONCILE_NO_AUDIT", ts=now,
                )

    # --- internals -------------------------------------------------------------------------------

    def _run_transition(
        self, *, tool_id: str, version: str, verb: str, new_state: ToolState, actor: str,
        action_class: str, detail: str | None,
    ) -> None:
        ts = self.clock.now_ts()
        op_key = _new_op_key(verb, f"{tool_id}@{version}")
        self._writer.stage_transition(
            tool_id=tool_id, version=version, op_key=op_key, verb=verb, new_state=new_state,
            ts=ts, detail=detail,
        )
        payload = _payload_hash(tool_id, version, verb, str(new_state))
        try:
            audit = self._audit_completion(
                op_key=op_key, actor=actor, action_class=action_class, payload_hash=payload,
                target_ref=f"{tool_id}@{version}",
            )
        except AuditError as exc:
            self._writer.rollback_operation(
                tool_id=tool_id, version=version, op_key=op_key, verb=verb,
                failure_code="AUDIT_APPEND_FAILED", ts=self.clock.now_ts(),
            )
            raise ToolError(
                "TOOL_AUDIT_FAILED", f"{verb} failed closed (audit unavailable): {exc}"
            ) from exc
        self._writer.commit_operation(
            tool_id=tool_id, version=version, op_key=op_key, audit_seq=audit.sequence, ts=ts
        )


__all__ = ["QUARANTINE_FAILURE_THRESHOLD", "SystemClock", "ToolRegistry"]
