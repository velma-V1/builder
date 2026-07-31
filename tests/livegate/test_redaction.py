"""Stage-3 unit — redaction of readiness output."""

from __future__ import annotations

import pytest

from factory.livegate.redaction import redact_pairs, redact_text


@pytest.mark.parametrize(
    ("raw", "must_not_contain"),
    [
        ("token=ghp_ABCDEFGHIJKLMNOPQRSTU12345", "ghp_ABCDEFGHIJKLMNOPQRSTU12345"),
        ("api_key: 'sk-secretvalue12345'", "sk-secretvalue12345"),
        ("PASSWORD=hunter2hunter2", "hunter2hunter2"),
        ("aws AKIAABCDEFGHIJKLMNOP here", "AKIAABCDEFGHIJKLMNOP"),
    ],
)
def test_secrets_are_masked(raw: str, must_not_contain: str) -> None:
    out = redact_text(raw)
    assert must_not_contain not in out
    assert "REDACTED" in out


def test_private_key_block_masked() -> None:
    pem = "-----BEGIN RSA PRIVATE KEY-----\nAAAABBBB\n-----END RSA PRIVATE KEY-----"
    assert "AAAABBBB" not in redact_text(pem)


def test_home_paths_masked() -> None:
    assert redact_text("/home/alice/.ssh/id") == "/home/[USER]/.ssh/id"
    assert redact_text("/Users/bob/data") == "/Users/[USER]/data"


def test_routable_ip_masked_but_allowlist_preserved() -> None:
    assert redact_text("host 203.0.113.9 up") == "host 203.0.x.x up"
    assert redact_text("bind 127.0.0.1 ok") == "bind 127.0.0.1 ok"
    assert redact_text("meta 169.254.169.254") == "meta 169.254.169.254"


def test_redact_pairs_masks_values_only() -> None:
    pairs = redact_pairs((("home", "/home/carol/x"), ("tok", "secret=abcdef123456")))
    assert pairs[0] == ("home", "/home/[USER]/x")
    assert "abcdef123456" not in pairs[1][1] and pairs[1][0] == "tok"
