"""RPH3-T4 failure-path (fault injection) — defensive writer branches that need forced failures.

Covers the mid-apply migration failure and the append retry-exhaustion paths, which cannot occur
under normal operation and are exercised here by injection (mirrors PH-2's REGR-0003 approach).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path

import pytest

from factory.audit import AuditError, AuditEvent, AuditRecord, AuditWriter, apply_audit_migrations
from factory.audit import writer as writer_module

pytestmark = pytest.mark.failure_path

EventFactory = Callable[..., AuditEvent]


def test_migration_apply_failure_is_fail_closed(
    tmp_path: Path, audit_migrations_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(_connection: sqlite3.Connection, _content: bytes) -> None:
        raise sqlite3.OperationalError("injected apply failure")

    monkeypatch.setattr(writer_module, "_apply_single_migration", _boom)
    db = tmp_path / "audit.db"
    with pytest.raises(AuditError) as exc:
        apply_audit_migrations(db, audit_migrations_root)
    assert exc.value.code == "MIGRATION_FAILED"
    # fail-closed: the version row was not recorded (transaction rolled back)
    connection = sqlite3.connect(str(db))
    try:
        rows = connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
        ).fetchone()
    finally:
        connection.close()
    assert rows[0] == 0


def test_append_retry_exhaustion_raises_contended(
    audit_db_path: Path, make_event: EventFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Force every computed record_hash to a constant that already exists → the UNIQUE(record_hash)
    # collision is a non-duplicate integrity error, so the writer retries and eventually gives up.
    const = "c" * 64
    raw = sqlite3.connect(str(audit_db_path))
    try:
        raw.execute(
            "INSERT INTO audit_records (sequence, op_key, record_kind, operation_class, actor, "
            "action_class, payload_hash, occurred_at, predecessor_hash, record_hash) "
            "VALUES (1, 'seed', 'COMPLETION', 1, 'a', 'c', 'p', 't', 'g', ?)",
            (const,),
        )
        raw.commit()
    finally:
        raw.close()

    monkeypatch.setattr(AuditRecord, "compute_hash", staticmethod(lambda **_kwargs: const))
    writer = AuditWriter(database_path=audit_db_path)
    with pytest.raises(AuditError) as exc:
        writer.append(make_event("op-new"))
    assert exc.value.code == "AUDIT_APPEND_CONTENDED"
