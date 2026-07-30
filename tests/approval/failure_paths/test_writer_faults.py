"""RPH3-T3 failure-path — private-writer error handling (stage / commit / rollback fail closed)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from factory.approval import ApprovalError, ApprovalState, apply_security_migrations
from factory.approval.writer import _ApprovalWriter

pytestmark = pytest.mark.failure_path

SECURITY_MIGRATIONS_ROOT = Path(__file__).resolve().parents[3] / "migrations" / "security"


def test_stage_transition_on_missing_record_raises(security_db_path: Path) -> None:
    writer = _ApprovalWriter(database_path=security_db_path)
    with pytest.raises(ApprovalError) as exc:
        writer.stage_transition(
            approval_id="absent", op_key="k", verb="grant", new_state=ApprovalState.GRANTED,
            ts=1_000_000,
        )
    assert exc.value.code == "APPROVAL_NOT_FOUND"


def test_stage_transition_on_broken_store_fails_closed(tmp_path: Path) -> None:
    db = tmp_path / "s.db"
    apply_security_migrations(db, SECURITY_MIGRATIONS_ROOT)
    sqlite3.connect(str(db)).execute("DROP TABLE approval_records")  # break the store
    sqlite3.connect(str(db)).commit()
    broken = sqlite3.connect(str(db))
    broken.execute("DROP TABLE IF EXISTS approval_records")
    broken.commit()
    broken.close()
    writer = _ApprovalWriter(database_path=db)
    with pytest.raises(ApprovalError) as exc:
        writer.stage_transition(
            approval_id="x", op_key="k", verb="grant", new_state=ApprovalState.GRANTED, ts=1,
        )
    assert exc.value.code == "APPROVAL_STAGE_FAILED"


def test_commit_on_broken_store_fails_closed(tmp_path: Path) -> None:
    db = tmp_path / "s.db"
    apply_security_migrations(db, SECURITY_MIGRATIONS_ROOT)
    broken = sqlite3.connect(str(db))
    broken.execute("DROP TABLE approval_records")
    broken.commit()
    broken.close()
    writer = _ApprovalWriter(database_path=db)
    with pytest.raises(ApprovalError) as exc:
        writer.commit_operation(approval_id="x", op_key="k", audit_seq=1, ts=1, drop_queue=False)
    assert exc.value.code == "APPROVAL_COMMIT_FAILED"


def test_rollback_on_broken_store_fails_closed(tmp_path: Path) -> None:
    db = tmp_path / "s.db"
    apply_security_migrations(db, SECURITY_MIGRATIONS_ROOT)
    broken = sqlite3.connect(str(db))
    broken.execute("DROP TABLE approval_records")
    broken.execute("DROP TABLE approval_queue")
    broken.commit()
    broken.close()
    writer = _ApprovalWriter(database_path=db)
    with pytest.raises(ApprovalError) as exc:
        writer.rollback_operation(
            approval_id="x", op_key="k", verb="enqueue", failure_code="F", ts=1,
        )
    assert exc.value.code == "APPROVAL_ROLLBACK_FAILED"
