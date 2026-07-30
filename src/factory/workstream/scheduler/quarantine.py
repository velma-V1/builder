"""Normalized-failure counting + three-failure quarantine (``01D §3.7/§6.24-25``).

Equivalent failures are classified by a normalized signature (component, operation, phase, stable
error code, affected resource, probable root cause) — volatile timestamps, worker ids, and retry
numbers are excluded. Three consecutive same-signature failures quarantine the workstream. A
materially different cause resets the sequence; verified transient / infrastructure failures do not
advance it.
"""

from __future__ import annotations

from dataclasses import dataclass

_SEP = "|"
QUARANTINE_THRESHOLD = 3


def normalize_signature(
    *, component: str, operation: str, phase: str, error_code: str, resource: str, root_cause: str
) -> str:
    """Deterministic equivalent-failure signature (excludes volatile fields)."""
    return _SEP.join([component, operation, phase, error_code, resource, root_cause])


@dataclass
class _State:
    signature: str
    count: int


class FailureCounter:
    """Per-workstream consecutive equivalent-failure counter with quarantine."""

    __slots__ = ("_quarantined", "_state")

    def __init__(self) -> None:
        self._state: dict[str, _State] = {}
        self._quarantined: set[str] = set()

    def record(self, workstream_id: str, signature: str, *, transient: bool = False) -> bool:
        """Record a failure. Returns True iff the workstream is now quarantined."""
        if transient:
            # Excluded from the equivalent-failure sequence (does not advance or reset it).
            return workstream_id in self._quarantined
        state = self._state.get(workstream_id)
        if state is None or state.signature != signature:
            self._state[workstream_id] = _State(signature, 1)
        else:
            state.count += 1
            if state.count >= QUARANTINE_THRESHOLD:
                self._quarantined.add(workstream_id)
        return workstream_id in self._quarantined

    def count(self, workstream_id: str) -> int:
        state = self._state.get(workstream_id)
        return state.count if state is not None else 0

    def is_quarantined(self, workstream_id: str) -> bool:
        return workstream_id in self._quarantined

    def reset(self, workstream_id: str) -> None:
        """Reset on deterministic evidence of a materially different cause."""
        self._state.pop(workstream_id, None)
        self._quarantined.discard(workstream_id)
