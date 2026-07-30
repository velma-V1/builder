"""RPH3-T2 unit — autonomy envelope (Decision A) + Decision B absoluteness."""

from __future__ import annotations

import pytest

from factory.permission import AutonomyEnvelope, EnvelopeOutcome, PermissionClass
from factory.permission.autonomy import (
    LEVEL_AUTONOMOUS,
    LEVEL_MANUAL,
    LEVEL_READ,
    LEVEL_SUPERVISED,
)


@pytest.mark.parametrize(
    ("permission_class", "level", "expected"),
    [
        (PermissionClass.READ, LEVEL_READ, EnvelopeOutcome.AUTO),
        (PermissionClass.WRITE, LEVEL_READ, EnvelopeOutcome.REQUIRES_CARD),
        (PermissionClass.WRITE, LEVEL_SUPERVISED, EnvelopeOutcome.AUTO),
        (PermissionClass.EXECUTE, LEVEL_SUPERVISED, EnvelopeOutcome.AUTO),
        (PermissionClass.READ, LEVEL_MANUAL, EnvelopeOutcome.REQUIRES_CARD),
        # Decision B: DELETE is never auto, at ANY level (including the most autonomous).
        (PermissionClass.DELETE, LEVEL_AUTONOMOUS, EnvelopeOutcome.REQUIRES_CARD),
        (PermissionClass.DELETE, LEVEL_SUPERVISED, EnvelopeOutcome.REQUIRES_CARD),
        # external / network effects are never auto.
        (PermissionClass.EXTERNAL, LEVEL_AUTONOMOUS, EnvelopeOutcome.REQUIRES_CARD),
        (PermissionClass.NETWORK, LEVEL_AUTONOMOUS, EnvelopeOutcome.REQUIRES_CARD),
    ],
)
def test_envelope_classify(
    permission_class: PermissionClass, level: str, expected: EnvelopeOutcome
) -> None:
    assert AutonomyEnvelope.classify(permission_class, level) is expected


def test_unknown_level_fails_closed() -> None:
    assert (
        AutonomyEnvelope.classify(PermissionClass.READ, "L9-unknown")
        is EnvelopeOutcome.REQUIRES_CARD
    )
