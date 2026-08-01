"""Phase 3A — Windows shortcut deliverable: validated where practical from this environment.

This session runs on Linux/WSL2, with no PowerShell interpreter available (confirmed: neither
``pwsh`` nor ``powershell`` is on PATH here) -- these tests cannot execute Builder.ps1,
install-shortcut.ps1, or uninstall-shortcut.ps1, and cannot create/verify a real Windows
``.lnk``. What they *do* verify:

1. every expected file exists and is non-empty;
2. brace/paren balance in the .ps1 files (catches a large class of copy-paste/edit mistakes);
3. Builder.ps1's regex extraction logic actually matches the real config/builder.yaml content,
   using an equivalent Python regex as a stand-in for the PowerShell ``[regex]::Match`` calls --
   this is the single most likely thing to silently break if config/builder.yaml's structure
   ever changes, since neither side uses a real YAML parser for this extraction.

Real `.lnk` creation/removal on Windows remains unverified from this environment and must be
checked on the Windows side -- this is stated explicitly, not silently skipped.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_WINDOWS_DIR = _REPO_ROOT / "scripts" / "windows"
_CONFIG_PATH = _REPO_ROOT / "config" / "builder.yaml"


def test_all_expected_windows_files_exist_and_are_non_empty() -> None:
    for filename in (
        "Builder.cmd",
        "Builder.ps1",
        "install-shortcut.ps1",
        "uninstall-shortcut.ps1",
    ):
        path = _WINDOWS_DIR / filename
        assert path.is_file(), f"missing: {path}"
        assert path.stat().st_size > 0, f"empty: {path}"


def test_builder_cmd_invokes_builder_ps1() -> None:
    content = (_WINDOWS_DIR / "Builder.cmd").read_text()
    assert "Builder.ps1" in content
    assert "powershell" in content.lower()


def test_builder_ps1_hands_off_to_start_all_inside_wsl() -> None:
    content = (_WINDOWS_DIR / "Builder.ps1").read_text()
    assert "scripts/start_all.py" in content
    assert "wsl" in content.lower()


def _brace_balance(text: str) -> bool:
    depth = 0
    for char in text:
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def test_powershell_scripts_have_balanced_braces() -> None:
    for filename in ("Builder.ps1", "install-shortcut.ps1", "uninstall-shortcut.ps1"):
        content = (_WINDOWS_DIR / filename).read_text()
        assert _brace_balance(content), f"unbalanced braces in {filename}"


def test_builder_ps1_regex_extraction_matches_the_real_config_file() -> None:
    """Mirrors Builder.ps1's comment-stripping + two [regex]::Match calls in Python -- a
    stand-in for actually running the PowerShell, which isn't possible in this environment.

    Regression coverage: an earlier, comment-unaware version of this regex matched the wrong
    "path:" (database.path instead of repository.path) once config/builder.yaml gained an
    explanatory comment line between "repository:" and "path:". This test would have caught
    that immediately.
    """
    config_text = _CONFIG_PATH.read_text()
    config_text_no_comments = re.sub(r"(?m)^\s*#.*$\r?\n?", "", config_text)

    distro_match = re.search(r"(?ms)^wsl:\s*\r?\n\s*distribution:\s*(\S+)", config_text_no_comments)
    path_match = re.search(
        r"(?ms)^repository:\s*\r?\n\s*path:\s*(\S+)", config_text_no_comments
    )

    assert distro_match is not None, "Builder.ps1's distro regex would not match builder.yaml"
    assert path_match is not None, (
        "Builder.ps1's repository-path regex would not match builder.yaml"
    )
    assert distro_match.group(1) == "Ubuntu"
    assert path_match.group(1) == "/home/xxthatguyxx/builder"


def test_builder_ps1_strips_comment_lines_before_matching() -> None:
    """Confirms Builder.ps1 itself actually performs the comment-stripping step (not just this
    test) -- i.e. this isn't a case of the test being correct while the real script regressed."""
    content = (_WINDOWS_DIR / "Builder.ps1").read_text()
    assert "regex]::Replace" in content
    assert "#.*" in content


def test_install_and_uninstall_target_the_same_shortcut_name() -> None:
    install_content = (_WINDOWS_DIR / "install-shortcut.ps1").read_text()
    uninstall_content = (_WINDOWS_DIR / "uninstall-shortcut.ps1").read_text()
    assert "Builder.lnk" in install_content
    assert "Builder.lnk" in uninstall_content


def test_install_shortcut_points_at_builder_cmd() -> None:
    content = (_WINDOWS_DIR / "install-shortcut.ps1").read_text()
    assert "Builder.cmd" in content
