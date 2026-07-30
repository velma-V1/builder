"""RPH3-T4 unit — audit writer: hash-chain, sequencing, head/export, migration integrity."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from factory.audit import (
    GENESIS_ANCHOR,
    AuditError,
    AuditEvent,
    AuditRecord,
    AuditWriter,
    RecordKind,
    apply_audit_migrations,
)

EventFactory = Callable[..., AuditEvent]


def test_first_record_anchors_to_genesis_and_sequence_one(
    writer: AuditWriter, make_event: EventFactory
) -> None:
    rec = writer.append(make_event("op-1"))
    assert rec.sequence == 1
    assert rec.predecessor_hash == GENESIS_ANCHOR
    assert rec.record_hash == rec.recompute_hash()


def test_sequence_is_prev_plus_one_and_chains(
    writer: AuditWriter, make_event: EventFactory
) -> None:
    a = writer.append(make_event("op-1"))
    b = writer.append(make_event("op-2"))
    c = writer.append(make_event("op-3"))
    assert [a.sequence, b.sequence, c.sequence] == [1, 2, 3]
    # each record's predecessor is the prior record's record_hash
    assert b.predecessor_hash == a.record_hash
    assert c.predecessor_hash == b.record_hash


def test_record_hash_binds_content_and_position(
    writer: AuditWriter, make_event: EventFactory
) -> None:
    rec = writer.append(make_event("op-1", actor="cmp-approval", action_class="destructive"))
    assert rec.record_hash == AuditRecord.compute_hash(
        sequence=rec.sequence,
        op_key=rec.op_key,
        record_kind=rec.record_kind,
        operation_class=rec.operation_class,
        actor=rec.actor,
        action_class=rec.action_class,
        target_ref=rec.target_ref,
        payload_hash=rec.payload_hash,
        occurred_at=rec.occurred_at,
        predecessor_hash=rec.predecessor_hash,
    )


def test_head_and_export(writer: AuditWriter, make_event: EventFactory) -> None:
    assert writer.head() is None
    writer.append(make_event("op-1"))
    writer.append(make_event("op-2"))
    head = writer.head()
    assert head is not None and head.sequence == 2
    exported = writer.export()
    assert [r.sequence for r in exported] == [1, 2]
    assert [r.op_key for r in exported] == ["op-1", "op-2"]
    assert writer.export(start=2) == exported[1:]


def test_class3_intent_then_completion_two_records(
    writer: AuditWriter, make_event: EventFactory
) -> None:
    intent = writer.append(
        make_event("op-c3", record_kind=RecordKind.INTENT, operation_class=3)
    )
    completion = writer.append(
        make_event("op-c3", record_kind=RecordKind.COMPLETION, operation_class=3)
    )
    assert intent.record_kind is RecordKind.INTENT
    assert completion.record_kind is RecordKind.COMPLETION
    # two distinct chained rows for one op_key
    assert completion.predecessor_hash == intent.record_hash
    assert [r.op_key for r in writer.export()] == ["op-c3", "op-c3"]


def test_migration_is_idempotent(
    audit_db_path: Path, audit_migrations_root: Path, make_event: EventFactory
) -> None:
    # applying again is a no-op (version already recorded)
    apply_audit_migrations(audit_db_path, audit_migrations_root)
    writer = AuditWriter(database_path=audit_db_path)
    assert writer.append(make_event("op-1")).sequence == 1


def test_migration_integrity_fails_closed_on_tamper(
    tmp_path: Path, audit_migrations_root: Path
) -> None:
    tampered_root = tmp_path / "m"
    tampered_root.mkdir()
    original = (audit_migrations_root / "0001_audit_chain.sql").read_text()
    (tampered_root / "0001_audit_chain.sql").write_text(original + "\n-- injected\n")
    with pytest.raises(AuditError) as exc:
        apply_audit_migrations(tmp_path / "audit.db", tampered_root)
    assert exc.value.code == "MIGRATION_INTEGRITY"


def test_migration_missing_when_no_sql_files(tmp_path: Path) -> None:
    empty_root = tmp_path / "m"
    empty_root.mkdir()
    with pytest.raises(AuditError) as exc:
        apply_audit_migrations(tmp_path / "audit.db", empty_root)
    assert exc.value.code == "MIGRATION_MISSING"


def test_migration_malformed_filename(tmp_path: Path) -> None:
    root = tmp_path / "m"
    root.mkdir()
    (root / "bad.sql").write_text("SELECT 1;")
    with pytest.raises(AuditError) as exc:
        apply_audit_migrations(tmp_path / "audit.db", root)
    assert exc.value.code == "MIGRATION_MALFORMED"


def test_chain_head_none_on_empty(writer: AuditWriter) -> None:
    assert writer.chain_head() is None


def test_export_range_end(writer: AuditWriter, make_event: EventFactory) -> None:
    for i in range(1, 4):
        writer.append(make_event(f"op-{i}"))
    ranged = writer.export(start=1, end=1)
    assert [r.sequence for r in ranged] == [1]


def test_error_str_format() -> None:
    assert str(AuditError("CODE_X", "message y")) == "CODE_X: message y"
