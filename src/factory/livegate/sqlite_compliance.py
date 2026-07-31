"""SQLite compliance gate (Stage-3 **first mandatory gate**).

This is *detection and verification only*. It reads the linked engine version and confirms the
durable-store guard (:mod:`factory.persistence.sqlite_guard`) fails **closed** when the engine is
below the approved floor and no backport is approved. It never upgrades, installs, or activates a
durable store — remediation is prepared as documentation and left for separate operator
authorization.
"""

from __future__ import annotations

from factory.livegate.models import CheckStatus, ReadinessCheck
from factory.persistence.errors import PersistenceError
from factory.persistence.sqlite_guard import (
    MIN_SQLITE_VERSION,
    assert_sqlite_supported,
    running_sqlite_version,
)

SQLITE_GATE_ID = "sqlite-engine-floor"


def _fmt(version: tuple[int, int, int]) -> str:
    return ".".join(str(p) for p in version)


def evaluate_sqlite_compliance(
    *,
    version: tuple[int, int, int] | None = None,
    minimum: tuple[int, int, int] = MIN_SQLITE_VERSION,
    approved_backports: frozenset[tuple[int, int, int]] = frozenset(),
) -> ReadinessCheck:
    """Return the SQLite readiness finding (mandatory gate).

    ``PASS`` only when the engine is ``>= minimum`` or an approved backport. Below the floor the
    finding is ``FAIL`` **and** the guard is confirmed to reject activation (fail-closed), so the
    durable stores stay inert. This function performs no side effects on the engine or filesystem.
    """
    actual = version if version is not None else running_sqlite_version()
    facts: tuple[tuple[str, str], ...] = (
        ("linked_runtime", _fmt(actual)),
        ("required_floor", _fmt(minimum)),
        ("approved_backports", ",".join(_fmt(b) for b in sorted(approved_backports)) or "(none)"),
    )
    try:
        supported = assert_sqlite_supported(
            version=actual, minimum=minimum, approved_backports=approved_backports
        )
    except PersistenceError as exc:
        # Below the floor: the guard rejected activation. This is the *expected, safe* outcome —
        # durable-store activation fails closed. It remains a blocking gate for live integration.
        return ReadinessCheck(
            check_id=SQLITE_GATE_ID,
            title="SQLite engine meets durable-store floor",
            status=CheckStatus.FAIL,
            detail=(
                f"engine {_fmt(actual)} is below the {_fmt(minimum)} floor and is not an approved "
                f"backport; durable-store activation is refused ({exc.code}). Remediation is "
                "PREPARED_NOT_EXECUTED — see docs/live-gate/05."
            ),
            mandatory=True,
            facts=(*facts, ("fail_closed_verified", "true"), ("guard_error", exc.code)),
        )
    return ReadinessCheck(
        check_id=SQLITE_GATE_ID,
        title="SQLite engine meets durable-store floor",
        status=CheckStatus.PASS,
        detail=f"engine {_fmt(supported)} satisfies the {_fmt(minimum)} floor / approved backport",
        mandatory=True,
        facts=(*facts, ("fail_closed_verified", "n/a")),
    )


def durable_activation_fails_closed_below_floor(
    *, below_floor_version: tuple[int, int, int] = (3, 50, 4)
) -> bool:
    """Verification helper: confirm the guard refuses a below-floor engine with no backport.

    Returns ``True`` when activation is (correctly) refused. Used by the compliance report and its
    tests to assert the durable stores cannot silently come up on an unsupported engine.
    """
    try:
        assert_sqlite_supported(version=below_floor_version, approved_backports=frozenset())
    except PersistenceError:
        return True
    return False
