"""PH-5 — Git manager on real temporary repositories (branch/worktree/checkpoint/policy)."""

from __future__ import annotations

from pathlib import Path

import pytest

from factory.git import CommitTrailers, GitManager, VerificationStatus
from factory.git.errors import GitError


def _trailers(cp: str = "CP1") -> CommitTrailers:
    return CommitTrailers("T1", "S1", "W1", cp, VerificationStatus.CHECKPOINT)


def _write(repo: Path, rel: str, text: str) -> None:
    target = repo / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def test_init_creates_main_with_baseline(manager: GitManager, repo: Path) -> None:
    assert manager.current_branch(repo) == "main"
    assert len(manager.head_commit(repo)) == 40


def test_require_clean_start(manager: GitManager, repo: Path) -> None:
    manager.require_clean_start(repo)  # clean → no raise
    _write(repo, "dirty.txt", "x")
    assert manager.has_unexplained_changes(repo)
    with pytest.raises(GitError) as exc:
        manager.require_clean_start(repo)
    assert exc.value.code == "UNEXPLAINED_CHANGES"


def test_create_task_branch_from_baseline(manager: GitManager, repo: Path) -> None:
    base = manager.head_commit(repo)
    branch = manager.create_task_branch(repo, base, task_id="T1", stage_id="S1")
    assert branch == "factory/S1/T1"
    assert manager.current_branch(repo) == branch


def test_create_task_branch_bad_baseline_fails(manager: GitManager, repo: Path) -> None:
    with pytest.raises(GitError) as exc:
        manager.create_task_branch(repo, "deadbeefdeadbeef", task_id="T1", stage_id="S1")
    assert exc.value.code == "GIT_COMMAND_FAILED"


def test_protected_ref_and_force_push_guards(manager: GitManager) -> None:
    with pytest.raises(GitError) as exc:
        manager.guard_protected_ref("main")
    assert exc.value.code == "PROTECTED_REF_WRITE" and exc.value.security
    manager.guard_protected_ref("factory/S1/T1")  # allowed
    with pytest.raises(GitError) as exc2:
        manager.guard_no_force_push(force=True)
    assert exc2.value.code == "FORCE_PUSH_DENIED"
    manager.guard_no_force_push(force=False)  # allowed


def test_checkpoint_owned_paths_only(manager: GitManager, repo: Path) -> None:
    base = manager.head_commit(repo)
    manager.create_task_branch(repo, base, task_id="T1", stage_id="S1")
    _write(repo, "src/a.py", "x = 1\n")
    cp = manager.checkpoint(
        repo, task_id="T1", owned_paths=("src/**",), subject="feat: a", trailers=_trailers()
    )
    assert cp.verification_status is VerificationStatus.CHECKPOINT
    assert not manager.has_unexplained_changes(repo)  # everything committed


def test_checkpoint_rejects_out_of_scope_changes(manager: GitManager, repo: Path) -> None:
    base = manager.head_commit(repo)
    manager.create_task_branch(repo, base, task_id="T1", stage_id="S1")
    _write(repo, "src/a.py", "x = 1\n")
    _write(repo, "outside.py", "y = 2\n")
    with pytest.raises(GitError) as exc:
        manager.checkpoint(
            repo, task_id="T1", owned_paths=("src/**",), subject="x", trailers=_trailers()
        )
    assert exc.value.code == "CHECKPOINT_SCOPE" and exc.value.security


def test_checkpoint_empty_is_rejected(manager: GitManager, repo: Path) -> None:
    base = manager.head_commit(repo)
    manager.create_task_branch(repo, base, task_id="T1", stage_id="S1")
    with pytest.raises(GitError) as exc:
        manager.checkpoint(
            repo, task_id="T1", owned_paths=("src/**",), subject="x", trailers=_trailers()
        )
    assert exc.value.code == "CHECKPOINT_EMPTY"


def test_checkpoint_on_protected_branch_denied(manager: GitManager, repo: Path) -> None:
    _write(repo, "src/a.py", "x = 1\n")  # still on main
    with pytest.raises(GitError) as exc:
        manager.checkpoint(
            repo, task_id="T1", owned_paths=("src/**",), subject="x", trailers=_trailers()
        )
    assert exc.value.code == "PROTECTED_REF_WRITE"


def test_exact_change_tracking(manager: GitManager, repo: Path) -> None:
    base = manager.head_commit(repo)
    manager.create_task_branch(repo, base, task_id="T1", stage_id="S1")
    _write(repo, "src/a.py", "x = 1\n")
    manager.checkpoint(
        repo, task_id="T1", owned_paths=("src/**",), subject="add a", trailers=_trailers("CP1")
    )
    c1 = manager.head_commit(repo)
    added = manager.changed_files(repo, base, c1)
    assert added.added == ("src/a.py",)

    _write(repo, "src/a.py", "x = 2\n")
    _write(repo, "src/b.py", "z = 3\n")
    manager.checkpoint(
        repo, task_id="T1", owned_paths=("src/**",), subject="mod", trailers=_trailers("CP2")
    )
    c2 = manager.head_commit(repo)
    delta = manager.changed_files(repo, c1, c2)
    assert delta.modified == ("src/a.py",)
    assert delta.added == ("src/b.py",)


def test_git_invocation_is_time_bounded(
    manager: GitManager, repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import subprocess

    def _timeout(*_args: object, **_kwargs: object) -> object:
        raise subprocess.TimeoutExpired(cmd="git", timeout=1)

    # Patch the shared subprocess module; the manager's ``subprocess.run`` resolves the same object.
    monkeypatch.setattr(subprocess, "run", _timeout)
    with pytest.raises(GitError) as exc:
        manager.head_commit(repo)
    assert exc.value.code == "GIT_TIMEOUT"


def test_rename_is_not_miscounted(manager: GitManager, repo: Path) -> None:
    base = manager.head_commit(repo)
    manager.create_task_branch(repo, base, task_id="T1", stage_id="S1")
    _write(repo, "src/a.py", "identical content for rename detection\n")
    manager.checkpoint(
        repo, task_id="T1", owned_paths=("src/**",), subject="add", trailers=_trailers("CP1")
    )
    c1 = manager.head_commit(repo)
    (repo / "src" / "a.py").rename(repo / "src" / "b.py")  # same content -> git detects a rename
    manager.checkpoint(
        repo, task_id="T1", owned_paths=("src/**",), subject="rename", trailers=_trailers("CP2")
    )
    delta = manager.changed_files(repo, c1, manager.head_commit(repo))
    # A rename (status R) is not categorized as add/modify/delete by the exact tracker.
    assert delta.is_empty


def test_worktree_lifecycle(manager: GitManager, repo: Path, tmp_path: Path) -> None:
    base = manager.head_commit(repo)
    branch = manager.create_task_branch(repo, base, task_id="T2", stage_id="S1")
    manager.create_task_branch(repo, base, task_id="T1", stage_id="S1")  # leave branch checked out
    wt_path = tmp_path / "wt"
    handle = manager.add_worktree(repo, branch, wt_path)
    assert handle.branch == branch
    assert wt_path.exists()
    manager.remove_worktree(repo, wt_path)
    assert not wt_path.exists()
