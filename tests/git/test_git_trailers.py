"""PH-5 unit — Factory commit trailers (CTR-COMMIT-TRAILER, ``01I §3.4``)."""

from __future__ import annotations

import pytest

from factory.git import CommitTrailers, VerificationStatus, parse_trailers, render_message
from factory.git.errors import GitError
from factory.git.trailers import render_trailers, status_from, validate_against


def _trailers() -> CommitTrailers:
    return CommitTrailers("T1", "S1", "W1", "CP1", VerificationStatus.CHECKPOINT)


def test_render_and_parse_roundtrip() -> None:
    message = render_message("feat: thing", _trailers())
    found = parse_trailers(message)
    assert found["Factory-Task"] == "T1"
    assert found["Verification-Status"] == "CHECKPOINT"


def test_render_trailers_contains_all_keys() -> None:
    block = render_trailers(_trailers())
    for key in ("Factory-Task", "Factory-Stage", "Factory-Workstream", "Factory-Checkpoint"):
        assert key in block


def test_validate_against_passes_when_consistent() -> None:
    message = render_message("feat: x", _trailers())
    validate_against(message, _trailers())  # no raise


def test_validate_against_detects_mismatch() -> None:
    message = render_message("feat: x", _trailers())
    other = CommitTrailers("T2", "S1", "W1", "CP1", VerificationStatus.CHECKPOINT)
    with pytest.raises(GitError) as exc:
        validate_against(message, other)
    assert exc.value.code == "TRAILER_MISMATCH"


def test_unknown_factory_trailer_is_rejected() -> None:
    with pytest.raises(GitError) as exc:
        parse_trailers("subject\n\nFactory-Bogus: nope\n")
    assert exc.value.code == "TRAILER_UNKNOWN"


def test_status_from_parses_enum() -> None:
    assert status_from("VERIFIED") is VerificationStatus.VERIFIED
