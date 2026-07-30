"""RPH3-T2 unit — Permission Engine decisions + grant lifecycle (decide/issue/revalidate/revoke)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

import pytest

from factory.permission import (
    ActionRequest,
    CommitState,
    DecisionKind,
    PermissionClass,
    PermissionEngine,
    PermissionError,
    PermissionGrant,
    PermissionState,
    TaskAuthority,
)

RequestFactory = Callable[..., ActionRequest]
AuthorityFactory = Callable[..., TaskAuthority]


class ControllableClock(Protocol):
    def now_ts(self) -> int: ...
    def advance(self, seconds: int) -> None: ...


def _issue(
    engine: PermissionEngine, request: ActionRequest, authority: TaskAuthority, ttl: int = 100
) -> PermissionGrant:
    decision = engine.decide(request, authority)
    assert decision.decision is DecisionKind.ALLOW
    return engine.issue_grant(decision, ttl)


def test_allow_in_envelope_path_contained(
    engine: PermissionEngine, make_request: RequestFactory, make_authority: AuthorityFactory
) -> None:
    decision = engine.decide(make_request(), make_authority())
    assert decision.decision is DecisionKind.ALLOW
    assert decision.canonical_resource == "src/main.py"


def test_issue_grant_is_active_committed_and_bound(
    engine: PermissionEngine, make_request: RequestFactory, make_authority: AuthorityFactory
) -> None:
    grant = _issue(engine, make_request(), make_authority())
    assert grant.state is PermissionState.ACTIVE
    assert grant.commit_state is CommitState.COMMITTED
    assert grant.resource == "src/main.py"
    assert grant.grant_fingerprint
    assert engine.revalidate(grant, engine.clock.now_ts()) is True


def test_issue_grant_rejects_non_allow_decision(
    engine: PermissionEngine, make_request: RequestFactory, make_authority: AuthorityFactory
) -> None:
    decision = engine.decide(
        make_request(permission_class=PermissionClass.DELETE), make_authority()
    )
    assert decision.decision is DecisionKind.REQUIRES_APPROVAL
    with pytest.raises(PermissionError) as exc:
        engine.issue_grant(decision, 100)
    assert exc.value.code == "PERMISSION_NOT_ALLOWED"


def test_issue_grant_rejects_nonpositive_ttl(
    engine: PermissionEngine, make_request: RequestFactory, make_authority: AuthorityFactory
) -> None:
    decision = engine.decide(make_request(), make_authority())
    with pytest.raises(PermissionError) as exc:
        engine.issue_grant(decision, 0)
    assert exc.value.code == "PERMISSION_INVALID_TTL"


def test_delete_is_requires_approval_decision_b(
    engine: PermissionEngine, make_request: RequestFactory, make_authority: AuthorityFactory
) -> None:
    decision = engine.decide(
        make_request(permission_class=PermissionClass.DELETE, action="rm"), make_authority()
    )
    assert decision.decision is DecisionKind.REQUIRES_APPROVAL
    assert "Decision B" in decision.cause


def test_out_of_envelope_is_requires_approval_decision_a(
    engine: PermissionEngine, make_request: RequestFactory, make_authority: AuthorityFactory
) -> None:
    # WRITE permitted for the task, but the L1-read autonomy level does not auto-run WRITE.
    authority = make_authority(
        autonomy_level="L1-read",
        allowed_classes=frozenset({PermissionClass.READ, PermissionClass.WRITE}),
    )
    decision = engine.decide(make_request(permission_class=PermissionClass.WRITE), authority)
    assert decision.decision is DecisionKind.REQUIRES_APPROVAL
    assert "Decision A" in decision.cause


def test_revalidate_after_revoke_is_false(
    engine: PermissionEngine, make_request: RequestFactory, make_authority: AuthorityFactory
) -> None:
    grant = _issue(engine, make_request(), make_authority())
    engine.revoke(grant.grant_id)
    revoked = engine.reader.get_grant(grant.grant_id)
    assert revoked is not None and revoked.state is PermissionState.REVOKED
    assert engine.revalidate(grant, engine.clock.now_ts()) is False


def test_expire_sweeps_and_revalidate_false(
    engine: PermissionEngine, clock: ControllableClock, make_request: RequestFactory,
    make_authority: AuthorityFactory,
) -> None:
    grant = _issue(engine, make_request(), make_authority(), ttl=10)
    clock.advance(11)
    assert engine.revalidate(grant, clock.now_ts()) is False  # auto-expiry at point of use
    expired = engine.expire()
    assert expired == (grant.grant_id,)
    swept = engine.reader.get_grant(grant.grant_id)
    assert swept is not None and swept.state is PermissionState.EXPIRED


def test_canonicalize_returns_relative_and_rejects_escape(
    engine: PermissionEngine, make_authority: AuthorityFactory
) -> None:
    authority = make_authority()
    assert engine.canonicalize("src/main.py", authority) == "src/main.py"
    with pytest.raises(PermissionError) as exc:
        engine.canonicalize("../secrets", authority)
    assert exc.value.code == "PERMISSION_PATH_ESCAPE"


def test_grant_without_path_resource(
    engine: PermissionEngine, make_request: RequestFactory, make_authority: AuthorityFactory
) -> None:
    # EXECUTE with no resource: no path validation, in-envelope at L2 → ALLOW.
    request = make_request(
        permission_class=PermissionClass.EXECUTE, action="run_tests", resource=None
    )
    decision = engine.decide(request, make_authority())
    assert decision.decision is DecisionKind.ALLOW
    assert decision.canonical_resource is None
    grant = engine.issue_grant(decision, 100)
    assert grant.resource is None
