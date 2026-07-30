"""Regression tests for exact migration bytes in Windows Git checkouts."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

PINNED_MIGRATIONS = (
    (
        "migrations/contracts/0001_activation_store.sql",
        "21d41f6d954fc92ef15c114ee847b81ca8d17eb83d5895823fd57ca6f337ffa1",
    ),
    (
        "migrations/runtime/0001_state.sql",
        "2fd4ecda34c05265be99de9c8aa36518cc9ac540c4038286c5da9cfb1fbd5f4c",
    ),
    (
        "migrations/runtime/0002_leases.sql",
        "a3a143e4b225655b68aadb5bc677acae7a99cf99b8c047e6c3113deb34b32ba6",
    ),
    (
        "migrations/runtime/0003_memory.sql",
        "65e0a4d16b84a49b205b1f2e48c91e11ae6dc48e9c179e318da3026283e10587",
    ),
    (
        "migrations/audit/0001_audit_chain.sql",
        "935e535a8db35693f94c6a30bcd9d312960eeeb24babea62e933ba7dfa06c433",
    ),
    (
        "migrations/security/0001_security_spine.sql",
        "099ae959d6f06c6b944925af151d8fa8dd2b65fdffd63660cf2a4355b7878a51",
    ),
    (
        "migrations/security/0002_permission.sql",
        "a65d227d9683eb060c834ae8b3cb65f33186ba37420b4065eec8623f8ded88cb",
    ),
    (
        "migrations/security/0003_tools.sql",
        "0050e74f80932fb58ea15d1f60f95661c7589d57dd623aad7691e26ea73a69b5",
    ),
)


@pytest.mark.parametrize(("relative_path", "expected_sha"), PINNED_MIGRATIONS)
def test_checked_out_migration_bytes_match_exact_pinned_sha(
    relative_path: str, expected_sha: str
) -> None:
    """A checkout conversion to CRLF must not invalidate a pinned migration."""
    content = (REPOSITORY_ROOT / relative_path).read_bytes()
    assert b"\r\n" not in content
    assert hashlib.sha256(content).hexdigest() == expected_sha


@pytest.mark.parametrize("relative_path", [path for path, _sha in PINNED_MIGRATIONS])
def test_git_checkout_policy_for_migrations_is_lf(relative_path: str) -> None:
    """Git must materialize every tracked SQL migration with exact LF bytes."""
    result = subprocess.run(  # noqa: S603
        ["git", "check-attr", "text", "eol", "--", relative_path],  # noqa: S607
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.splitlines() == [
        f"{relative_path}: text: set",
        f"{relative_path}: eol: lf",
    ]
