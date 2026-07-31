"""Preinstall unit — prerequisite manifest + fail-closed evaluation."""

from __future__ import annotations

from factory.livegate.models import CheckStatus
from factory.preinstall.prerequisites import (
    PREREQUISITES,
    evaluate_prerequisite,
    get_prerequisite,
    unmet_mandatory,
)


def test_manifest_covers_expected_tools() -> None:
    names = {p.name for p in PREREQUISITES}
    assert {"wsl2", "docker", "nvidia_cuda", "ollama", "python", "uv", "sqlite", "git"} <= names


def test_sqlite_floor_is_3_51_3() -> None:
    assert get_prerequisite("sqlite").minimum == (3, 51, 3)


def test_evaluate_pass_fail_unavailable() -> None:
    assert evaluate_prerequisite("docker", (24, 0, 0)) is CheckStatus.PASS
    assert evaluate_prerequisite("docker", (23, 0, 0)) is CheckStatus.FAIL
    assert evaluate_prerequisite("docker", None) is CheckStatus.UNAVAILABLE


def test_unknown_prerequisite_fails_closed() -> None:
    assert evaluate_prerequisite("totally-unknown", (9, 9, 9)) is CheckStatus.ERROR


def test_unmet_mandatory_flags_missing_and_unknown() -> None:
    # Everything satisfied → nothing unmet.
    ok = {p.name: p.minimum for p in PREREQUISITES}
    assert unmet_mandatory(ok) == ()
    # Drop docker + add an unknown → both reported.
    partial = dict(ok)
    del partial["docker"]
    partial["mystery"] = (1, 0)
    unmet = unmet_mandatory(partial)
    assert "docker" in unmet
    assert "unknown:mystery" in unmet
