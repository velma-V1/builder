"""Value objects for the PH-5 Git manager (``01I``).

Encodes the two Task-5.1 contracts and the branch/checkpoint vocabulary:

* **CTR-BASELINE-MANIFEST** (``01I §3.3``) — :class:`BaselineManifest` / :class:`RepoBaseline`: the
  versioned, multi-repo approved baseline with promotion mode and per-repo approved commit.
* **CTR-COMMIT-TRAILER** (``01I §3.4``) — :class:`CommitTrailers`: the standardized Factory trailer
  set whose values must agree with authoritative task/evidence records.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class PromotionMode(StrEnum):
    INDEPENDENT = "INDEPENDENT"
    ATOMIC = "ATOMIC"


class VerificationStatus(StrEnum):
    UNVERIFIED = "UNVERIFIED"
    CHECKPOINT = "CHECKPOINT"
    VERIFIED = "VERIFIED"


@dataclass(frozen=True, slots=True)
class RepoBaseline:
    """One repository's canonical identity + approved commit within a project baseline."""

    repo_id: str
    approved_commit: str
    is_primary: bool = False


@dataclass(frozen=True, slots=True)
class BaselineManifest:
    """Versioned Project Baseline Manifest (CTR-BASELINE-MANIFEST, ``01I §3.3``)."""

    project_id: str
    version: str
    repos: tuple[RepoBaseline, ...]
    promotion_mode: PromotionMode

    def primary(self) -> RepoBaseline:
        for repo in self.repos:
            if repo.is_primary:
                return repo
        raise ValueError("baseline manifest has no primary repository")

    def approved_commit(self, repo_id: str) -> str:
        for repo in self.repos:
            if repo.repo_id == repo_id:
                return repo.approved_commit
        raise KeyError(repo_id)


@dataclass(frozen=True, slots=True)
class CommitTrailers:
    """Standardized Factory commit trailers (CTR-COMMIT-TRAILER, ``01I §3.4``)."""

    task_id: str
    stage_id: str
    workstream_id: str
    checkpoint_id: str
    verification_status: VerificationStatus


@dataclass(frozen=True, slots=True)
class Checkpoint:
    """A verified checkpoint commit on a controlled task branch."""

    checkpoint_id: str
    commit_sha: str
    branch: str
    task_id: str
    verification_status: VerificationStatus


@dataclass(frozen=True, slots=True)
class WorktreeHandle:
    branch: str
    path: str


@dataclass(frozen=True, slots=True)
class ChangeSet:
    """Exact change tracking between two tree states (``01I §5.10`` traceability)."""

    added: tuple[str, ...]
    modified: tuple[str, ...]
    deleted: tuple[str, ...]

    @property
    def is_empty(self) -> bool:
        return not (self.added or self.modified or self.deleted)

    def all_paths(self) -> tuple[str, ...]:
        return tuple(sorted({*self.added, *self.modified, *self.deleted}))
