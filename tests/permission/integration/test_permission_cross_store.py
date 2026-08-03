"""RPH3-T2 integration — XSC-RPH3 Class-1 across the security-spine + audit stores (permission)."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path

from factory.audit import AuditValidator, AuditWriter, RecordKind
from factory.permission import (
    ActionRequest,
    CommitState,
    DecisionKind,
    PermissionEngine,
    PermissionGrant,
    TaskAuthority,
)

RequestFactory = Callable[..., ActionRequest]
AuthorityFactory = Callable[..., TaskAuthority]


def _committed_intent_rows(security_db_path: Path) -> list[tuple[str, str, int]]:
    connection = sqlite3.connect(str(security_db_path))
    try:
        return [
            (str(r[0]), str(r[1]), int(r[2]))
            for r in connection.execute(
                "SELECT op_key, status, audit_seq FROM permission_intents ORDER BY created_ts"
            )
        ]
    finally:
        connection.close()


def _issue(
    engine: PermissionEngine, make_request: RequestFactory, make_authority: AuthorityFactory
) -> PermissionGrant:
    decision = engine.decide(make_request(), make_authority())
    assert decision.decision is DecisionKind.ALLOW
    return engine.issue_grant(decision, 100)


def test_class1_happy_path_one_grant_one_completion_joined_by_op_key(
    engine: PermissionEngine,
    audit_db_path: Path,
    security_db_path: Path,
    make_request: RequestFactory,
    make_authority: AuthorityFactory,
) -> None:
    grant = _issue(engine, make_request, make_authority)
    stored = engine.reader.get_grant(grant.grant_id)
    assert stored is not None and stored.commit_state is CommitState.COMMITTED

    audit_records = AuditWriter(database_path=audit_db_path).export()
    completions = {r.op_key: r for r in audit_records if r.record_kind is RecordKind.COMPLETION}
    for op_key, status, audit_seq in _committed_intent_rows(security_db_path):
        assert status == "COMMITTED"
        assert op_key in completions  # joined by op_key (INV-1)
        assert completions[op_key].sequence == audit_seq

    op_keys = [r.op_key for r in audit_records if r.record_kind is RecordKind.COMPLETION]
    assert len(op_keys) == len(set(op_keys))  # one COMPLETION per op_key
    assert AuditValidator(database_path=audit_db_path).verify_chain().valid is True


def test_full_lifecycle_chain_valid_no_pending_intents(
    engine: PermissionEngine,
    audit_db_path: Path,
    make_request: RequestFactory,
    make_authority: AuthorityFactory,
) -> None:
    grant = _issue(engine, make_request, make_authority)
    engine.revoke(grant.grant_id)
    assert engine.reader.list_pending_intents() == ()
    assert AuditValidator(database_path=audit_db_path).verify_chain().valid is True


def test_op_keys_unique_per_operation(
    engine: PermissionEngine,
    security_db_path: Path,
    make_request: RequestFactory,
    make_authority: AuthorityFactory,
) -> None:
    _issue(engine, make_request, make_authority)
    _issue(engine, make_request, make_authority)
    connection = sqlite3.connect(str(security_db_path))
    try:
        op_keys = [str(r[0]) for r in connection.execute("SELECT op_key FROM permission_intents")]
    finally:
        connection.close()
    assert len(op_keys) == len(set(op_keys)) == 2
