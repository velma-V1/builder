"""Phase-order enforcement: PH-4 → PH-5 → PH-6 (preinstall preparation).

Live integration must proceed strictly in order and each phase must pass independently before the
next is authorized. This module encodes that ordering and refuses an out-of-order or skip-ahead
request (fail closed). It authorizes nothing by itself — promotion remains a separate operator act.
"""

from __future__ import annotations

from enum import IntEnum


class LivePhase(IntEnum):
    PH4 = 4
    PH5 = 5
    PH6 = 6


_ORDER: tuple[LivePhase, ...] = (LivePhase.PH4, LivePhase.PH5, LivePhase.PH6)


def next_phase(completed: frozenset[LivePhase]) -> LivePhase | None:
    """Return the next phase eligible for authorization, or ``None`` when all are complete.

    A phase is eligible only when **every** earlier phase is complete. Gaps are not skippable.
    """
    for phase in _ORDER:
        if phase in completed:
            continue
        # This is the first incomplete phase; it is eligible only if all earlier ones are complete.
        earlier = _ORDER[: _ORDER.index(phase)]
        if all(e in completed for e in earlier):
            return phase
        return None
    return None


def is_authorization_allowed(
    requested: LivePhase, completed: frozenset[LivePhase]
) -> tuple[bool, str]:
    """Return ``(allowed, reason)`` for authorizing ``requested`` given the completed set."""
    if requested in completed:
        return False, "ALREADY_COMPLETE"
    earlier = _ORDER[: _ORDER.index(requested)]
    missing = [e.name for e in earlier if e not in completed]
    if missing:
        return False, f"BLOCKED_PRIOR_PHASES:{','.join(missing)}"
    return True, "ELIGIBLE"
