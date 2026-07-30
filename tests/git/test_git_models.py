"""PH-5 unit — Git value objects (baseline manifest, change set)."""

from __future__ import annotations

import pytest

from factory.git import BaselineManifest, ChangeSet, PromotionMode, RepoBaseline


def _manifest() -> BaselineManifest:
    return BaselineManifest(
        project_id="P1",
        version="v1",
        repos=(
            RepoBaseline("repo-a", "aaaa", is_primary=True),
            RepoBaseline("repo-b", "bbbb"),
        ),
        promotion_mode=PromotionMode.ATOMIC,
    )


def test_manifest_primary_and_lookup() -> None:
    m = _manifest()
    assert m.primary().repo_id == "repo-a"
    assert m.approved_commit("repo-b") == "bbbb"


def test_manifest_missing_primary_raises() -> None:
    m = BaselineManifest("P", "v1", (RepoBaseline("r", "c"),), PromotionMode.INDEPENDENT)
    with pytest.raises(ValueError, match="no primary"):
        m.primary()


def test_manifest_unknown_repo_raises() -> None:
    with pytest.raises(KeyError):
        _manifest().approved_commit("ghost")


def test_change_set_helpers() -> None:
    empty = ChangeSet((), (), ())
    assert empty.is_empty
    cs = ChangeSet(("a.py",), ("b.py",), ("c.py",))
    assert not cs.is_empty
    assert cs.all_paths() == ("a.py", "b.py", "c.py")
