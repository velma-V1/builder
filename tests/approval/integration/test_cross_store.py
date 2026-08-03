"""RPH3-T3 integration — XSC-RPH3 Class-1 across the security-spine + audit stores.

Proves the happy path produces exactly one COMMITTED domain record and one COMPLETION audit joined
by ``op_key`` (INV-1), that the intent's ``audit_seq`` matches the audit record, that the chain
stays valid across a full lifecycle, and that replay/duplicate attempts are rejected.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path

from factory.approval import (
    ApprovalEngine,
    ApprovalRecord,
    ApprovalRequest,
    ApprovalState,
    CommitState,
    DecisionKind,
    OperatorDecision,
    action_fingerprint,
)
from factory.audit import AuditValidator, AuditWriter, RecordKind

RequestFactory = Callable[..., ApprovalRequest]


def _committed_intent_rows(security_db_path: Path) -> list[tuple[str, str, int]]:
    connection = sqlite3.connect(str(security_db_path))
    try:
        return [
            (str(r[0]), str(r[1]), int(r[2]))
            for r in connection.execute(
                "SELECT op_key, status, audit_seq FROM approval_intents ORDER BY created_ts"
            )
        ]
    finally:
        connection.close()


def test_class1_happy_path_one_record_one_completion_joined_by_op_key(
    engine: ApprovalEngine,
    audit_db_path: Path,
    security_db_path: Path,
    make_request: RequestFactory,
) -> None:
    card = engine.enqueue(make_request())
    granted = engine.decide(card.approval_id, OperatorDecision(DecisionKind.GRANT, operator="op"))
    assert isinstance(granted, ApprovalRecord)

    # domain record is COMMITTED (authoritative)
    stored = engine.reader.get_record(card.approval_id)
    assert stored is not None and stored.commit_state is CommitState.COMMITTED

    # every intent committed with an audit_seq resolving to a real COMPLETION audit for its op_key
    audit_records = AuditWriter(database_path=audit_db_path).export()
    completions = {r.op_key: r for r in audit_records if r.record_kind is RecordKind.COMPLETION}
    for op_key, status, audit_seq in _committed_intent_rows(security_db_path):
        assert status == "COMMITTED"
        assert op_key in completions  # joined by op_key (INV-1: success only after durable audit)
        assert completions[op_key].sequence == audit_seq

    # exactly one COMPLETION per op_key (no duplicate audit)
    op_keys = [r.op_key for r in audit_records if r.record_kind is RecordKind.COMPLETION]
    assert len(op_keys) == len(set(op_keys))

    # audit chain remains valid end to end
    assert AuditValidator(database_path=audit_db_path).verify_chain().valid is True


def test_full_lifecycle_chain_valid_and_no_pending_intents(
    engine: ApprovalEngine, audit_db_path: Path, make_request: RequestFactory
) -> None:
    card = engine.enqueue(make_request(repetition_limit=2))
    record = engine.decide(card.approval_id, OperatorDecision(DecisionKind.GRANT, operator="op"))
    assert isinstance(record, ApprovalRecord)
    fingerprint = action_fingerprint(
        task_id=record.task_id,
        tool=record.tool,
        action=record.action,
        resource=record.resource,
        scope=record.scope,
    )
    assert engine.consume(record, fingerprint) is True
    assert engine.reader.list_pending_intents() == ()  # all intents committed
    assert AuditValidator(database_path=audit_db_path).verify_chain().valid is True


def test_replayed_consumption_is_rejected(
    engine: ApprovalEngine, make_request: RequestFactory
) -> None:
    card = engine.enqueue(make_request(repetition_limit=1))
    record = engine.decide(card.approval_id, OperatorDecision(DecisionKind.GRANT, operator="op"))
    assert isinstance(record, ApprovalRecord)
    fingerprint = action_fingerprint(
        task_id=record.task_id,
        tool=record.tool,
        action=record.action,
        resource=record.resource,
        scope=record.scope,
    )
    assert engine.consume(record, fingerprint) is True
    # a replay of the same (now-exhausted) record consumes nothing (single-use)
    stale = engine.reader.get_record(card.approval_id)
    assert stale is not None and stale.state is ApprovalState.CONSUMED
    assert engine.consume(stale, fingerprint) is False


def test_op_keys_are_unique_per_operation(
    engine: ApprovalEngine, security_db_path: Path, make_request: RequestFactory
) -> None:
    engine.enqueue(make_request())
    engine.enqueue(make_request())
    connection = sqlite3.connect(str(security_db_path))
    try:
        op_keys = [str(r[0]) for r in connection.execute("SELECT op_key FROM approval_intents")]
    finally:
        connection.close()
    assert len(op_keys) == len(set(op_keys)) == 2  # distinct K per operation instance
