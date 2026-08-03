"""Disposable, isolated per-task worker workspace (Phase 3B).

A worker never touches the live repository directly: every run gets its own git worktree checked
out from a dedicated task branch, rooted under a scratch directory outside the live working tree.
The worker's writes are scoped to that worktree only (enforced by a ``PathAuthority`` rooted at
the workspace, never the live repo's own authority) and the worktree is destroyed once the run's
output has been frozen into a checkpoint commit and evidence/promotion no longer need it.

``factory.sandbox``'s existing ``SandboxSpec``/``evaluate_spec`` policy (Docker-oriented, still a
deterministic fake pending live WSL2/Docker execution per its own module docstring) is additionally
evaluated here for defense in depth and to keep sandbox *policy* enforcement centralized in one
place, even though the actual isolation mechanism for Phase 3B is the git worktree, not a
container. A policy violation here still fails closed exactly like it would for a real sandbox.
"""

from __future__ import annotations

import contextlib
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path

from factory.git.errors import GitError
from factory.git.manager import GitManager
from factory.sandbox.models import NetworkPolicy, ResourceLimits, SandboxSpec
from factory.sandbox.policy import evaluate_spec
from factory.worker_engine.errors import WorkerEngineRunError

_DEFAULT_RESOURCE_LIMITS = ResourceLimits(
    cpu_millis=2000, memory_mb=2048, disk_mb=4096, pids=64, wall_clock_s=1800
)


@dataclass(frozen=True, slots=True)
class Workspace:
    """A single task run's disposable, isolated worktree."""

    workspace_id: str
    task_id: str
    branch_ref: str
    base_sha: str
    path: Path


def _record_sandbox_policy(*, task_id: str, workstream_id: str) -> None:
    """Evaluate the shared sandbox policy for defense in depth; raise on any violation.

    Constructs a fully-compliant spec (no host mounts, no privilege escalation, hardened
    topology defaults) -- the point is to prove the *policy* a real sandbox would also have to
    satisfy is satisfied, not to actually provision a container.
    """
    spec = SandboxSpec(
        task_id=task_id,
        workstream_id=workstream_id,
        image="local-git-worktree",
        image_version="1",
        resources=_DEFAULT_RESOURCE_LIMITS,
        network=NetworkPolicy.DENY,
    )
    violations = evaluate_spec(spec)
    if violations:
        first = violations[0]
        raise WorkerEngineRunError("SANDBOX_POLICY_DENIED", f"{first.code}: {first.detail}")


class WorkspaceManager:
    """Provisions and destroys per-task disposable worktrees under ``sandbox_root``."""

    __slots__ = ("_git", "_sandbox_root")

    def __init__(self, git: GitManager, sandbox_root: Path) -> None:
        self._git = git
        self._sandbox_root = sandbox_root

    def provision(
        self, *, repo: Path, task_id: str, workstream_id: str, stage_id: str = "worker"
    ) -> Workspace:
        """Create a dedicated task branch off the repo's current HEAD and a worktree for it.

        Never checks out or otherwise mutates the live ``repo`` working directory/HEAD at all --
        the branch is created directly at a commit (no checkout), and only the independent
        worktree directory is ever actually touched by the worker.
        """
        _record_sandbox_policy(task_id=task_id, workstream_id=workstream_id)

        base_sha = self._git.head_commit(repo)
        workspace_id = f"{task_id}-{uuid.uuid4().hex[:12]}"
        branch_ref = f"factory/{stage_id}/{task_id}"
        worktree_path = self._sandbox_root / workspace_id

        self._sandbox_root.mkdir(parents=True, exist_ok=True)
        branch = self._git.create_branch_at(repo, branch_ref, base_sha)
        self._git.add_worktree(repo, branch, worktree_path)

        return Workspace(
            workspace_id=workspace_id,
            task_id=task_id,
            branch_ref=branch_ref,
            base_sha=base_sha,
            path=worktree_path,
        )

    def destroy(self, repo: Path, workspace: Workspace) -> None:
        """Remove the worktree and its branch. Idempotent -- safe to call more than once."""
        if workspace.path.exists():
            try:
                self._git.remove_worktree(repo, workspace.path)
            except GitError:
                shutil.rmtree(workspace.path, ignore_errors=True)
                self._git.prune_worktrees(repo)
        with contextlib.suppress(GitError):
            # Already deleted (a repeated destroy() call) is not a failure -- idempotent.
            self._git.delete_branch(repo, workspace.branch_ref, force=True)
