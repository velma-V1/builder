"""RPH3-T4 failure-path — partial-write rollback, concurrency/retry, and tamper detection.

Tamper-evidence (01K §3.2 / 01K-AC-20): local records are not claimed absolutely immutable against
the machine owner. These tests simulate an attacker who bypasses the append-only triggers (by
dropping them) and edits the store directly, then prove CMP-AUDITV DETECTS the break.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path

import pytest

from factory.audit import (
    AuditError,
    AuditEvent,
    AuditRecord,
    AuditValidator,
    AuditWriter,
    BreakClass,
    RecordKind,
)

pytestmark = pytest.mark.failure_path

EventFactory = Callable[..., AuditEvent]


def _seed(writer: AuditWriter, make_event: EventFactory, n: int) -> None:
    for i in range(1, n + 1):
        writer.append(make_event(f"op-{i}"))


def _reforge_actor(connection: sqlite3.Connection, record: AuditRecord, new_actor: str) -> str:
    """Tamper a record's actor AND re-forge its record_hash so it self-verifies (consistent)."""
    new_hash = AuditRecord.compute_hash(
        sequence=record.sequence,
        op_key=record.op_key,
        record_kind=record.record_kind,
        operation_class=record.operation_class,
        actor=new_actor,
        action_class=record.action_class,
        target_ref=record.target_ref,
        payload_hash=record.payload_hash,
        occurred_at=record.occurred_at,
        predecessor_hash=record.predecessor_hash,
    )
    connection.execute(
        "UPDATE audit_records SET actor = ?, record_hash = ? WHERE sequence = ?",
        (new_actor, new_hash, record.sequence),
    )
    connection.commit()
    return new_hash


def _drop_triggers(db_path: Path) -> sqlite3.Connection:
    """Open a writable connection with the append-only triggers dropped (attacker file access)."""
    connection = sqlite3.connect(str(db_path))
    connection.execute("DROP TRIGGER audit_records_no_update")
    connection.execute("DROP TRIGGER audit_records_no_delete")
    connection.commit()
    return connection


# --- partial write / rollback -------------------------------------------------------------------


def test_failed_append_leaves_chain_unchanged(
    writer: AuditWriter, validator: AuditValidator, make_event: EventFactory
) -> None:
    _seed(writer, make_event, 2)
    # a duplicate COMPLETION fails; the transaction must roll back leaving no partial record
    with pytest.raises(AuditError):
        writer.append(make_event("op-1", record_kind=RecordKind.COMPLETION, operation_class=1))
    assert len(writer.export()) == 2
    assert validator.verify_chain().valid is True


def test_append_to_unmigrated_store_fails_closed(tmp_path: Path, make_event: EventFactory) -> None:
    empty = tmp_path / "empty.db"
    sqlite3.connect(str(empty)).close()  # exists but has no audit_records table
    writer = AuditWriter(database_path=empty)
    with pytest.raises(AuditError) as exc:
        writer.append(make_event("op-1"))
    assert exc.value.code == "AUDIT_APPEND_FAILED"


# --- concurrency / duplicate handling -----------------------------------------------------------


def test_sequence_collision_retries_no_fork(
    writer: AuditWriter, audit_db_path: Path, validator: AuditValidator, make_event: EventFactory
) -> None:
    a = writer.append(make_event("op-1"))
    # simulate a concurrent writer grabbing sequence 2 out-of-band (inserts are allowed by triggers)
    raw = sqlite3.connect(str(audit_db_path))
    try:
        raw.execute(
            "INSERT INTO audit_records (sequence, op_key, record_kind, operation_class, actor, "
            "action_class, payload_hash, occurred_at, predecessor_hash, record_hash) "
            "VALUES (2, 'op-x', 'COMPLETION', 1, 'a', 'c', 'p', 't', ?, 'sidehash')",
            (a.record_hash,),
        )
        raw.commit()
    finally:
        raw.close()
    # the writer must retry past the taken sequence and land on 3 (no fork, no gap)
    c = writer.append(make_event("op-2"))
    assert c.sequence == 3
    assert sorted(r.sequence for r in writer.export()) == [1, 2, 3]


# --- tamper detection ---------------------------------------------------------------------------


def test_detects_rewrite(
    writer: AuditWriter, validator: AuditValidator, audit_db_path: Path, make_event: EventFactory
) -> None:
    _seed(writer, make_event, 3)
    connection = _drop_triggers(audit_db_path)
    try:
        connection.execute("UPDATE audit_records SET actor = 'evil' WHERE sequence = 2")
        connection.commit()
    finally:
        connection.close()
    verdict = validator.verify_chain()
    assert verdict.valid is False
    assert AuditValidator.classify_break(verdict) is BreakClass.REWRITE


def test_detects_deletion(
    writer: AuditWriter, validator: AuditValidator, audit_db_path: Path, make_event: EventFactory
) -> None:
    _seed(writer, make_event, 3)
    connection = _drop_triggers(audit_db_path)
    try:
        connection.execute("DELETE FROM audit_records WHERE sequence = 2")
        connection.commit()
    finally:
        connection.close()
    verdict = validator.verify_chain()
    assert verdict.valid is False
    assert AuditValidator.classify_break(verdict) is BreakClass.DELETION


def test_detects_truncation_with_expected_head(
    writer: AuditWriter, validator: AuditValidator, audit_db_path: Path, make_event: EventFactory
) -> None:
    _seed(writer, make_event, 3)
    head = writer.chain_head()
    assert head is not None
    connection = _drop_triggers(audit_db_path)
    try:
        connection.execute("DELETE FROM audit_records WHERE sequence = 3")
        connection.commit()
    finally:
        connection.close()
    verdict = validator.verify_chain(expected_head=head)
    assert verdict.valid is False
    assert AuditValidator.classify_break(verdict) is BreakClass.TRUNCATION


def test_detects_bad_anchor(
    writer: AuditWriter, validator: AuditValidator, audit_db_path: Path, make_event: EventFactory
) -> None:
    _seed(writer, make_event, 2)
    connection = _drop_triggers(audit_db_path)
    try:
        connection.execute(
            "UPDATE audit_records SET predecessor_hash = 'ff' WHERE sequence = 1"
        )
        connection.commit()
    finally:
        connection.close()
    verdict = validator.verify_chain()
    assert verdict.valid is False
    assert AuditValidator.classify_break(verdict) is BreakClass.BAD_ANCHOR


def test_detects_reorder_via_export(
    writer: AuditWriter, validator: AuditValidator, make_event: EventFactory
) -> None:
    _seed(writer, make_event, 3)
    exported = writer.export()
    # physically swap two records (sequence order no longer matches given order)
    reordered = (exported[0], exported[2], exported[1])
    verdict = validator.verify_export(reordered)
    assert verdict.valid is False
    assert AuditValidator.classify_break(verdict) is BreakClass.REORDER


def test_detects_consistent_reforge_of_middle_record(
    writer: AuditWriter, validator: AuditValidator, audit_db_path: Path, make_event: EventFactory
) -> None:
    # Strongest tamper: re-forge a MIDDLE record so it self-verifies (record_hash matches its
    # tampered content). The next record's predecessor_hash no longer chains → linkage break.
    _seed(writer, make_event, 3)
    middle = writer.export()[1]
    connection = _drop_triggers(audit_db_path)
    try:
        _reforge_actor(connection, middle, "evil")
    finally:
        connection.close()
    verdict = validator.verify_chain()
    assert verdict.valid is False
    assert AuditValidator.classify_break(verdict) is BreakClass.REORDER


def test_detects_consistent_reforge_of_head_against_expected(
    writer: AuditWriter, validator: AuditValidator, audit_db_path: Path, make_event: EventFactory
) -> None:
    # Re-forge the HEAD so it self-verifies; only a remembered expected-head catches it (its
    # record_hash differs from the trusted value).
    _seed(writer, make_event, 2)
    expected = writer.chain_head()
    assert expected is not None
    head_record = writer.export()[1]
    connection = _drop_triggers(audit_db_path)
    try:
        _reforge_actor(connection, head_record, "evil")
    finally:
        connection.close()
    verdict = validator.verify_chain(expected_head=expected)
    assert verdict.valid is False
    assert AuditValidator.classify_break(verdict) is BreakClass.REWRITE
