"""Models for the roadmap PH-3 Tool Registry + Gateway (CMP-TOOLREG / CMP-TOOLGW).

CMP-TOOLREG is the one authoritative, **default-DENY** registry: a tool absent is uncallable.
Every registered tool carries a **complete declaration** plus **provenance** (source + integrity
checksum + license) for downloaded components. CMP-TOOLGW is the single call path; it enforces
registry (default-deny) + permission (TOCTOU) + resource/termination **request contracts**, and
treats output as untrusted. Registry rows carry the XSC-RPH3 Class-1 marker (``commit_state``).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol

_SEP = "\x1f"


class ToolState(StrEnum):
    REGISTERED = "REGISTERED"
    QUARANTINED = "QUARANTINED"
    RELEASED = "RELEASED"


class CommitState(StrEnum):
    PENDING = "PENDING"
    COMMITTED = "COMMITTED"


class Clock(Protocol):
    def now_ts(self) -> int: ...
    def now_iso(self) -> str: ...


@dataclass(frozen=True, slots=True)
class ToolDeclaration:
    """A complete tool declaration (01K §2.18-24). Incomplete ⇒ registration rejected."""

    tool_id: str
    version: str
    capabilities: tuple[str, ...]
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    side_effects: tuple[str, ...]
    permission_classes: tuple[str, ...]
    environment: str
    resource_profile: str
    failure_behavior: str

    def is_complete(self) -> bool:
        required_text = (
            self.tool_id,
            self.version,
            self.environment,
            self.resource_profile,
            self.failure_behavior,
        )
        return (
            all(bool(v) for v in required_text)
            and bool(self.capabilities)
            and bool(self.permission_classes)
        )

    def to_json(self) -> str:
        return json.dumps(
            {
                "tool_id": self.tool_id,
                "version": self.version,
                "capabilities": list(self.capabilities),
                "inputs": list(self.inputs),
                "outputs": list(self.outputs),
                "side_effects": list(self.side_effects),
                "permission_classes": list(self.permission_classes),
                "environment": self.environment,
                "resource_profile": self.resource_profile,
                "failure_behavior": self.failure_behavior,
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    @staticmethod
    def from_json(text: str) -> ToolDeclaration:
        d = json.loads(text)
        return ToolDeclaration(
            tool_id=str(d["tool_id"]),
            version=str(d["version"]),
            capabilities=tuple(d["capabilities"]),
            inputs=tuple(d["inputs"]),
            outputs=tuple(d["outputs"]),
            side_effects=tuple(d["side_effects"]),
            permission_classes=tuple(d["permission_classes"]),
            environment=str(d["environment"]),
            resource_profile=str(d["resource_profile"]),
            failure_behavior=str(d["failure_behavior"]),
        )

    def canonical_hash(self) -> str:
        return hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class Provenance:
    """Provenance for a (downloaded) component: source, integrity checksum, license (01K-AC-09)."""

    source: str
    checksum: str
    license: str

    def is_complete(self) -> bool:
        return all(bool(v) for v in (self.source, self.checksum, self.license))


@dataclass(frozen=True, slots=True)
class OutputSchema:
    """The schema tool OUTPUT must satisfy before any consumer sees it (untrusted-until-valid)."""

    kind: str  # "json" | "text"
    max_bytes: int
    required_keys: tuple[str, ...] = ()

    def to_json(self) -> str:
        return json.dumps(
            {
                "kind": self.kind,
                "max_bytes": self.max_bytes,
                "required_keys": list(self.required_keys),
            },
            sort_keys=True,
        )

    @staticmethod
    def from_json(text: str) -> OutputSchema:
        data = json.loads(text)
        return OutputSchema(
            kind=str(data["kind"]),
            max_bytes=int(data["max_bytes"]),
            required_keys=tuple(data.get("required_keys", [])),
        )


@dataclass(frozen=True, slots=True)
class RegistrationVerdict:
    approved: bool
    reason: str
    tool_id: str
    version: str


@dataclass(frozen=True, slots=True)
class ToolRecord:
    tool_id: str
    version: str
    state: ToolState
    commit_state: CommitState
    declaration_hash: str
    provenance_source: str
    provenance_checksum: str
    license: str
    failure_count: int
    created_ts: int
    updated_ts: int


@dataclass(frozen=True, slots=True)
class ResourceLimits:
    """The per-execution resource REQUEST CONTRACT (01K §3.1). Actual OS enforcement is PH-5."""

    wall_clock_s: int
    idle_s: int
    cpu_s: int
    ram_mb: int
    storage_mb: int
    max_processes: int
    max_files: int
    max_output_bytes: int
    max_download_bytes: int


@dataclass(frozen=True, slots=True)
class ResourceVerdict:
    within_limits: bool
    reason: str


@dataclass(frozen=True, slots=True)
class ToolCall:
    tool_id: str
    version: str
    args: tuple[str, ...]
    task_id: str
    requested_limits: ResourceLimits | None = None


@dataclass(frozen=True, slots=True)
class ValidatedOutput:
    kind: str
    size_bytes: int
    payload: str


@dataclass(frozen=True, slots=True)
class ToolResult:
    tool_id: str
    version: str
    output: ValidatedOutput


@dataclass(frozen=True, slots=True)
class Denial:
    reason_code: str
    message: str


class SandboxExecutor(Protocol):
    """A PH-5 sandbox executor seam. RPH3 performs NO direct host execution — without an injected
    executor the gateway fails closed. Returns raw (untrusted) output bytes for a permitted call."""

    def run(self, call: ToolCall, limits: ResourceLimits) -> bytes: ...


@dataclass(frozen=True, slots=True)
class RegistrationRequest:
    declaration: ToolDeclaration
    provenance: Provenance
    output_schema: OutputSchema
    downloaded: bool = True
    actor: str = "cmp-toolreg"
    extra: dict[str, str] = field(default_factory=dict)


__all__ = [
    "Clock",
    "CommitState",
    "Denial",
    "OutputSchema",
    "Provenance",
    "RegistrationRequest",
    "RegistrationVerdict",
    "ResourceLimits",
    "ResourceVerdict",
    "SandboxExecutor",
    "ToolCall",
    "ToolDeclaration",
    "ToolRecord",
    "ToolResult",
    "ToolState",
    "ValidatedOutput",
]
