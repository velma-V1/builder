"""Factory commit-trailer rendering + validation (CTR-COMMIT-TRAILER, ``01I §3.4``).

Trailers are rendered deterministically and validated back so a commit message can never disagree
with the authoritative task/evidence record it claims (``01I §5.12``). Parsing rejects an unknown
Factory trailer key and a value mismatch.
"""

from __future__ import annotations

from factory.git.errors import GitError
from factory.git.models import CommitTrailers, VerificationStatus

_TASK = "Factory-Task"
_STAGE = "Factory-Stage"
_WORKSTREAM = "Factory-Workstream"
_CHECKPOINT = "Factory-Checkpoint"
_STATUS = "Verification-Status"

_KNOWN_KEYS = frozenset({_TASK, _STAGE, _WORKSTREAM, _CHECKPOINT, _STATUS})


def render_trailers(trailers: CommitTrailers) -> str:
    """Render the standardized trailer block (``01I §3.4``)."""
    return "\n".join(
        [
            f"{_TASK}: {trailers.task_id}",
            f"{_STAGE}: {trailers.stage_id}",
            f"{_WORKSTREAM}: {trailers.workstream_id}",
            f"{_CHECKPOINT}: {trailers.checkpoint_id}",
            f"{_STATUS}: {trailers.verification_status.value}",
        ]
    )


def render_message(subject: str, trailers: CommitTrailers) -> str:
    return f"{subject}\n\n{render_trailers(trailers)}\n"


def parse_trailers(message: str) -> dict[str, str]:
    """Extract Factory trailers from a commit message; reject unknown Factory-* keys."""
    found: dict[str, str] = {}
    for line in message.splitlines():
        if ": " not in line:
            continue
        key, _, value = line.partition(": ")
        key = key.strip()
        if key in _KNOWN_KEYS:
            found[key] = value.strip()
        elif key.startswith("Factory-"):
            raise GitError("TRAILER_UNKNOWN", f"unknown Factory trailer key: {key}")
    return found


def validate_against(message: str, expected: CommitTrailers) -> None:
    """Raise ``TRAILER_MISMATCH`` if the message trailers disagree with the authoritative record."""
    found = parse_trailers(message)
    mismatches = []
    for key, value in (
        (_TASK, expected.task_id),
        (_STAGE, expected.stage_id),
        (_WORKSTREAM, expected.workstream_id),
        (_CHECKPOINT, expected.checkpoint_id),
        (_STATUS, expected.verification_status.value),
    ):
        if found.get(key) != value:
            mismatches.append(key)
    if mismatches:
        raise GitError(
            "TRAILER_MISMATCH", f"commit trailers disagree with task record: {sorted(mismatches)}"
        )


def status_from(value: str) -> VerificationStatus:
    return VerificationStatus(value)
