"""PH-5 — secret broker (scoped leases, redaction, revocation, no persistence)."""

from __future__ import annotations

import pytest

from factory.secret import (
    FakeSecretBackend,
    SecretBroker,
    SecretError,
    SecretRef,
    contains_secret,
    redact,
)


def _backend() -> FakeSecretBackend:
    return FakeSecretBackend({"ref-1": "s3cr3t-token", "ref-2": "hunter2"})


def _ref(ref_id: str = "ref-1", ttl: int = 100, task: str = "T1") -> SecretRef:
    return SecretRef(ref_id=ref_id, name="TOKEN", task_id=task, max_ttl=ttl)


def test_backend_satisfies_protocol() -> None:
    assert isinstance(_backend(), SecretBroker)


def test_inject_creates_active_lease() -> None:
    b = _backend()
    lease = b.inject(_ref(), now=0)
    assert lease.value == "s3cr3t-token"
    assert lease.is_active(now=50)
    assert not lease.is_active(now=100)  # expiry exclusive


def test_inject_unknown_ref_rejected() -> None:
    with pytest.raises(SecretError) as exc:
        _backend().inject(_ref("ghost"), now=0)
    assert exc.value.code == "SECRET_UNKNOWN"


def test_inject_bad_ttl_rejected() -> None:
    with pytest.raises(SecretError) as exc:
        _backend().inject(_ref(ttl=0), now=0)
    assert exc.value.code == "SECRET_TTL_INVALID"


def test_redaction_hides_active_material() -> None:
    b = _backend()
    b.inject(_ref(), now=0)
    redacted = b.redact("using s3cr3t-token now", now=1)
    assert "s3cr3t-token" not in redacted
    assert "REDACTED" in redacted


def test_expired_lease_is_not_active() -> None:
    b = _backend()
    b.inject(_ref(ttl=10), now=0)
    assert b.active_values(now=5) == ("s3cr3t-token",)
    assert b.active_values(now=20) == ()


def test_revoke_drops_material() -> None:
    b = _backend()
    b.inject(_ref(), now=0)
    assert b.revoke("ref-1") is True
    assert b.revoke("ref-1") is False  # already gone
    assert b.active_values(now=1) == ()
    assert not b.has_persisted_material(now=1)


def test_revoke_task_clears_all_for_task() -> None:
    b = _backend()
    b.inject(_ref("ref-1", task="T1"), now=0)
    b.inject(_ref("ref-2", task="T1"), now=0)
    assert b.revoke_task("T1") == 2
    assert not b.has_persisted_material(now=1)


def test_scan_export_blocks_leaked_secret() -> None:
    b = _backend()
    with pytest.raises(SecretError) as exc:
        b.scan_export("dump: hunter2")
    assert exc.value.code == "SECRET_IN_EXPORT"
    b.scan_export("clean output")  # no raise


def test_standalone_redaction_helpers() -> None:
    assert redact("ab", ["a"]) == "***REDACTED***b"
    assert contains_secret("xyz", ["y"])
    assert not contains_secret("xyz", ["q"])


def test_secret_error_repr() -> None:
    err = SecretError("X", "y")
    assert "SecretError(code='X'" in repr(err)
    assert str(err) == "X: y"
