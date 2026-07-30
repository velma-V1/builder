"""RPH3-T2 unit — engine guard branches (revoke guards, revalidate on missing/mismatch)."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path

import pytest

from factory.permission import (
    ActionRequest,
    DecisionKind,
    PermissionEngine,
    PermissionError,
    PermissionGrant,
    PermissionState,
    TaskAuthority,
)
from factory.permission.writer import _PermissionWriter

RequestFactory = Callable[..., ActionRequest]
AuthorityFactory = Callable[..., TaskAuthority]


def _issue(
    engine: PermissionEngine, make_request: RequestFactory, make_authority: AuthorityFactory
) -> PermissionGrant:
    decision = engine.decide(make_request(), make_authority())
    assert decision.decision is DecisionKind.ALLOW
    return engine.issue_grant(decision, 100)


def test_revoke_unknown_grant_raises(engine: PermissionEngine) -> None:
    with pytest.raises(PermissionError) as exc:
        engine.revoke("grn-missing")
    assert exc.value.code == "PERMISSION_NOT_FOUND"


def test_revoke_inflight_grant_raises(
    engine: PermissionEngine, make_request: RequestFactory, make_authority: AuthorityFactory
) -> None:
    grant = _issue(engine, make_request, make_authority)
    raw = sqlite3.connect(str(engine.security_database_path))
    raw.execute(
        "UPDATE permission_grants SET commit_state = 'PENDING' WHERE grant_id = ?",
        (grant.grant_id,),
    )
    raw.commit()
    raw.close()
    with pytest.raises(PermissionError) as exc:
        engine.revoke(grant.grant_id)
    assert exc.value.code == "PERMISSION_INFLIGHT"


def test_revoke_terminal_grant_raises(
    engine: PermissionEngine, make_request: RequestFactory, make_authority: AuthorityFactory
) -> None:
    grant = _issue(engine, make_request, make_authority)
    engine.revoke(grant.grant_id)
    with pytest.raises(PermissionError) as exc:
        engine.revoke(grant.grant_id)
    assert exc.value.code == "PERMISSION_NOT_REVOCABLE"


def test_revalidate_missing_grant_is_false(
    engine: PermissionEngine, make_request: RequestFactory, make_authority: AuthorityFactory
) -> None:
    grant = _issue(engine, make_request, make_authority)
    raw = sqlite3.connect(str(engine.security_database_path))
    raw.execute("DELETE FROM permission_grants WHERE grant_id = ?", (grant.grant_id,))
    raw.commit()
    raw.close()
    assert engine.revalidate(grant, engine.clock.now_ts()) is False


def test_revalidate_fingerprint_mismatch_is_false(
    engine: PermissionEngine, make_request: RequestFactory, make_authority: AuthorityFactory
) -> None:
    grant = _issue(engine, make_request, make_authority)
    tampered = PermissionGrant(
        grant_id=grant.grant_id, task_id=grant.task_id, tool=grant.tool, action=grant.action,
        permission_class=grant.permission_class, resource=grant.resource, scope=grant.scope,
        purpose=grant.purpose, grant_fingerprint="different-fingerprint",
        expires_at=grant.expires_at, state=grant.state, commit_state=grant.commit_state,
        created_ts=grant.created_ts, updated_ts=grant.updated_ts,
    )
    assert engine.revalidate(tampered, engine.clock.now_ts()) is False


def test_stage_transition_sqlite_error_fails_closed(security_db_path: Path) -> None:
    # a grant row exists, but the intents table is gone → the intent INSERT fails inside the txn.
    raw = sqlite3.connect(str(security_db_path))
    raw.execute(
        "INSERT INTO permission_grants (grant_id, state, commit_state, task_id, tool, action, "
        "permission_class, resource, scope, purpose, grant_fingerprint, expires_at, created_ts, "
        "updated_ts) VALUES ('g1','ACTIVE','COMMITTED','t','sh','w','WRITE',NULL,'s','p','f',9,1,1)"
    )
    raw.execute("DROP TABLE permission_intents")
    raw.commit()
    raw.close()
    writer = _PermissionWriter(database_path=security_db_path)
    with pytest.raises(PermissionError) as exc:
        writer.stage_transition(
            grant_id="g1", op_key="k", verb="revoke", new_state=PermissionState.REVOKED, ts=2,
        )
    assert exc.value.code == "PERMISSION_STAGE_FAILED"
