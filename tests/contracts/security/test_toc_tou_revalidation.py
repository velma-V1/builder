from pathlib import Path

import pytest

from factory.contracts.errors import ContractError
from factory.contracts.models import ErrorCode
from factory.contracts.validation.paths import PathAuthority

pytestmark = pytest.mark.security


def test_revalidation_succeeds_when_nothing_changed(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / "src").mkdir()
    authority = PathAuthority(project_root=root)

    result = authority.evaluate(
        "src/module.py",
        operation="write",
        allowed=["src/**"],
        forbidden=[],
        read_only=[],
        active_exclusive_paths=[],
    )
    assert result.allowed

    authority.revalidate_before_use(result)  # must not raise


def test_revalidation_detects_a_directory_replaced_by_a_symlink_after_authorization(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / "workdir").mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    authority = PathAuthority(project_root=root)

    # An agent is authorized to write to a path under `workdir` at time-of-check...
    result = authority.evaluate(
        "workdir/generated.py",
        operation="write",
        allowed=["**"],
        forbidden=[],
        read_only=[],
        active_exclusive_paths=[],
    )
    assert result.allowed

    # ...but before the write actually happens, an attacker (or a racing process) swaps the
    # authorized directory out for a symlink pointing outside the project root.
    (root / "workdir").rename(tmp_path / "workdir-original")
    (root / "workdir").symlink_to(outside)

    with pytest.raises(ContractError) as raised:
        authority.revalidate_before_use(result)
    assert raised.value.code is ErrorCode.SECURITY_DENIED


def test_revalidation_detects_an_intermediate_directory_becoming_a_symlink(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / "a" / "b").mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    authority = PathAuthority(project_root=root)

    result = authority.evaluate(
        "a/b/file.txt",
        operation="write",
        allowed=["**"],
        forbidden=[],
        read_only=[],
        active_exclusive_paths=[],
    )
    assert result.allowed

    (root / "a").rename(tmp_path / "a-original")
    (root / "a").symlink_to(outside)

    with pytest.raises(ContractError) as raised:
        authority.revalidate_before_use(result)
    assert raised.value.code is ErrorCode.SECURITY_DENIED


def test_revalidation_of_an_already_denied_result_is_always_rejected(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    authority = PathAuthority(project_root=root)

    denied = authority.evaluate(
        "../escape.txt",
        operation="write",
        allowed=["**"],
        forbidden=[],
        read_only=[],
        active_exclusive_paths=[],
    )
    assert not denied.allowed

    with pytest.raises(ContractError) as raised:
        authority.revalidate_before_use(denied)
    assert raised.value.code is ErrorCode.SECURITY_DENIED
