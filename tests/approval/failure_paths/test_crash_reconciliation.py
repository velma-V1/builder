"""RPH3-T3 failure-path — XSC-RPH3 Class-1 crash windows, fail-closed audit, migration faults.

Simulates a crash by staging a mutation (S1+S2) without its completion audit (S3) or commit (S4),
then proves startup reconciliation rolls it forward (audit present) or back (audit absent), and that
an audit-store failure makes every operation fail closed (no non-authoritative authority survives).
"""

from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Callable
from pathlib import Path

import pytest

import factory.approval.store as store_mod
from factory.approval import (
    ApprovalEngine,
    ApprovalError,
    ApprovalRecord,
    ApprovalRequest,
    ApprovalState,
    CommitState,
    DecisionKind,
    OperatorDecision,
    apply_security_migrations,
)
from factory.approval.engine import _new_op_key
from factory.approval.writer import _ApprovalWriter
from factory.audit import AuditEvent, RecordKind

pytestmark = pytest.mark.failure_path

RequestFactory = Callable[..., ApprovalRequest]


class _FixedClock:
    def now_ts(self) -> int:
        return 1_000_000

    def now_iso(self) -> str:
        return "2026-07-26T00:00:00Z"


def _grant(engine: ApprovalEngine, request: ApprovalRequest) -> ApprovalRecord:
    card = engine.enqueue(request)
    record = engine.decide(card.approval_id, OperatorDecision(DecisionKind.GRANT, operator="op"))
    assert isinstance(record, ApprovalRecord)
    return record


# --- Class-1 crash windows -----------------------------------------------------------------------


def test_crash_before_audit_rolls_enqueue_back(
    engine: ApprovalEngine, make_request: RequestFactory
) -> None:
    # S1+S2 staged, then "crash" (no S3 audit, no S4 commit).
    op_key = _new_op_key("enqueue", "apr-crash")
    engine._writer.stage_enqueue(
        approval_id="apr-crash", op_key=op_key, task_id="t", tool="sh", action="w", resource=None,
        scope="r", purpose="p", consequences="c", autonomy_level="L2", repetition_limit=1,
        requires_confirmation=False, expires_at=2_000_000, ts=1_000_000,
    )
    staged = engine.reader.get_record("apr-crash")
    assert staged is not None and staged.commit_state is CommitState.PENDING
    engine.reconcile_startup()
    assert engine.reader.get_record("apr-crash") is None  # never authoritative → deleted


def test_crash_after_audit_rolls_enqueue_forward(
    engine: ApprovalEngine, make_request: RequestFactory
) -> None:
    op_key = _new_op_key("enqueue", "apr-fwd")
    engine._writer.stage_enqueue(
        approval_id="apr-fwd", op_key=op_key, task_id="t", tool="sh", action="w", resource=None,
        scope="r", purpose="p", consequences="c", autonomy_level="L2", repetition_limit=1,
        requires_confirmation=False, expires_at=2_000_000, ts=1_000_000,
    )
    # the durable completion audit that S3 wrote before the crash
    engine._audit.append(
        AuditEvent(
            op_key=op_key, record_kind=RecordKind.COMPLETION, operation_class=1, actor="a",
            action_class="approval.enqueue", payload_hash="ph", occurred_at="t",
        )
    )
    engine.reconcile_startup()
    forwarded = engine.reader.get_record("apr-fwd")
    assert forwarded is not None
    assert forwarded.commit_state is CommitState.COMMITTED


def test_crash_before_audit_rolls_transition_back_to_prior_state(
    engine: ApprovalEngine, make_request: RequestFactory
) -> None:
    record = _grant(engine, make_request(repetition_limit=2))
    # stage a consume (S1+S2) then "crash" before its audit.
    op_key = _new_op_key("consume", record.approval_id)
    engine._writer.stage_transition(
        approval_id=record.approval_id, op_key=op_key, verb="consume",
        new_state=ApprovalState.GRANTED, ts=1_000_050, increment_use=True,
    )
    mid = engine.reader.get_record(record.approval_id)
    assert mid is not None and mid.commit_state is CommitState.PENDING and mid.uses_consumed == 1
    engine.reconcile_startup()
    restored = engine.reader.get_record(record.approval_id)
    assert restored is not None
    assert restored.commit_state is CommitState.COMMITTED
    assert restored.state is ApprovalState.GRANTED
    assert restored.uses_consumed == 0  # the staged use was undone


def test_reconcile_is_idempotent(
    engine: ApprovalEngine, make_request: RequestFactory
) -> None:
    _grant(engine, make_request())
    engine.reconcile_startup()
    engine.reconcile_startup()  # a second pass over now-terminal intents is a safe no-op
    assert engine.reader.list_pending_intents() == ()


# --- fail-closed on audit failure ----------------------------------------------------------------


def test_enqueue_fails_closed_when_audit_unavailable(
    security_db_path: Path, tmp_path: Path, make_request: RequestFactory
) -> None:
    empty_audit = tmp_path / "empty.db"
    sqlite3.connect(str(empty_audit)).close()  # exists but unmigrated → append fails
    engine = ApprovalEngine(
        security_database_path=security_db_path,
        audit_database_path=empty_audit,
        clock=_FixedClock(),
    )
    with pytest.raises(ApprovalError) as exc:
        engine.enqueue(make_request())
    assert exc.value.code == "APPROVAL_AUDIT_FAILED"
    assert engine.reader.list_committed_pending() == ()  # nothing authoritative survived
    assert engine.reader.queue_ids() == ()


def test_transition_fails_closed_and_restores_prior(
    engine: ApprovalEngine, audit_db_path: Path, make_request: RequestFactory
) -> None:
    card = engine.enqueue(make_request())
    # break the audit store after enqueue so the GRANT's completion audit cannot be written
    broken = sqlite3.connect(str(audit_db_path))
    broken.execute("DROP TABLE audit_records")
    broken.commit()
    broken.close()
    with pytest.raises(ApprovalError) as exc:
        engine.decide(card.approval_id, OperatorDecision(DecisionKind.GRANT, operator="op"))
    assert exc.value.code == "APPROVAL_AUDIT_FAILED"
    restored = engine.reader.get_record(card.approval_id)
    assert restored is not None
    assert restored.state is ApprovalState.PENDING  # grant rolled back to its prior state
    assert restored.commit_state is CommitState.COMMITTED


def test_reconcile_refuses_invalid_audit_chain(
    engine: ApprovalEngine, audit_db_path: Path, make_request: RequestFactory
) -> None:
    engine.enqueue(make_request())
    tamper = sqlite3.connect(str(audit_db_path))
    tamper.execute("DROP TRIGGER audit_records_no_update")
    tamper.execute("UPDATE audit_records SET actor = 'evil' WHERE sequence = 1")
    tamper.commit()
    tamper.close()
    with pytest.raises(ApprovalError) as exc:
        engine.reconcile_startup()
    assert exc.value.code == "APPROVAL_AUDIT_CHAIN_INVALID"


# --- migration fault injection -------------------------------------------------------------------


def test_migration_missing_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(ApprovalError) as exc:
        apply_security_migrations(tmp_path / "x.db", tmp_path / "empty_dir")
    assert exc.value.code == "MIGRATION_MISSING"


def test_migration_malformed_filename_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "m"
    root.mkdir()
    (root / "not_versioned.sql").write_text("SELECT 1;")
    with pytest.raises(ApprovalError) as exc:
        apply_security_migrations(tmp_path / "x.db", root)
    assert exc.value.code == "MIGRATION_MALFORMED"


def test_migration_integrity_mismatch_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "m"
    root.mkdir()
    (root / "0001_security_spine.sql").write_text("CREATE TABLE tampered (x);")  # wrong content
    with pytest.raises(ApprovalError) as exc:
        apply_security_migrations(tmp_path / "x.db", root)
    assert exc.value.code == "MIGRATION_INTEGRITY"


def test_migration_apply_failure_is_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "m"
    root.mkdir()
    bad = root / "0001_bad.sql"
    bad.write_text("CREATE TABLE ok (x);\nTHIS IS NOT SQL;\n")
    # pin the bad file's real hash so integrity passes but the SQL fails mid-apply
    digest = hashlib.sha256(bad.read_bytes()).hexdigest()
    monkeypatch.setattr(store_mod, "_EXPECTED_MIGRATION_HASHES", {"0001_bad.sql": digest})
    with pytest.raises(ApprovalError) as exc:
        apply_security_migrations(tmp_path / "x.db", root)
    assert exc.value.code == "MIGRATION_FAILED"


# --- writer error path ---------------------------------------------------------------------------


def test_stage_on_unmigrated_store_fails_closed(tmp_path: Path) -> None:
    empty = tmp_path / "empty.db"
    sqlite3.connect(str(empty)).close()  # no approval tables
    writer = _ApprovalWriter(database_path=empty)
    with pytest.raises(ApprovalError) as exc:
        writer.stage_enqueue(
            approval_id="a", op_key="k", task_id="t", tool="sh", action="w", resource=None,
            scope="r", purpose="p", consequences="c", autonomy_level="L2", repetition_limit=1,
            requires_confirmation=False, expires_at=2, ts=1,
        )
    assert exc.value.code == "APPROVAL_STAGE_FAILED"
