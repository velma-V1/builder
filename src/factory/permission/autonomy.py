"""Autonomy envelope (Decision A) for CMP-PERM.

The active task's autonomy level selects, per permission class, whether an action may run
automatically (``auto``) or must be presented as an approval card (``requires_card``). Decision B is
absolute and independent of level: **every** ``DELETE`` is ``requires_card`` (no auto-deletion path
exists); external and network effects are likewise never auto. An unknown level fails closed.
"""

from __future__ import annotations

from enum import StrEnum

from factory.permission.models import PermissionClass


class EnvelopeOutcome(StrEnum):
    AUTO = "auto"
    REQUIRES_CARD = "requires_card"


# Named autonomy levels (versioned policy; matches the approval-card autonomy display, 01R Dec A).
LEVEL_MANUAL = "L0-manual"
LEVEL_READ = "L1-read"
LEVEL_SUPERVISED = "L2-supervised"
LEVEL_AUTONOMOUS = "L3-autonomous"

# Per-level auto-permitted classes. DELETE / EXTERNAL / NETWORK are absent from each set
# (Decision B + external/real-world effects are never auto).
_AUTO_CLASSES: dict[str, frozenset[PermissionClass]] = {
    LEVEL_MANUAL: frozenset(),
    LEVEL_READ: frozenset({PermissionClass.READ}),
    LEVEL_SUPERVISED: frozenset(
        {PermissionClass.READ, PermissionClass.WRITE, PermissionClass.EXECUTE}
    ),
    LEVEL_AUTONOMOUS: frozenset(
        {PermissionClass.READ, PermissionClass.WRITE, PermissionClass.EXECUTE}
    ),
}

# Classes that are ALWAYS requires_card regardless of level (Decision B + external effects).
_ALWAYS_CARD: frozenset[PermissionClass] = frozenset(
    {PermissionClass.DELETE, PermissionClass.EXTERNAL, PermissionClass.NETWORK}
)


class AutonomyEnvelope:
    """Pure classifier: (permission class, autonomy level) → auto | requires_card (Decision A/B)."""

    @staticmethod
    def classify(permission_class: PermissionClass, level: str) -> EnvelopeOutcome:
        if permission_class in _ALWAYS_CARD:
            return EnvelopeOutcome.REQUIRES_CARD  # Decision B / external — never auto
        auto = _AUTO_CLASSES.get(level)
        if auto is None:
            return EnvelopeOutcome.REQUIRES_CARD  # unknown level fails closed
        if permission_class in auto:
            return EnvelopeOutcome.AUTO
        return EnvelopeOutcome.REQUIRES_CARD


__all__ = [
    "LEVEL_AUTONOMOUS",
    "LEVEL_MANUAL",
    "LEVEL_READ",
    "LEVEL_SUPERVISED",
    "AutonomyEnvelope",
    "EnvelopeOutcome",
]
