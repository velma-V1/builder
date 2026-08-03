"""RPH3-T2 failure-path — XSC-RPH3 Class-1 crash windows, fail-closed audit, migration faults."""

from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Callable
from pathlib import Path

import pytest

import factory.permission.store as store_mod
from factory.audit import AuditEvent, RecordKind
from factory.permission import (
    ActionRequest,
    CommitState,
    PermissionClass,
    PermissionEngine,
    PermissionError,
    PermissionGrant,
    PermissionState,
    TaskAuthority,
    apply_permission_migrations,
)
from factory.permission.engine import _new_op_key

pytestmark = pytest.mark.failure_path

RequestFactory = Callable[..., ActionRequest]
AuthorityFactory = Callable[..., TaskAuthority]

SECURITY_MIGRATIONS_ROOT = Path(__file__).resolve().parents[3] / "migrations" / "security"


class _FixedClock:
    def now_ts(self) -> int:
        return 1_000_000

    def now_iso(self) -> str:
        return "2026-07-26T00:00:00Z"


def _issue(
    engine: PermissionEngine, make_request: RequestFactory, make_authority: AuthorityFactory
) -> PermissionGrant:
    decision = engine.decide(make_request(), make_authority())
    return engine.issue_grant(decision, 100)


def test_crash_before_audit_rolls_issue_back(
    engine: PermissionEngine, make_request: RequestFactory, make_authority: AuthorityFactory
) -> None:
    op_key = _new_op_key("issue", "grn-crash")
    engine._writer.stage_issue(
        grant_id="grn-crash",
        op_key=op_key,
        task_id="t",
        tool="sh",
        action="w",
        permission_class=PermissionClass.WRITE,
        resource="src/main.py",
        scope="src",
        purpose="p",
        grant_fingerprint="fp",
        expires_at=2_000_000,
        ts=1_000_000,
    )
    staged = engine.reader.get_grant("grn-crash")
    assert staged is not None and staged.commit_state is CommitState.PENDING
    engine.reconcile_startup()
    assert engine.reader.get_grant("grn-crash") is None  # never authoritative → deleted


def test_crash_after_audit_rolls_issue_forward(
    engine: PermissionEngine, make_request: RequestFactory
) -> None:
    op_key = _new_op_key("issue", "grn-fwd")
    engine._writer.stage_issue(
        grant_id="grn-fwd",
        op_key=op_key,
        task_id="t",
        tool="sh",
        action="w",
        permission_class=PermissionClass.WRITE,
        resource="src/main.py",
        scope="src",
        purpose="p",
        grant_fingerprint="fp",
        expires_at=2_000_000,
        ts=1_000_000,
    )
    engine._audit.append(
        AuditEvent(
            op_key=op_key,
            record_kind=RecordKind.COMPLETION,
            operation_class=1,
            actor="a",
            action_class="permission.issue",
            payload_hash="ph",
            occurred_at="t",
        )
    )
    engine.reconcile_startup()
    forwarded = engine.reader.get_grant("grn-fwd")
    assert forwarded is not None and forwarded.commit_state is CommitState.COMMITTED


def test_crash_before_audit_rolls_transition_back(
    engine: PermissionEngine, make_request: RequestFactory, make_authority: AuthorityFactory
) -> None:
    grant = _issue(engine, make_request, make_authority)
    op_key = _new_op_key("revoke", grant.grant_id)
    engine._writer.stage_transition(
        grant_id=grant.grant_id,
        op_key=op_key,
        verb="revoke",
        new_state=PermissionState.REVOKED,
        ts=1_000_050,
    )
    mid = engine.reader.get_grant(grant.grant_id)
    assert mid is not None and mid.commit_state is CommitState.PENDING
    engine.reconcile_startup()
    restored = engine.reader.get_grant(grant.grant_id)
    assert restored is not None
    assert restored.commit_state is CommitState.COMMITTED
    assert restored.state is PermissionState.ACTIVE  # prior state restored (roll back)


def test_reconcile_is_idempotent(
    engine: PermissionEngine, make_request: RequestFactory, make_authority: AuthorityFactory
) -> None:
    _issue(engine, make_request, make_authority)
    engine.reconcile_startup()
    engine.reconcile_startup()
    assert engine.reader.list_pending_intents() == ()


def test_issue_fails_closed_when_audit_unavailable(
    security_db_path: Path,
    tmp_path: Path,
    make_request: RequestFactory,
    make_authority: AuthorityFactory,
) -> None:
    empty_audit = tmp_path / "empty.db"
    sqlite3.connect(str(empty_audit)).close()
    engine = PermissionEngine(
        security_database_path=security_db_path,
        audit_database_path=empty_audit,
        clock=_FixedClock(),
    )
    decision = engine.decide(make_request(), make_authority())
    with pytest.raises(PermissionError) as exc:
        engine.issue_grant(decision, 100)
    assert exc.value.code == "PERMISSION_AUDIT_FAILED"
    assert engine.reader.list_active_for_task("task-1") == ()  # nothing authoritative survived


def test_revoke_fails_closed_and_restores_prior(
    engine: PermissionEngine,
    audit_db_path: Path,
    make_request: RequestFactory,
    make_authority: AuthorityFactory,
) -> None:
    grant = _issue(engine, make_request, make_authority)
    broken = sqlite3.connect(str(audit_db_path))
    broken.execute("DROP TABLE audit_records")
    broken.commit()
    broken.close()
    with pytest.raises(PermissionError) as exc:
        engine.revoke(grant.grant_id)
    assert exc.value.code == "PERMISSION_AUDIT_FAILED"
    restored = engine.reader.get_grant(grant.grant_id)
    assert restored is not None and restored.state is PermissionState.ACTIVE


def test_reconcile_refuses_invalid_audit_chain(
    engine: PermissionEngine,
    audit_db_path: Path,
    make_request: RequestFactory,
    make_authority: AuthorityFactory,
) -> None:
    _issue(engine, make_request, make_authority)
    tamper = sqlite3.connect(str(audit_db_path))
    tamper.execute("DROP TRIGGER audit_records_no_update")
    tamper.execute("UPDATE audit_records SET actor = 'evil' WHERE sequence = 1")
    tamper.commit()
    tamper.close()
    with pytest.raises(PermissionError) as exc:
        engine.reconcile_startup()
    assert exc.value.code == "PERMISSION_AUDIT_CHAIN_INVALID"


def test_migration_missing_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(PermissionError) as exc:
        apply_permission_migrations(tmp_path / "x.db", tmp_path / "empty_dir")
    assert exc.value.code == "MIGRATION_MISSING"


def test_migration_malformed_filename_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "m"
    root.mkdir()
    (root / "not_versioned.sql").write_text("SELECT 1;")
    with pytest.raises(PermissionError) as exc:
        apply_permission_migrations(tmp_path / "x.db", root)
    assert exc.value.code == "MIGRATION_MALFORMED"


def test_migration_integrity_mismatch_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "m"
    root.mkdir()
    (root / "0002_permission.sql").write_text("CREATE TABLE tampered (x);")
    with pytest.raises(PermissionError) as exc:
        apply_permission_migrations(tmp_path / "x.db", root)
    assert exc.value.code == "MIGRATION_INTEGRITY"


def test_migration_apply_failure_is_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "m"
    root.mkdir()
    bad = root / "0002_bad.sql"
    bad.write_text("CREATE TABLE ok (x);\nTHIS IS NOT SQL;\n")
    digest = hashlib.sha256(bad.read_bytes()).hexdigest()
    monkeypatch.setattr(store_mod, "_EXPECTED_MIGRATION_HASHES", {"0002_bad.sql": digest})
    with pytest.raises(PermissionError) as exc:
        apply_permission_migrations(tmp_path / "x.db", root)
    assert exc.value.code == "MIGRATION_FAILED"
