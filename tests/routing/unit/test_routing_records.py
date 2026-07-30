"""PH-4 unit — append-only execution ledger + fallback provenance (CTR-MODEL-EXEC-RECORD)."""

from __future__ import annotations

import pytest

from factory.routing import ExecutionLedger, ExecutionRecord, ExecutionStatus, FallbackRecord
from factory.routing.errors import RoutingError
from factory.routing.records import InMemoryRecordStore


def _rec(
    record_id: str, status: ExecutionStatus = ExecutionStatus.SUCCEEDED, **kw: object
) -> ExecutionRecord:
    fields = dict(
        record_id=record_id,
        task_id="t1",
        stage_id="s1",
        attempt=1,
        route_key="OLLAMA:qwen3:8b",
        fingerprint_digest="d",
        status=status,
        started_at=0,
        reason="ok",
    )
    fields.update(kw)
    return ExecutionRecord(**fields)  # type: ignore[arg-type]


def test_store_is_append_only_and_rejects_duplicate_ids() -> None:
    store = InMemoryRecordStore()
    store.append(_rec("exec-1"))
    with pytest.raises(RoutingError) as exc:
        store.append(_rec("exec-1"))
    assert exc.value.code == "RECORD_DUPLICATE"
    assert len(store.all()) == 1


def test_seeded_store_appends_in_order() -> None:
    store = InMemoryRecordStore(seed=[_rec("exec-1"), _rec("exec-2")])
    assert [r.record_id for r in store.all()] == ["exec-1", "exec-2"]


def test_ledger_record_and_queries() -> None:
    ledger = ExecutionLedger()
    ledger.record(_rec("exec-1"))
    ledger.record(_rec("exec-2", stage_id="s2"))
    assert ledger.get("exec-1") is not None
    assert ledger.get("missing") is None
    assert len(ledger.for_task("t1")) == 2
    assert ledger.latest_for_stage("t1", "s1").record_id == "exec-1"  # type: ignore[union-attr]
    assert ledger.latest_for_stage("t1", "s9") is None


def test_next_attempt_increments_per_stage() -> None:
    ledger = ExecutionLedger()
    assert ledger.next_attempt("t1", "s1") == 1
    ledger.record(_rec("exec-1", attempt=1))
    assert ledger.next_attempt("t1", "s1") == 2


def test_supersede_unknown_record_is_rejected() -> None:
    ledger = ExecutionLedger()
    with pytest.raises(RoutingError) as exc:
        ledger.record(_rec("exec-2", supersedes="ghost"))
    assert exc.value.code == "RECORD_SUPERSEDE_UNKNOWN"


def test_register_fallback_requires_both_records() -> None:
    ledger = ExecutionLedger()
    ledger.record(_rec("exec-1", status=ExecutionStatus.FAILED))
    ledger.record(_rec("exec-2", supersedes="exec-1"))
    fb = FallbackRecord("exec-1", "exec-2", "failed", "d1", "d2", ("g",))
    assert ledger.register_fallback(fb) is fb
    assert ledger.fallbacks() == (fb,)


def test_register_fallback_rejects_unknown_endpoints() -> None:
    ledger = ExecutionLedger()
    ledger.record(_rec("exec-1"))
    with pytest.raises(RoutingError) as exc:
        ledger.register_fallback(FallbackRecord("ghost", "exec-1", "r", "d", "d", ()))
    assert exc.value.code == "FALLBACK_FROM_UNKNOWN"
    with pytest.raises(RoutingError) as exc2:
        ledger.register_fallback(FallbackRecord("exec-1", "ghost", "r", "d", "d", ()))
    assert exc2.value.code == "FALLBACK_TO_UNKNOWN"


def test_in_flight_lists_only_running_records() -> None:
    ledger = ExecutionLedger()
    ledger.record(_rec("exec-1", status=ExecutionStatus.RUNNING))
    ledger.record(_rec("exec-2", status=ExecutionStatus.SUCCEEDED))
    assert [r.record_id for r in ledger.in_flight()] == ["exec-1"]
    assert len(ledger.all_records()) == 2
