"""PH-5 unit — GitError surface."""

from __future__ import annotations

from factory.git.errors import GitError


def test_git_error_fields_and_formatting() -> None:
    err = GitError("PROTECTED_REF_WRITE", "denied", security=True)
    assert err.code == "PROTECTED_REF_WRITE"
    assert err.security is True
    assert str(err) == "PROTECTED_REF_WRITE: denied"
    assert repr(err) == "GitError(code='PROTECTED_REF_WRITE', message='denied', security=True)"
