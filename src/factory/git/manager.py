"""PH-5 Git manager (Task 5.1, ``01I``).

Controlled, offline-safe Git operations on real repositories: task branches from an approved
baseline, worktree isolation, verified checkpoint commits (owned paths + standardized trailers
only), and exact change tracking. The manager enforces the ``01I`` safety boundary locally:

* **protected refs are never written by a workstream** (``01I §3.2/§5.4``); an attempt is a security
  event;
* **force-push / history rewrite never happen automatically** (``01I §5.13``);
* **unexplained local changes block task start** (``01I §5.8``);
* **checkpoints include only owned-path changes** (ownership validation), with trailers agreeing
  with the authoritative task record (``01I §5.12``).

Real ``git`` is invoked with argument lists (never a shell); the executable is resolved to an
absolute path so no partial-path lookup occurs.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path

from factory.contracts.validation.paths import PathAuthority
from factory.git.errors import GitError
from factory.git.models import (
    ChangeSet,
    Checkpoint,
    CommitTrailers,
    WorktreeHandle,
)
from factory.git.trailers import render_message, validate_against

_DEFAULT_PROTECTED = frozenset({"main", "master"})
_BOT_ENV = ("-c", "user.name=Factory", "-c", "user.email=factory@localhost")
# Bounded wall-clock for any single git invocation so a hung git process cannot block a lane.
_DEFAULT_GIT_TIMEOUT_S = 60


def _git_executable() -> str:
    found = shutil.which("git")
    if found is None:  # pragma: no cover - git is a required dev dependency
        raise GitError("GIT_UNAVAILABLE", "git executable not found on PATH")
    return found


class GitManager:
    """Controlled Git operations bound to an approved baseline and protected-ref policy."""

    __slots__ = ("_git", "_protected", "_timeout")

    def __init__(
        self,
        protected_refs: frozenset[str] = _DEFAULT_PROTECTED,
        *,
        timeout_s: int = _DEFAULT_GIT_TIMEOUT_S,
    ) -> None:
        self._git = _git_executable()
        self._protected = protected_refs
        self._timeout = timeout_s

    # -- low-level -------------------------------------------------------------------------
    def _run(self, repo: Path, *args: str) -> str:
        try:
            result = subprocess.run(  # noqa: S603 - args are literal/validated, never shell-parsed
                [self._git, "-C", str(repo), *args],
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
        except subprocess.TimeoutExpired as exc:
            # ``subprocess.run`` kills + reaps the child on timeout; surface it as a bounded error.
            raise GitError(
                "GIT_TIMEOUT", f"git {args[0]} exceeded {self._timeout}s and was terminated"
            ) from exc
        if result.returncode != 0:
            raise GitError("GIT_COMMAND_FAILED", f"git {args[0]} failed: {result.stderr.strip()}")
        return result.stdout

    # -- setup / inspection ----------------------------------------------------------------
    def init_repo(self, path: Path) -> None:
        """Initialize a repository with a deterministic initial commit (test/bootstrap helper)."""
        path.mkdir(parents=True, exist_ok=True)
        self._run(path, "init", "-q", "-b", "main")
        (path / ".gitkeep").write_text("", encoding="utf-8")
        self._run(path, "add", ".gitkeep")
        self._run(path, *_BOT_ENV, "commit", "-q", "-m", "baseline")

    def head_commit(self, repo: Path) -> str:
        return self._run(repo, "rev-parse", "HEAD").strip()

    def current_branch(self, repo: Path) -> str:
        return self._run(repo, "rev-parse", "--abbrev-ref", "HEAD").strip()

    def resolve_ref(self, repo: Path, ref: str) -> str:
        return self._run(repo, "rev-parse", f"{ref}^{{commit}}").strip()

    def fast_forward_ref(self, repo: Path, ref: str, commit: str, expected_old: str) -> None:
        """Atomically advance an unprotected ref after proving ancestry and expected revision."""
        self.guard_protected_ref(ref)
        self._run(repo, "merge-base", "--is-ancestor", expected_old, commit)
        self._run(repo, "update-ref", f"refs/heads/{ref}", commit, expected_old)

    def restore_ref(self, repo: Path, ref: str, commit: str, expected_current: str) -> None:
        """Atomically restore an unprotected ref during controlled promotion rollback."""
        self.guard_protected_ref(ref)
        self._run(repo, "update-ref", f"refs/heads/{ref}", commit, expected_current)

    def file_digest_at(self, repo: Path, commit: str, path: str) -> str:
        """Return the exact blob digest used for immutable manifest revalidation."""
        try:
            result = subprocess.run(  # noqa: S603 - resolved git executable, argv without shell
                [self._git, "-C", str(repo), "show", f"{commit}:{path}"],
                capture_output=True,
                timeout=self._timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise GitError("GIT_TIMEOUT", "git show exceeded promotion timeout") from exc
        if result.returncode != 0:
            raise GitError("GIT_COMMAND_FAILED", f"manifest path unavailable: {path}")
        return hashlib.sha256(result.stdout).hexdigest()

    def has_unexplained_changes(self, repo: Path) -> bool:
        return bool(self._run(repo, "status", "--porcelain").strip())

    def require_clean_start(self, repo: Path) -> None:
        """Refuse to begin work when unexplained local changes exist (``01I §5.8``)."""
        if self.has_unexplained_changes(repo):
            raise GitError(
                "UNEXPLAINED_CHANGES", "workspace has uncommitted changes; task start refused"
            )

    # -- policy guards ---------------------------------------------------------------------
    def guard_protected_ref(self, ref: str) -> None:
        """Reject a workstream write to a protected ref; record as a security event (``§5.7``)."""
        if ref in self._protected:
            raise GitError(
                "PROTECTED_REF_WRITE",
                f"workstreams may not write protected ref {ref}",
                security=True,
            )

    def guard_no_force_push(self, *, force: bool) -> None:
        """Automatic force-push / history rewrite is never permitted (``01I §5.13``)."""
        if force:
            raise GitError(
                "FORCE_PUSH_DENIED",
                "force-push / history rewrite requires high-risk approval",
                security=True,
            )

    # -- branch / worktree lifecycle -------------------------------------------------------
    def create_task_branch(
        self, repo: Path, baseline_commit: str, task_id: str, stage_id: str
    ) -> str:
        """Create a traceable controlled task branch from an approved baseline commit."""
        branch = f"factory/{stage_id}/{task_id}"
        self.guard_protected_ref(branch)
        self._run(repo, "checkout", "-q", "-b", branch, baseline_commit)
        return branch

    def create_branch_at(self, repo: Path, branch: str, commit: str) -> str:
        """Create a branch ref pointing at ``commit`` without checking it out or touching the
        live repo's working directory/HEAD at all (Phase 3B: worktree-only worker branches)."""
        self.guard_protected_ref(branch)
        self._run(repo, "branch", branch, commit)
        return branch

    def add_worktree(self, repo: Path, branch: str, worktree_path: Path) -> WorktreeHandle:
        self.guard_protected_ref(branch)
        self._run(repo, "worktree", "add", "-q", str(worktree_path), branch)
        return WorktreeHandle(branch=branch, path=str(worktree_path))

    def remove_worktree(self, repo: Path, worktree_path: Path) -> None:
        self._run(repo, "worktree", "remove", "--force", str(worktree_path))

    def delete_branch(self, repo: Path, branch: str, *, force: bool = True) -> None:
        """Delete a local branch (Phase 3B: disposable per-task worker branches)."""
        self.guard_protected_ref(branch)
        flag = "-D" if force else "-d"
        self._run(repo, "branch", flag, branch)

    def prune_worktrees(self, repo: Path) -> None:
        """Clean up worktree administrative files for worktrees removed on disk out-of-band."""
        self._run(repo, "worktree", "prune")

    # -- change tracking -------------------------------------------------------------------
    def working_changes(self, repo: Path) -> tuple[str, ...]:
        lines = self._run(repo, "status", "--porcelain").splitlines()
        return tuple(sorted(line[3:] for line in lines if line.strip()))

    def changed_files(self, repo: Path, from_ref: str, to_ref: str = "HEAD") -> ChangeSet:
        """Exact change tracking between two committed states (``01I §5.10``)."""
        out = self._run(repo, "diff", "--name-status", from_ref, to_ref)
        added: list[str] = []
        modified: list[str] = []
        deleted: list[str] = []
        for line in out.splitlines():
            status, _, path = line.partition("\t")
            # A/M/D are tracked; renames/copies/type-changes carry no single owned path here.
            bucket = {"A": added, "M": modified, "D": deleted}.get(status[:1])
            if bucket is not None:
                bucket.append(path.strip())
        return ChangeSet(tuple(sorted(added)), tuple(sorted(modified)), tuple(sorted(deleted)))

    # -- checkpoint ------------------------------------------------------------------------
    def checkpoint(
        self,
        repo: Path,
        *,
        task_id: str,
        owned_paths: tuple[str, ...],
        subject: str,
        trailers: CommitTrailers,
    ) -> Checkpoint:
        """Commit a verified checkpoint of *owned-path* changes only, with validated trailers."""
        branch = self.current_branch(repo)
        self.guard_protected_ref(branch)

        changed = self.working_changes(repo)
        if not changed:
            raise GitError("CHECKPOINT_EMPTY", "no changes to checkpoint (coherent commits only)")

        authority = PathAuthority(repo)
        out_of_scope = [
            path
            for path in changed
            if not authority.evaluate(
                path,
                operation="write",
                allowed=list(owned_paths),
                forbidden=[],
                read_only=[],
                active_exclusive_paths=[],
            ).allowed
        ]
        if out_of_scope:
            raise GitError(
                "CHECKPOINT_SCOPE",
                f"changes outside owned paths cannot be checkpointed: {sorted(out_of_scope)}",
                security=True,
            )

        message = render_message(subject, trailers)
        validate_against(message, trailers)
        for path in changed:
            self._run(repo, "add", "--", path)
        self._run(repo, *_BOT_ENV, "commit", "-q", "-m", message)
        return Checkpoint(
            checkpoint_id=trailers.checkpoint_id,
            commit_sha=self.head_commit(repo),
            branch=branch,
            task_id=task_id,
            verification_status=trailers.verification_status,
        )
