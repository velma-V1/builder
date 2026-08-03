"""Phase 3B: WorkspaceManager must not be required for every task -- it is an explicit, opt-in
tool for SANDBOXED_EXECUTION only, never invoked automatically at task intake.
"""

from __future__ import annotations

from pathlib import Path

from factory.git.manager import GitManager
from factory.worker_engine.workspace import WorkspaceManager


def test_provisioning_a_workspace_is_an_explicit_call_not_an_automatic_side_effect(
    tmp_path: Path,
) -> None:
    """Merely constructing a WorkspaceManager (as any execution-mode-aware caller would, since it
    might need one for SOME tasks) must not create anything on disk -- only calling .provision()
    explicitly does."""
    repo = tmp_path / "repo"
    sandbox_root = tmp_path / "sandboxes"
    git = GitManager()
    git.init_repo(repo)

    WorkspaceManager(git, sandbox_root)  # construction only, no provision() call
    assert not sandbox_root.exists()


def test_provisioning_never_touches_the_live_repository_checkout(tmp_path: Path) -> None:
    """Requirement 7 (workspace half): provisioning a disposable worktree must never change the
    live repository's own branch/HEAD or working tree -- only an independent worktree directory
    is ever created."""
    repo = tmp_path / "repo"
    sandbox_root = tmp_path / "sandboxes"
    git = GitManager()
    git.init_repo(repo)
    branch_before = git.current_branch(repo)
    head_before = git.head_commit(repo)

    wm = WorkspaceManager(git, sandbox_root)
    workspace = wm.provision(repo=repo, task_id="t-1", workstream_id="ws-1")

    assert git.current_branch(repo) == branch_before
    assert git.head_commit(repo) == head_before
    assert not git.has_unexplained_changes(repo)
    assert workspace.path.is_dir()
    assert workspace.path != repo

    wm.destroy(repo, workspace)


def test_destroy_removes_the_worktree_and_is_idempotent(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    sandbox_root = tmp_path / "sandboxes"
    git = GitManager()
    git.init_repo(repo)
    wm = WorkspaceManager(git, sandbox_root)
    workspace = wm.provision(repo=repo, task_id="t-1", workstream_id="ws-1")

    wm.destroy(repo, workspace)
    assert not workspace.path.exists()

    # Calling destroy a second time must not raise -- idempotent cleanup.
    wm.destroy(repo, workspace)


def test_writes_inside_a_provisioned_workspace_never_appear_in_the_live_repo(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    sandbox_root = tmp_path / "sandboxes"
    git = GitManager()
    git.init_repo(repo)
    wm = WorkspaceManager(git, sandbox_root)
    workspace = wm.provision(repo=repo, task_id="t-1", workstream_id="ws-1")

    (workspace.path / "new_file.txt").write_text("worker output")

    assert not (repo / "new_file.txt").exists()
    assert not git.has_unexplained_changes(repo)

    wm.destroy(repo, workspace)
