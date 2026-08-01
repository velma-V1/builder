"""Agent Zero contracts (value types).

Agent Zero is a **managed external worker**, not an authority. A :class:`WorkOrder` is the entire
grant it receives (assigned work, explicitly granted tools, a bounded path scope, a bounded resource
envelope) — never a provider key, a Docker socket, or unrestricted filesystem access. Its own report
of what happened is captured as ``worker_claimed_outcome`` on :class:`AgentZeroResult`: a claim, not
a verdict. **Worker success is never Builder verification success** — that distinction is structural
here, not just documented: this module defines no "verified"/"approved"/"promoted" field anywhere,
and a worker's attempt to smuggle such a claim through ``worker_self_report`` is inert (see
:mod:`factory.integrations.agent_zero.policy`).
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum


class AgentZeroIntegrationMode(StrEnum):
    """The only mode Agent Zero is integrated in: a managed worker Builder dispatches to."""

    MANAGED_WORKER = "MANAGED_WORKER"


class ModuleHealthState(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


class WorkerOutcome(StrEnum):
    """The worker's own claim about how its run ended. NEVER Builder's verification verdict."""

    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    TIMED_OUT = "TIMED_OUT"
    CANCELLED = "CANCELLED"
    CRASHED = "CRASHED"


class AgentZeroEventType(StrEnum):
    STARTED = "STARTED"
    PROGRESS = "PROGRESS"
    TOOL_CALL = "TOOL_CALL"
    PATCH_PROPOSED = "PATCH_PROPOSED"
    ARTIFACT_PRODUCED = "ARTIFACT_PRODUCED"
    EVIDENCE_ATTACHED = "EVIDENCE_ATTACHED"
    LOG = "LOG"
    HEARTBEAT = "HEARTBEAT"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True, slots=True)
class ResourceEnvelope:
    """Hard, positive resource bounds granted to a single work order (mirrors sandbox limits)."""

    cpu_millis: int
    memory_mb: int
    disk_mb: int
    wall_clock_s: int


@dataclass(frozen=True, slots=True)
class ToolGrant:
    """One explicitly granted tool. Anything not granted is denied (see ``capabilities.py``)."""

    tool_name: str
    scope: str = ""  # e.g. "read_only", "write:src/**" — advisory detail, not the enforcement point


@dataclass(frozen=True, slots=True)
class WorkOrder:
    """The entire grant handed to Agent Zero for one unit of work.

    ``branch_ref`` is never ``"main"``/``"master"`` (enforced by
    :func:`factory.integrations.agent_zero.policy.deny_direct_main_access` at construction time in
    :mod:`task_mapping`). ``allowed_path_globs`` is evaluated through :class:`PathAuthority`, never
    a bespoke check. There is no field here for a provider key, a Docker socket, a merge/approve/
    promote capability, or a schedule — those are structurally absent, not merely unset.
    """

    work_order_id: str
    task_id: str
    workstream_id: str
    branch_ref: str
    instructions: str
    granted_tools: frozenset[str]
    allowed_path_globs: tuple[str, ...]
    resources: ResourceEnvelope
    timeout_s: int
    model_route_token: str = ""  # opaque; redeemed only through ModelRouterPort, never a raw handle


@dataclass(frozen=True, slots=True)
class AgentZeroEvent:
    """One append-only, sequenced event from the worker. Untrusted until validated."""

    work_order_id: str
    sequence: int
    event_type: AgentZeroEventType
    occurred_at: int
    payload: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Patch:
    """A proposed patch. Content lives in ``diff_text``; ``content_digest`` pins it for evidence."""

    target_path: str
    diff_text: str
    content_digest: str


@dataclass(frozen=True, slots=True)
class Artifact:
    """A produced artifact reference. Bytes are not carried here — only a content-addressed
    digest."""

    artifact_path: str
    content_digest: str
    media_type: str = "application/octet-stream"


@dataclass(frozen=True, slots=True)
class EvidenceItem:
    kind: str
    detail: str
    content_digest: str = ""


@dataclass(frozen=True, slots=True)
class EvidenceBundle:
    items: tuple[EvidenceItem, ...] = ()

    @property
    def is_empty(self) -> bool:
        return not self.items


@dataclass(frozen=True, slots=True)
class AgentZeroResult:
    """The typed outcome of one work order. NOT a Builder verification verdict — see module
    docstring.

    ``worker_self_report`` carries whatever free-form claims the worker attached (e.g. a worker
    might claim ``{"verified": "true"}``); those claims are preserved here for audit but are never
    treated as authoritative anywhere in this package — enforced by
    :func:`factory.integrations.agent_zero.policy.assert_no_self_certification` /
    :func:`assert_no_self_promotion`.
    """

    work_order_id: str
    worker_claimed_outcome: WorkerOutcome
    patches: tuple[Patch, ...] = ()
    artifacts: tuple[Artifact, ...] = ()
    evidence: EvidenceBundle = EvidenceBundle()
    reason: str = ""
    worker_self_report: Mapping[str, str] = field(default_factory=dict)
    malformed: bool = False
    incomplete: bool = False


@dataclass(frozen=True, slots=True)
class ModuleHealth:
    state: ModuleHealthState
    detail: str = ""
    checked_at: int = 0


@dataclass(frozen=True, slots=True)
class CompatibilityReport:
    builder_contract_version: str
    worker_reported_version: str
    compatible: bool
    reason: str = ""


def content_digest(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()
