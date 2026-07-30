"""RPH3-T2 security — least-privilege, path safety (#10), Decision B, TOCTOU, isolation."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path

import pytest

import factory.permission as permission_pkg
from factory.permission import (
    ActionRequest,
    DecisionKind,
    PermissionClass,
    PermissionEngine,
    PermissionState,
    SQLitePermissionReader,
    TaskAuthority,
)
from factory.permission.writer import _PermissionWriter

pytestmark = pytest.mark.security

RequestFactory = Callable[..., ActionRequest]
AuthorityFactory = Callable[..., TaskAuthority]


def test_deny_by_default_class_not_permitted(
    engine: PermissionEngine, make_request: RequestFactory, make_authority: AuthorityFactory
) -> None:
    authority = make_authority(allowed_classes=frozenset({PermissionClass.READ}))
    decision = engine.decide(make_request(permission_class=PermissionClass.WRITE), authority)
    assert decision.decision is DecisionKind.DENY
    assert "least-privilege" in decision.cause


def test_grant_cannot_exceed_task_mismatch(
    engine: PermissionEngine, make_request: RequestFactory, make_authority: AuthorityFactory
) -> None:
    # a request naming a different task than the authority envelope is denied (01K-AC-02)
    decision = engine.decide(make_request(task_id="other-task"), make_authority())
    assert decision.decision is DecisionKind.DENY
    assert "task" in decision.cause


@pytest.mark.parametrize(
    "bad_path",
    [
        "../etc/passwd",          # traversal
        "/etc/passwd",            # absolute posix
        "C:\\Windows\\notepad",   # drive-qualified
        "src/main.py:stream",     # NTFS ADS
        "src/CON",                # reserved device name
        "src/bad\x00name",        # null byte
        "src/trailing ",          # trailing space
    ],
)
def test_path_escapes_are_denied(
    engine: PermissionEngine, make_request: RequestFactory, make_authority: AuthorityFactory,
    bad_path: str,
) -> None:
    decision = engine.decide(make_request(resource=bad_path), make_authority())
    assert decision.decision is DecisionKind.DENY
    assert "path denied" in decision.cause


def test_symlink_escape_is_denied(
    engine: PermissionEngine, project_root: Path, make_request: RequestFactory,
    make_authority: AuthorityFactory,
) -> None:
    outside = project_root.parent / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("secret")
    link = project_root / "src" / "link"
    try:
        link.symlink_to(outside)
    except OSError:  # pragma: no cover - platform without symlink permission
        pytest.skip("symlinks not permitted on this platform")
    decision = engine.decide(
        make_request(resource="src/link/secret.txt", permission_class=PermissionClass.READ),
        make_authority(allowed_paths=("src/**",)),
    )
    assert decision.decision is DecisionKind.DENY
    assert "escapes the project root" in decision.cause


def test_every_delete_is_approval_gated_no_auto_path(
    engine: PermissionEngine, make_request: RequestFactory, make_authority: AuthorityFactory
) -> None:
    # Decision B: at EVERY level, a delete is REQUIRES_APPROVAL — never ALLOW (no auto-delete path).
    for level in ("L1-read", "L2-supervised", "L3-autonomous"):
        decision = engine.decide(
            make_request(permission_class=PermissionClass.DELETE, action="rm"),
            make_authority(autonomy_level=level),
        )
        assert decision.decision is not DecisionKind.ALLOW


def test_toctou_stale_grant_rejected_after_state_change(
    engine: PermissionEngine, make_request: RequestFactory, make_authority: AuthorityFactory
) -> None:
    decision = engine.decide(make_request(), make_authority())
    grant = engine.issue_grant(decision, 100)
    assert engine.revalidate(grant, engine.clock.now_ts()) is True
    # state changes out-of-band between grant and use (revoked) → revalidate must reject (TOCTOU)
    engine.revoke(grant.grant_id)
    assert engine.revalidate(grant, engine.clock.now_ts()) is False


def test_read_only_path_denied_for_write(
    engine: PermissionEngine, make_request: RequestFactory, make_authority: AuthorityFactory
) -> None:
    authority = make_authority(allowed_paths=("**",), read_only_paths=("README.md",))
    decision = engine.decide(
        make_request(permission_class=PermissionClass.WRITE, resource="README.md"), authority
    )
    assert decision.decision is DecisionKind.DENY
    assert "read-only" in decision.cause


# --- structural isolation (DEP-RPH3 §4A + approval/permission table isolation) --------------------


def test_writer_denied_writes_outside_permission_tables(security_db_path: Path) -> None:
    connection = _PermissionWriter(database_path=security_db_path)._connect()
    try:
        with pytest.raises(sqlite3.DatabaseError):
            connection.execute(
                "INSERT INTO schema_migrations (version, applied_at) VALUES (9, 'x')"
            )
    finally:
        connection.close()


def test_permission_writer_cannot_touch_approval_tables(tmp_path: Path) -> None:
    # a shared store carrying both domains (applied in canonical order 0001 → 0002): the permission
    # writer must not mutate approval_* tables.
    from factory.approval import apply_security_migrations
    from factory.permission import apply_permission_migrations

    root = Path("migrations/security")
    store = tmp_path / "spine.db"
    apply_security_migrations(store, root)      # 0001 approval
    apply_permission_migrations(store, root)    # 0002 permission
    connection = _PermissionWriter(database_path=store)._connect()
    try:
        with pytest.raises(sqlite3.DatabaseError):
            connection.execute(
                "INSERT INTO approval_queue (approval_id, enqueued_ts) VALUES ('x', 1)"
            )
    finally:
        connection.close()


def test_reader_connection_denies_every_write(security_db_path: Path) -> None:
    connection = SQLitePermissionReader(database_path=security_db_path)._connect()
    try:
        with pytest.raises(sqlite3.DatabaseError):
            connection.execute("UPDATE permission_grants SET state = 'X'")
    finally:
        connection.close()


def test_writer_is_not_publicly_exported() -> None:
    assert "_PermissionWriter" not in permission_pkg.__all__
    assert not hasattr(permission_pkg, "_PermissionWriter")


def test_grant_only_stores_canonical_path_never_raw(
    engine: PermissionEngine, make_authority: AuthorityFactory
) -> None:
    # a raw path with mixed separators + redundant segments is stored only in canonical form.
    request = ActionRequest(
        task_id="task-1", tool="sh", action="w", permission_class=PermissionClass.WRITE,
        scope="src", purpose="p", resource="src/./main.py",
    )
    decision = engine.decide(request, make_authority())
    assert decision.decision is DecisionKind.ALLOW
    grant = engine.issue_grant(decision, 100)
    assert grant.resource == "src/main.py"
    assert grant.state is PermissionState.ACTIVE
