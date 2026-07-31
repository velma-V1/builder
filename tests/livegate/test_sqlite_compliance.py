"""Stage-3 unit — SQLite compliance gate (first mandatory gate; detection + fail-closed only)."""

from __future__ import annotations

import sqlite3

from factory.livegate.models import CheckStatus
from factory.livegate.sqlite_compliance import (
    durable_activation_fails_closed_below_floor,
    evaluate_sqlite_compliance,
)
from factory.persistence.sqlite_guard import MIN_SQLITE_VERSION


def test_below_floor_fails_and_is_mandatory() -> None:
    check = evaluate_sqlite_compliance(version=(3, 50, 4))
    assert check.status is CheckStatus.FAIL
    assert check.mandatory
    assert ("fail_closed_verified", "true") in check.facts


def test_at_floor_passes() -> None:
    check = evaluate_sqlite_compliance(version=MIN_SQLITE_VERSION)
    assert check.status is CheckStatus.PASS


def test_above_floor_passes() -> None:
    assert evaluate_sqlite_compliance(version=(3, 52, 0)).status is CheckStatus.PASS


def test_approved_backport_passes() -> None:
    check = evaluate_sqlite_compliance(
        version=(3, 50, 4), approved_backports=frozenset({(3, 50, 4)})
    )
    assert check.status is CheckStatus.PASS


def test_durable_activation_fails_closed_below_floor() -> None:
    assert durable_activation_fails_closed_below_floor() is True


def test_current_runtime_is_detected_and_recorded() -> None:
    # Detection reflects the real linked engine; on this environment that is 3.50.4 (below floor).
    check = evaluate_sqlite_compliance()
    facts = dict(check.facts)
    assert facts["linked_runtime"] == sqlite3.sqlite_version
