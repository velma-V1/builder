"""Map a validated Agent Zero event stream into a typed :class:`AgentZeroResult`.

This is interpretation only — it never certifies anything. ``worker_claimed_outcome`` reflects what
the worker's terminal event said happened; ``malformed``/``incomplete`` flag structural problems in
the stream itself. None of this is Builder verification (see :mod:`models` module docstring).
"""

from __future__ import annotations

import re

from factory.integrations.agent_zero.models import (
    AgentZeroEvent,
    AgentZeroEventType,
    AgentZeroResult,
    Artifact,
    EvidenceBundle,
    EvidenceItem,
    Patch,
    WorkerOutcome,
)

_TERMINAL_TYPES = frozenset(
    {AgentZeroEventType.COMPLETED, AgentZeroEventType.FAILED, AgentZeroEventType.CANCELLED}
)
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")

_OUTCOME_FOR_TERMINAL = {
    AgentZeroEventType.COMPLETED: WorkerOutcome.SUCCESS,
    AgentZeroEventType.FAILED: WorkerOutcome.FAILURE,
    AgentZeroEventType.CANCELLED: WorkerOutcome.CANCELLED,
}


def _valid_digest(value: str) -> bool:
    return bool(_DIGEST_RE.match(value))


def map_events_to_result(work_order_id: str, events: tuple[AgentZeroEvent, ...]) -> AgentZeroResult:
    """Interpret an already-sequence-validated event stream. Never trusts a worker's own verdict."""
    terminal = next((e for e in events if e.event_type in _TERMINAL_TYPES), None)
    patches: list[Patch] = []
    artifacts: list[Artifact] = []
    evidence: list[EvidenceItem] = []
    malformed = False

    for e in events:
        if e.event_type is AgentZeroEventType.PATCH_PROPOSED:
            target = e.payload.get("target_path", "")
            digest = e.payload.get("content_digest", "")
            if not target or not _valid_digest(digest):
                malformed = True
                continue
            patches.append(Patch(target, e.payload.get("diff_text", ""), digest))
        elif e.event_type is AgentZeroEventType.ARTIFACT_PRODUCED:
            path = e.payload.get("artifact_path", "")
            digest = e.payload.get("content_digest", "")
            if not path or not _valid_digest(digest):
                malformed = True
                continue
            artifacts.append(
                Artifact(path, digest, e.payload.get("media_type", "application/octet-stream"))
            )
        elif e.event_type is AgentZeroEventType.EVIDENCE_ATTACHED:
            kind = e.payload.get("kind", "")
            if not kind:
                malformed = True
                continue
            evidence.append(
                EvidenceItem(kind, e.payload.get("detail", ""), e.payload.get("content_digest", ""))
            )

    if terminal is None:
        return AgentZeroResult(
            work_order_id=work_order_id,
            worker_claimed_outcome=WorkerOutcome.FAILURE,
            patches=tuple(patches),
            artifacts=tuple(artifacts),
            evidence=EvidenceBundle(tuple(evidence)),
            reason="event stream ended without a terminal event",
            malformed=malformed,
            incomplete=True,
        )

    outcome = _OUTCOME_FOR_TERMINAL[terminal.event_type]
    reason = terminal.payload.get("reason", "")
    incomplete = False
    if outcome is WorkerOutcome.SUCCESS and not patches and not artifacts:
        incomplete = True
        reason = reason or "COMPLETED with no patches or artifacts produced"
    if outcome is WorkerOutcome.SUCCESS and not evidence:
        incomplete = True
        reason = reason or "COMPLETED with no evidence attached"

    return AgentZeroResult(
        work_order_id=work_order_id,
        worker_claimed_outcome=outcome,
        patches=tuple(patches),
        artifacts=tuple(artifacts),
        evidence=EvidenceBundle(tuple(evidence)),
        reason=reason,
        worker_self_report=dict(terminal.payload),
        malformed=malformed,
        incomplete=incomplete,
    )
