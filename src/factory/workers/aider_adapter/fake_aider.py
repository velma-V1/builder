"""Deterministic fake Aider coding-worker adapter (preinstallation stand-in for Task 4.2).

Models the bounded coding-worker contract of ``03 §2`` / ``01A §2``: Aider proposes edits and a
collectible package, but it **cannot certify its own work, expand path ownership, self-assign scope,
or change authoritative state**. Every proposed edit path is checked against the task's owned paths
via the tested :class:`~factory.contracts.validation.paths.PathAuthority`; an out-of-scope edit is
refused, not silently applied. ``collect_package`` returns proposed diffs + evidence for the
watchdog/reviewer to judge — never an ``APPROVE``/``COMPLETE`` verdict.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from factory.contracts.validation.paths import PathAuthority
from factory.routing.adapters.base import CallRequest, CallResult
from factory.routing.models import (
    CapabilityReport,
    ExecutionStatus,
    ModelFingerprint,
    Provider,
    RuntimeStatus,
)


@dataclass(frozen=True, slots=True)
class ProposedEdit:
    path: str
    added_lines: int


@dataclass(frozen=True, slots=True)
class WorkerPacket:
    """A collectible, non-authoritative Aider result (no self-certification)."""

    task_id: str
    accepted_edits: tuple[ProposedEdit, ...]
    rejected_paths: tuple[str, ...]
    diff_summary: str
    self_certified: bool = field(default=False)


def _aider_fingerprint(backing_model: str) -> ModelFingerprint:
    return ModelFingerprint(
        family="aider",
        declared_name=f"aider+{backing_model}",
        artifact_digest=f"sha256-fake-aider-{backing_model}",
        quantization="n/a",
        fmt="tool",
        ollama_version="0.0.0-fake",
        runtime_version="aider-fake",
        context_window=8192,
        context_allocation=4096,
        sampling=(("temperature", "0.0"),),
        system_prompt_version="aider-sys-v1",
        tool_schema_version="tools-v1",
        adapter_version="aider-fake-v1",
        routing_policy_version="route-v1",
        gpu_config="none",
    )


class FakeAiderWorker:
    """Bounded coding worker: refuses scope expansion and never self-certifies."""

    __slots__ = ("_available", "_backing_model")

    def __init__(self, available: bool = True, backing_model: str = "qwen3:8b") -> None:
        self._available = available
        self._backing_model = backing_model

    @property
    def provider_name(self) -> str:
        return Provider.AIDER.value

    def probe(self) -> CapabilityReport:
        status = RuntimeStatus.AVAILABLE if self._available else RuntimeStatus.UNAVAILABLE
        reason = "ok" if self._available else "aider worker offline"
        models = ("aider",) if self._available else ()
        return CapabilityReport(Provider.AIDER, status, models, "aider-fake", reason)

    def supports(self, model_id: str) -> bool:
        return self._available and model_id == "aider"

    def call(self, request: CallRequest) -> CallResult:
        if not self._available:
            return CallResult(
                ExecutionStatus.RUNTIME_UNAVAILABLE, "", 0, None, "aider offline",
                "RUNTIME_UNAVAILABLE",
            )
        return CallResult(
            ExecutionStatus.SUCCEEDED,
            f"aider handled {request.task_id}",
            min(request.max_tokens, 16),
            _aider_fingerprint(self._backing_model),
            "ok",
        )

    def cancel(self, task_id: str) -> bool:
        return self._available

    def submit_task(
        self,
        task_id: str,
        project_root: Path,
        owned_paths: Sequence[str],
        requested_edits: Sequence[ProposedEdit],
    ) -> WorkerPacket:
        """Attempt bounded edits. Paths outside ``owned_paths`` are rejected, never applied."""
        authority = PathAuthority(project_root)
        accepted: list[ProposedEdit] = []
        rejected: list[str] = []
        for edit in requested_edits:
            # PathAuthority.evaluate canonicalizes + contains and returns allowed=False for any
            # traversal/escape (it does not raise), so no owned-path escape is ever applied.
            result = authority.evaluate(
                edit.path,
                operation="write",
                allowed=list(owned_paths),
                forbidden=[],
                read_only=[],
                active_exclusive_paths=[],
            )
            if result.allowed:
                accepted.append(edit)
            else:
                rejected.append(edit.path)
        summary = f"{len(accepted)} edit(s) within scope, {len(rejected)} rejected"
        return WorkerPacket(task_id, tuple(accepted), tuple(rejected), summary)

    def collect_package(self, packet: WorkerPacket) -> WorkerPacket:
        """Return the packet unchanged. Structurally cannot set a certified/approved verdict."""
        return packet
