"""RPH3-T4 security — append-only enforcement, cardinality, Class-3 ordering, forge-resistance.

SEC-RPH3 (audit): the audit chain is append-only + tamper-evident; ``UNIQUE(op_key, record_kind)``
allows one INTENT + one COMPLETION per op while rejecting duplicate lifecycle records; a Class-3
COMPLETION cannot precede its INTENT (01K-AC-19; XSC-RPH3).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path

import pytest

from factory.audit import AuditError, AuditEvent, AuditWriter, RecordKind

pytestmark = pytest.mark.security

EventFactory = Callable[..., AuditEvent]


def test_append_only_trigger_rejects_update(
    writer: AuditWriter, audit_db_path: Path, make_event: EventFactory
) -> None:
    writer.append(make_event("op-1"))
    connection = sqlite3.connect(str(audit_db_path))
    try:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute("UPDATE audit_records SET actor = 'evil'")
    finally:
        connection.close()


def test_append_only_trigger_rejects_delete(
    writer: AuditWriter, audit_db_path: Path, make_event: EventFactory
) -> None:
    writer.append(make_event("op-1"))
    connection = sqlite3.connect(str(audit_db_path))
    try:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute("DELETE FROM audit_records")
    finally:
        connection.close()


@pytest.mark.parametrize(
    "statement",
    [
        "INSERT INTO audit_records (sequence, op_key, record_kind, operation_class, actor, "
        "action_class, payload_hash, occurred_at, predecessor_hash, record_hash) "
        "VALUES (9, 'x', 'COMPLETION', 1, 'a', 'c', 'p', 't', 'h', 'r')",
        "UPDATE audit_records SET actor = 'evil'",
        "DELETE FROM audit_records",
        "DROP TABLE audit_records",
    ],
)
def test_readonly_connection_denies_mutation(
    writer: AuditWriter, audit_db_path: Path, make_event: EventFactory, statement: str
) -> None:
    writer.append(make_event("op-1"))
    connection = sqlite3.connect(f"file:{audit_db_path}?mode=ro", uri=True)
    try:
        with pytest.raises(sqlite3.DatabaseError):
            connection.execute(statement)
    finally:
        connection.close()


def test_duplicate_completion_rejected(
    writer: AuditWriter, make_event: EventFactory
) -> None:
    writer.append(make_event("op-1", record_kind=RecordKind.COMPLETION, operation_class=1))
    with pytest.raises(AuditError) as exc:
        writer.append(make_event("op-1", record_kind=RecordKind.COMPLETION, operation_class=1))
    assert exc.value.code == "AUDIT_DUPLICATE"


def test_second_intent_rejected(writer: AuditWriter, make_event: EventFactory) -> None:
    writer.append(make_event("op-1", record_kind=RecordKind.INTENT, operation_class=3))
    with pytest.raises(AuditError) as exc:
        writer.append(make_event("op-1", record_kind=RecordKind.INTENT, operation_class=3))
    assert exc.value.code == "AUDIT_DUPLICATE"


def test_intent_completion_pair_allowed(writer: AuditWriter, make_event: EventFactory) -> None:
    writer.append(make_event("op-1", record_kind=RecordKind.INTENT, operation_class=3))
    completion = writer.append(
        make_event("op-1", record_kind=RecordKind.COMPLETION, operation_class=3)
    )
    assert completion.sequence == 2


def test_class3_completion_before_intent_rejected(
    writer: AuditWriter, make_event: EventFactory
) -> None:
    with pytest.raises(AuditError) as exc:
        writer.append(make_event("op-1", record_kind=RecordKind.COMPLETION, operation_class=3))
    assert exc.value.code == "AUDIT_COMPLETION_BEFORE_INTENT"


def test_intent_only_valid_for_class3(writer: AuditWriter, make_event: EventFactory) -> None:
    with pytest.raises(AuditError) as exc:
        writer.append(make_event("op-1", record_kind=RecordKind.INTENT, operation_class=1))
    assert exc.value.code == "AUDIT_INTENT_ONLY_CLASS3"


def test_bad_operation_class_rejected(writer: AuditWriter, make_event: EventFactory) -> None:
    with pytest.raises(AuditError) as exc:
        writer.append(make_event("op-1", operation_class=9))
    assert exc.value.code == "AUDIT_BAD_CLASS"


def test_event_carries_no_chain_identity_fields() -> None:
    # forge-resistance: the caller-supplied event has no sequence/predecessor/record_hash fields;
    # the writer computes them, so a caller cannot forge chain position.
    fields = set(AuditEvent.__dataclass_fields__)
    assert {"sequence", "predecessor_hash", "record_hash"}.isdisjoint(fields)
