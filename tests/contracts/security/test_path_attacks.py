import os
import subprocess
import sys
from pathlib import Path

import pytest

from factory.contracts.errors import ContractError
from factory.contracts.models import ErrorCode
from factory.contracts.validation.paths import PathAuthority

pytestmark = pytest.mark.security


def _evaluate(tmp_path: Path, candidate: str, *, allowed: list[str] | None = None) -> bool:
    authority = PathAuthority(project_root=tmp_path)
    result = authority.evaluate(
        candidate,
        operation="write",
        allowed=allowed if allowed is not None else ["**"],
        forbidden=[],
        read_only=[],
        active_exclusive_paths=[],
    )
    return result.allowed


def test_dot_dot_traversal_is_denied(tmp_path: Path) -> None:
    assert not _evaluate(tmp_path, "../outside.txt")
    assert not _evaluate(tmp_path, "src/../../outside.txt")


def test_absolute_posix_path_is_denied(tmp_path: Path) -> None:
    assert not _evaluate(tmp_path, "/etc/passwd")


def test_absolute_windows_path_is_denied(tmp_path: Path) -> None:
    assert not _evaluate(tmp_path, "C:\\Windows\\System32\\evil.dll")
    assert not _evaluate(tmp_path, "C:/Windows/System32/evil.dll")


def test_unc_path_is_denied(tmp_path: Path) -> None:
    assert not _evaluate(tmp_path, "\\\\attacker-host\\share\\file.txt")


def test_sibling_prefix_bypass_is_denied(tmp_path: Path) -> None:
    root = tmp_path / "Factory"
    root.mkdir()
    (tmp_path / "Factory-Evil").mkdir()
    authority = PathAuthority(project_root=root)

    # A naive `str.startswith` containment check would incorrectly allow this,
    # since "Factory-Evil" starts with the same string as "Factory".
    escaped = os.path.relpath(tmp_path / "Factory-Evil" / "secret.txt", root)
    result = authority.evaluate(
        escaped,
        operation="write",
        allowed=["**"],
        forbidden=[],
        read_only=[],
        active_exclusive_paths=[],
    )
    assert not result.allowed


def test_mixed_separators_are_normalized_and_still_checked(tmp_path: Path) -> None:
    assert not _evaluate(tmp_path, "src\\..\\..\\outside.txt")


def test_trailing_spaces_and_dots_are_denied(tmp_path: Path) -> None:
    assert not _evaluate(tmp_path, "src/file.py ")
    assert not _evaluate(tmp_path, "src/file.py.")


def test_ads_syntax_is_denied(tmp_path: Path) -> None:
    assert not _evaluate(tmp_path, "src/file.txt:hidden-stream")


@pytest.mark.parametrize(
    "name", ["CON", "PRN", "AUX", "NUL", "COM1", "COM9", "LPT1", "LPT9", "con.txt", "Nul.log"]
)
def test_reserved_device_names_are_denied(tmp_path: Path, name: str) -> None:
    assert not _evaluate(tmp_path, f"src/{name}")


def test_null_byte_is_denied(tmp_path: Path) -> None:
    assert not _evaluate(tmp_path, "src/file\x00.py")


def test_symlink_escape_is_denied(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("secret", encoding="utf-8")
    (root / "link").symlink_to(outside)

    authority = PathAuthority(project_root=root)
    result = authority.evaluate(
        "link/secret.txt",
        operation="read",
        allowed=["**"],
        forbidden=[],
        read_only=[],
        active_exclusive_paths=[],
    )
    assert not result.allowed


@pytest.mark.skipif(sys.platform != "win32", reason="junction escape requires Windows semantics")
def test_junction_escape_is_denied_on_windows(tmp_path: Path) -> None:  # pragma: no cover
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("secret", encoding="utf-8")
    subprocess.run(  # noqa: S603 -- fixed command; paths come from pytest's temp directory
        [os.environ["COMSPEC"], "/d", "/c", "mklink", "/J", str(root / "link"), str(outside)],
        check=True,
        capture_output=True,
        text=True,
    )

    authority = PathAuthority(project_root=root)
    result = authority.evaluate(
        "link/secret.txt",
        operation="read",
        allowed=["**"],
        forbidden=[],
        read_only=[],
        active_exclusive_paths=[],
    )
    assert not result.allowed


def test_allowed_path_does_not_override_forbidden_or_read_only(tmp_path: Path) -> None:
    authority = PathAuthority(project_root=tmp_path)
    result = authority.evaluate(
        "docs/frozen.md",
        operation="write",
        allowed=["**"],
        forbidden=["docs/frozen.md"],
        read_only=[],
        active_exclusive_paths=[],
    )
    assert not result.allowed


def test_read_only_path_denies_write(tmp_path: Path) -> None:
    authority = PathAuthority(project_root=tmp_path)
    result = authority.evaluate(
        "schemas/locked.json",
        operation="write",
        allowed=["**"],
        forbidden=[],
        read_only=["schemas/**"],
        active_exclusive_paths=[],
    )
    assert not result.allowed


def test_active_exclusive_ownership_denies_concurrent_write(tmp_path: Path) -> None:
    authority = PathAuthority(project_root=tmp_path)
    result = authority.evaluate(
        "src/shared.py",
        operation="write",
        allowed=["**"],
        forbidden=[],
        read_only=[],
        active_exclusive_paths=["src/**"],
    )
    assert not result.allowed


def test_revalidate_before_use_rejects_denied_result(tmp_path: Path) -> None:
    authority = PathAuthority(project_root=tmp_path)
    denied = authority.evaluate(
        "../outside.txt",
        operation="write",
        allowed=["**"],
        forbidden=[],
        read_only=[],
        active_exclusive_paths=[],
    )
    with pytest.raises(ContractError) as raised:
        authority.revalidate_before_use(denied)
    assert raised.value.code is ErrorCode.SECURITY_DENIED


def test_revalidate_before_use_detects_toctou_symlink_swap(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / "workdir").mkdir()
    authority = PathAuthority(project_root=root)

    result = authority.evaluate(
        "workdir/file.py",
        operation="write",
        allowed=["**"],
        forbidden=[],
        read_only=[],
        active_exclusive_paths=[],
    )
    assert result.allowed

    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "workdir").rename(tmp_path / "workdir-moved")
    (root / "workdir").symlink_to(outside)

    with pytest.raises(ContractError) as raised:
        authority.revalidate_before_use(result)
    assert raised.value.code is ErrorCode.SECURITY_DENIED
