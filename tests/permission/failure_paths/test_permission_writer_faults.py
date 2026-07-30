"""RPH3-T2 failure-path — private-writer error handling (stage / commit / rollback fail closed)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from factory.permission import PermissionError, PermissionState, apply_permission_migrations
from factory.permission.writer import _PermissionWriter

pytestmark = pytest.mark.failure_path

SECURITY_MIGRATIONS_ROOT = Path(__file__).resolve().parents[3] / "migrations" / "security"


def test_stage_transition_on_missing_grant_raises(security_db_path: Path) -> None:
    writer = _PermissionWriter(database_path=security_db_path)
    with pytest.raises(PermissionError) as exc:
        writer.stage_transition(
            grant_id="absent", op_key="k", verb="revoke", new_state=PermissionState.REVOKED,
            ts=1_000_000,
        )
    assert exc.value.code == "PERMISSION_NOT_FOUND"


def test_stage_issue_on_broken_store_fails_closed(tmp_path: Path) -> None:
    db = tmp_path / "s.db"
    apply_permission_migrations(db, SECURITY_MIGRATIONS_ROOT)
    broken = sqlite3.connect(str(db))
    broken.execute("DROP TABLE permission_grants")
    broken.commit()
    broken.close()
    writer = _PermissionWriter(database_path=db)
    with pytest.raises(PermissionError) as exc:
        writer.stage_issue(
            grant_id="g", op_key="k", task_id="t", tool="sh", action="w",
            permission_class="WRITE", resource=None, scope="s", purpose="p",  # type: ignore[arg-type]
            grant_fingerprint="fp", expires_at=2, ts=1,
        )
    assert exc.value.code == "PERMISSION_STAGE_FAILED"


def test_commit_on_broken_store_fails_closed(tmp_path: Path) -> None:
    db = tmp_path / "s.db"
    apply_permission_migrations(db, SECURITY_MIGRATIONS_ROOT)
    broken = sqlite3.connect(str(db))
    broken.execute("DROP TABLE permission_grants")
    broken.commit()
    broken.close()
    writer = _PermissionWriter(database_path=db)
    with pytest.raises(PermissionError) as exc:
        writer.commit_operation(grant_id="g", op_key="k", audit_seq=1, ts=1)
    assert exc.value.code == "PERMISSION_COMMIT_FAILED"


def test_rollback_on_broken_store_fails_closed(tmp_path: Path) -> None:
    db = tmp_path / "s.db"
    apply_permission_migrations(db, SECURITY_MIGRATIONS_ROOT)
    broken = sqlite3.connect(str(db))
    broken.execute("DROP TABLE permission_grants")
    broken.commit()
    broken.close()
    writer = _PermissionWriter(database_path=db)
    with pytest.raises(PermissionError) as exc:
        writer.rollback_operation(grant_id="g", op_key="k", verb="issue", failure_code="F", ts=1)
    assert exc.value.code == "PERMISSION_ROLLBACK_FAILED"
