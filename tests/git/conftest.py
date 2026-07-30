"""Shared fixtures for the PH-5 Git manager test suite (real temporary repositories)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from factory.git import GitManager


@pytest.fixture
def manager() -> GitManager:
    return GitManager()


@pytest.fixture
def repo(manager: GitManager, tmp_path: Path) -> Iterator[Path]:
    path = tmp_path / "proj"
    manager.init_repo(path)
    yield path
