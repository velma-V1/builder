"""UI Studio contracts (value types).

UI Studio compiles a requirement into a generation plan and renders it through a **deterministic
fake renderer** — no frontend package is installed, no real build tool runs, no preview server
starts. Every generated artifact is a content-addressed description (:class:`SourceFileRef`), not
literal bundled bytes, so verification is fast and fully offline.

State boundaries are typed, not just documented: :class:`StateOwner` tags every
:class:`StateContract`/:class:`DataContract`, and only ``BACKEND_AUTHORITATIVE`` may claim to own
durable truth — ``XSTATE_WORKFLOW`` legal transitions, ``TANSTACK_QUERY_SNAPSHOT`` backend mirrors,
and ``ZUSTAND_PRESENTATION`` local UI state may never claim that role (enforced in
:mod:`state_contracts`).
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum


class BuildStatus(StrEnum):
    """Never DEPLOYED/LIVE — nothing generated here is installed or activated."""

    NOT_BUILT = "NOT_BUILT"
    DRY_RUN_OK = "DRY_RUN_OK"
    DRY_RUN_FAILED = "DRY_RUN_FAILED"


class RiskSeverity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class PreviewState(StrEnum):
    DRAFT = "DRAFT"
    RENDERING = "RENDERING"
    READY = "READY"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


class StateOwner(StrEnum):
    """Who owns a piece of state. Only BACKEND_AUTHORITATIVE may hold durable truth."""

    XSTATE_WORKFLOW = "XSTATE_WORKFLOW"  # workflows and legal transitions
    TANSTACK_QUERY_SNAPSHOT = "TANSTACK_QUERY_SNAPSHOT"  # backend snapshots and records
    ZUSTAND_PRESENTATION = "ZUSTAND_PRESENTATION"  # presentation-only state
    BACKEND_AUTHORITATIVE = "BACKEND_AUTHORITATIVE"  # all authoritative state


@dataclass(frozen=True, slots=True)
class DesignTokenSet:
    colors: Mapping[str, str] = field(default_factory=dict)
    spacing: Mapping[str, str] = field(default_factory=dict)
    typography: Mapping[str, str] = field(default_factory=dict)
    radii: Mapping[str, str] = field(default_factory=dict)
    motion: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ComponentDescriptor:
    name: str
    library: str  # e.g. "shadcn/ui", "echarts", "react-flow", "maplibre", "deck.gl", "monaco"
    category: str = ""
    requires_props: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PageDescriptor:
    name: str
    route: str
    components: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class WidgetDescriptor:
    name: str
    component: str
    data_contract_ref: str = ""


@dataclass(frozen=True, slots=True)
class TemplateDescriptor:
    template_id: str
    title: str
    description: str
    pages: tuple[str, ...]
    widgets: tuple[str, ...]
    required_components: tuple[str, ...]
    realtime: bool = False


@dataclass(frozen=True, slots=True)
class StateContract:
    """A legal-transition description for one XState workflow. Not a running machine."""

    name: str
    owner: StateOwner
    states: tuple[str, ...]
    events: tuple[str, ...]
    legal_transitions: tuple[tuple[str, str, str], ...]  # (from_state, event, to_state)


@dataclass(frozen=True, slots=True)
class DataContract:
    """A TanStack Query cache contract: a bounded, backend-sourced snapshot — never invented."""

    name: str
    owner: StateOwner
    query_key: tuple[str, ...]
    snapshot_shape: Mapping[str, str] = field(default_factory=dict)
    stale_after_s: int = 30


@dataclass(frozen=True, slots=True)
class RealtimeChannelContract:
    channel: str
    event_types: tuple[str, ...]
    replay_window: int = 500
    supports_snapshot_reconciliation: bool = True
    supports_reconnect_cursor: bool = True


@dataclass(frozen=True, slots=True)
class ProjectManifest:
    project_id: str
    title: str
    template_id: str
    tokens_digest: str
    created_at: int
    compatibility_version: str
    #: Every generated project requires an operator to pin exact frontend dependency versions
    #: before any install — never guessed here.
    requires_operator_pin: bool = True


@dataclass(frozen=True, slots=True)
class SourceFileRef:
    """A content-addressed reference to a generated source file. Bytes live in evidence, not
    here."""

    path: str
    content_digest: str
    purpose: str = ""


@dataclass(frozen=True, slots=True)
class TestInventoryItem:
    kind: str  # "vitest" | "testing-library" | "playwright" | "axe-core"
    name: str
    covers: str = ""


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
class UnresolvedRisk:
    risk_id: str
    severity: RiskSeverity
    detail: str
    mitigation: str = ""
    acknowledged: bool = False


@dataclass(frozen=True, slots=True)
class RollbackRecord:
    previous_project_manifest_ref: str
    rollback_available: bool
    detail: str = ""


@dataclass(frozen=True, slots=True)
class ArtifactPackage:
    """Every generated UI artifact — source, manifest, tokens, inventories, contracts, tests,
    evidence, build status, unresolved risks, and a rollback record, together in one bundle."""

    project_manifest: ProjectManifest
    source_files: tuple[SourceFileRef, ...]
    tokens: DesignTokenSet
    component_inventory: tuple[ComponentDescriptor, ...]
    page_inventory: tuple[PageDescriptor, ...]
    widget_inventory: tuple[WidgetDescriptor, ...]
    state_contracts: tuple[StateContract, ...]
    data_contracts: tuple[DataContract, ...]
    realtime_contracts: tuple[RealtimeChannelContract, ...]
    tests: tuple[TestInventoryItem, ...]
    evidence: EvidenceBundle
    build_status: BuildStatus
    unresolved_risks: tuple[UnresolvedRisk, ...]
    rollback: RollbackRecord


def content_digest(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()
