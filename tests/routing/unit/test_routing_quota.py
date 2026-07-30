"""PH-4 unit — quota / usage ledger (fail-closed admission, snapshot/restore)."""

from __future__ import annotations

import pytest

from factory.routing import QuotaLimits, UsageCounters
from factory.routing.errors import RoutingError
from factory.scheduler import QuotaLedger


def _ledger() -> QuotaLedger:
    return QuotaLedger(
        default_limits=QuotaLimits(max_requests=3, max_tokens=100, max_wall_time=50),
        per_scope_limits={"vip": QuotaLimits(max_requests=10, max_tokens=1000, max_wall_time=500)},
    )


def test_charge_accumulates_usage() -> None:
    ledger = _ledger()
    ledger.charge("default", requests=1, tokens=10, wall_time=5)
    ledger.charge("default", requests=1, tokens=20, wall_time=5)
    used = ledger.usage_for("default")
    assert (used.requests, used.tokens, used.wall_time) == (2, 30, 10)


def test_would_exceed_reflects_each_dimension() -> None:
    ledger = _ledger()
    assert ledger.would_exceed("default", requests=4, tokens=0, wall_time=0)
    assert ledger.would_exceed("default", requests=0, tokens=101, wall_time=0)
    assert ledger.would_exceed("default", requests=0, tokens=0, wall_time=51)
    assert not ledger.would_exceed("default", requests=1, tokens=1, wall_time=1)


def test_charge_over_limit_is_refused_without_mutation() -> None:
    ledger = _ledger()
    with pytest.raises(RoutingError) as exc:
        ledger.charge("default", requests=99, tokens=0, wall_time=0)
    assert exc.value.code == "QUOTA_EXCEEDED"
    assert ledger.usage_for("default") == UsageCounters()  # unchanged


def test_negative_charge_rejected() -> None:
    with pytest.raises(RoutingError) as exc:
        _ledger().charge("default", requests=-1, tokens=0, wall_time=0)
    assert exc.value.code == "QUOTA_NEGATIVE"


def test_per_scope_limit_overrides_default() -> None:
    ledger = _ledger()
    assert ledger.limits_for("vip").max_requests == 10
    assert ledger.limits_for("other").max_requests == 3  # falls back to default


def test_remaining_never_negative() -> None:
    ledger = _ledger()
    ledger.charge("default", requests=2, tokens=90, wall_time=10)
    remaining = ledger.remaining("default")
    assert remaining.max_requests == 1
    assert remaining.max_tokens == 10


def test_snapshot_restore_roundtrip() -> None:
    ledger = _ledger()
    ledger.charge("default", requests=1, tokens=5, wall_time=1)
    snap = ledger.snapshot()
    fresh = _ledger()
    fresh.restore(snap)
    assert fresh.usage_for("default").tokens == 5
