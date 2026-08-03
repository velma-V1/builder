"""Immutable read-side models for Phase 3B's worker-run persistence.

Mirrors the shape of ``migrations/runtime/0006_worker_runs.sql``. Distinct from
``factory.integrations.agent_zero.models`` (the untrusted worker-contract types) and from
``factory.orchestrator.models`` (authoritative task state) -- this is Builder's own record of
what a worker run did, for evidence and audit, never itself authoritative task state.

``branch_ref``/``base_sha`` are ``None`` for every run except ``SANDBOXED_EXECUTION`` (only a
real git worktree has a branch/base commit). ``sandbox_path`` is the one field that means "where
this run's output lives on disk, if anywhere": populated for ``SANDBOXED_EXECUTION`` (the
worktree path) *and* for ``STAGED_WRITE`` (the temp staging directory path, since exactly one of
the two ever applies to a given run) -- ``None`` only for ``DIRECT_READ_ONLY``, which never
creates any workspace at all. ``staging_id`` is populated only for ``STAGED_WRITE``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from factory.worker_engine.execution_policy import ExecutionMode


class WorkerRunOutcome(StrEnum):
    """The Worker Engine's own recorded outcome for a run -- distinct from the untrusted
    ``WorkerOutcome`` a worker claims about itself (``factory.integrations.agent_zero.models``)."""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    CRASHED = "CRASHED"


@dataclass(frozen=True, slots=True)
class WorkerRunRecord:
    run_id: str
    task_id: str
    attempt: int
    requested_mode: ExecutionMode
    selected_mode: ExecutionMode
    mode_reason: str
    policy_rule: str
    sandbox_path: str | None
    branch_ref: str | None
    base_sha: str | None
    staging_id: str | None
    work_order_json: str
    model_route_token: str
    started_at: str
    finished_at: str | None
    outcome: WorkerRunOutcome | None
    reason: str | None


@dataclass(frozen=True, slots=True)
class WorkerEventRecord:
    run_id: str
    sequence: int
    event_type: str
    payload_json: str
    occurred_at: str


@dataclass(frozen=True, slots=True)
class WorkerArtifactRecord:
    run_id: str
    artifact_path: str
    content_digest: str
    media_type: str
