"""Immutable integration-baseline tracking + drift detection (``01D §3.3/§6.10``).

A stage records exactly one immutable integration baseline. A lane cannot silently rebase, merge, or
change its baseline during execution: a baseline change requires a recorded, approved update. Any
mismatch between a lane's observed baseline and the recorded one is drift and blocks integration.
"""

from __future__ import annotations

from factory.workstream.conflict.models import IntegrationBaseline
from factory.workstream.errors import WorkstreamError


class BaselineTracker:
    """Records one immutable baseline per stage and detects silent drift."""

    __slots__ = ("_baselines",)

    def __init__(self) -> None:
        self._baselines: dict[str, IntegrationBaseline] = {}

    def record(self, stage_id: str, commit: str) -> IntegrationBaseline:
        existing = self._baselines.get(stage_id)
        if existing is not None and existing.commit != commit:
            raise WorkstreamError(
                "BASELINE_IMMUTABLE",
                f"stage {stage_id} baseline is {existing.commit}; silent change to {commit} denied",
            )
        baseline = IntegrationBaseline(stage_id, commit)
        self._baselines[stage_id] = baseline
        return baseline

    def baseline(self, stage_id: str) -> IntegrationBaseline | None:
        return self._baselines.get(stage_id)

    def has_drifted(self, stage_id: str, observed_commit: str) -> bool:
        recorded = self._baselines.get(stage_id)
        return recorded is not None and recorded.commit != observed_commit

    def approved_update(self, stage_id: str, new_commit: str) -> IntegrationBaseline:
        """Record an approved baseline change (the only legal way to move a baseline)."""
        baseline = IntegrationBaseline(stage_id, new_commit)
        self._baselines[stage_id] = baseline
        return baseline
