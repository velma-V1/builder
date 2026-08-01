"""Phase 3A — Windows shortcut deliverable: validated where practical from this environment.

This session runs on Linux/WSL2, with no PowerShell interpreter available (confirmed: neither
``pwsh`` nor ``powershell`` is on PATH here) -- these tests cannot execute Builder.ps1,
install-shortcut.ps1, or uninstall-shortcut.ps1, and cannot create/verify a real Windows
``.lnk``. What they *do* verify:

1. every expected file exists and is non-empty;
2. brace/paren balance in the .ps1 files (catches a large class of copy-paste/edit mistakes);
3. Builder.ps1's ``Get-BuilderConfigValue`` section-aware config parser, reimplemented in Python
   as a deterministic stand-in for the PowerShell function -- this is the single most likely
   thing to silently break if config/builder.yaml's structure ever changes, since neither side
   uses a real YAML parser for this extraction.

Real `.lnk` creation/removal on Windows remains unverified from this environment and must be
checked on the Windows side -- this is stated explicitly, not silently skipped.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_WINDOWS_DIR = _REPO_ROOT / "scripts" / "windows"
_CONFIG_PATH = _REPO_ROOT / "config" / "builder.yaml"


def _strip_comment_lines(text: str) -> str:
    """Python mirror of Builder.ps1's comment-stripping regex replace.

    Same helper as Builder.ps1: strips whole comment-only lines before matching.
    """
    return re.sub(r"(?m)^\s*#.*$\r?\n?", "", text)


def _parse_config_value(config_text_no_comments: str, section: str, key: str) -> str | None:
    """Python mirror of Builder.ps1's ``Get-BuilderConfigValue`` function, line for line.

    Returns ``None`` under exactly the conditions that function returns ``$null``: the section
    header isn't found, the key isn't found before the next top-level line, or the resolved
    value is blank after unquoting -- never raises.
    """
    lines = re.split(r"\r?\n", config_text_no_comments)
    section_header_pattern = re.compile(rf"^{re.escape(section)}:\s*$")
    key_line_pattern = re.compile(rf"^\s+{re.escape(key)}:\s*(.*)$")

    in_section = False
    raw_value: str | None = None

    for line in lines:
        if not in_section:
            if section_header_pattern.match(line):
                in_section = True
            continue

        if re.match(r"^\S", line):
            # A new top-level (non-indented) line ends this section.
            break

        match = key_line_pattern.match(line)
        if match:
            raw_value = match.group(1)
            break

    if raw_value is None:
        return None

    trimmed = raw_value.strip()
    if len(trimmed) >= 2:
        first_char, last_char = trimmed[0], trimmed[-1]
        is_quoted = (first_char == '"' and last_char == '"') or (
            first_char == "'" and last_char == "'"
        )
        if is_quoted:
            trimmed = trimmed[1:-1].strip()

    if trimmed == "":
        return None

    return trimmed


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


def test_builder_ps1_uses_the_section_aware_parser_not_a_bare_word_regex() -> None:
    """Regression guard: an earlier version used a ``\\S+`` capture for wsl.distribution /
    repository.path, which silently truncated any value containing a space. Confirms the
    section-aware ``Get-BuilderConfigValue`` helper is what Builder.ps1 actually calls now."""
    content = (_WINDOWS_DIR / "Builder.ps1").read_text()
    assert "function Get-BuilderConfigValue" in content
    assert (
        'Get-BuilderConfigValue -ConfigTextNoComments $configTextNoComments '
        '-Section "wsl" -Key "distribution"'
    ) in content
    assert (
        'Get-BuilderConfigValue -ConfigTextNoComments $configTextNoComments '
        '-Section "repository" -Key "path"'
    ) in content


def test_builder_ps1_quotes_the_wsl_distro_at_the_invocation_site() -> None:
    """A distro name containing a space must survive PowerShell's own word-splitting when
    passed to `wsl -d ...`, not just survive config parsing."""
    content = (_WINDOWS_DIR / "Builder.ps1").read_text()
    assert '-d "$wslDistro"' in content


def test_builder_ps1_strips_comment_lines_before_matching() -> None:
    """Confirms Builder.ps1 itself actually performs the comment-stripping step (not just this
    test) -- i.e. this isn't a case of the test being correct while the real script regressed."""
    content = (_WINDOWS_DIR / "Builder.ps1").read_text()
    assert "regex]::Replace" in content
    assert "#.*" in content


def test_parser_matches_the_real_config_file() -> None:
    """Regression coverage: an earlier, comment-unaware version of the extraction matched the
    wrong "path:" (database.path instead of repository.path) once config/builder.yaml gained an
    explanatory comment line between "repository:" and "path:". This test would have caught
    that immediately, and still would if the real file regressed."""
    config_text_no_comments = _strip_comment_lines(_CONFIG_PATH.read_text())

    distro = _parse_config_value(config_text_no_comments, "wsl", "distribution")
    path = _parse_config_value(config_text_no_comments, "repository", "path")

    assert distro == "Ubuntu"
    assert path == "/home/xxthatguyxx/builder"


def test_parser_preserves_a_plain_unquoted_value() -> None:
    text = _strip_comment_lines("wsl:\n  distribution: Ubuntu\n")
    assert _parse_config_value(text, "wsl", "distribution") == "Ubuntu"


def test_parser_preserves_a_distribution_name_containing_spaces() -> None:
    text = "wsl:\n  distribution: Ubuntu 22.04 LTS\n"
    assert _parse_config_value(text, "wsl", "distribution") == "Ubuntu 22.04 LTS"


def test_parser_preserves_a_plain_repository_path() -> None:
    text = "repository:\n  path: /home/xxthatguyxx/builder\n"
    assert _parse_config_value(text, "repository", "path") == "/home/xxthatguyxx/builder"


def test_parser_preserves_a_repository_path_containing_a_space() -> None:
    """The exact defect this fix addresses: a WSL-mounted Windows path with a space in the
    username, e.g. a real Windows profile directory like "John Doe"."""
    text = "repository:\n  path: /mnt/c/Users/John Doe/builder\n"
    assert _parse_config_value(text, "repository", "path") == "/mnt/c/Users/John Doe/builder"


def test_parser_unwraps_a_double_quoted_value_containing_spaces() -> None:
    text = 'repository:\n  path: "/mnt/c/Users/John Doe/builder"\n'
    assert _parse_config_value(text, "repository", "path") == "/mnt/c/Users/John Doe/builder"


def test_parser_unwraps_a_single_quoted_value_containing_spaces() -> None:
    text = "repository:\n  path: '/mnt/c/Users/John Doe/builder'\n"
    assert _parse_config_value(text, "repository", "path") == "/mnt/c/Users/John Doe/builder"


def test_parser_skips_a_comment_between_section_and_key() -> None:
    text = _strip_comment_lines(
        "repository:\n"
        "  # Path to this repository, as seen from inside the configured WSL distribution.\n"
        "  path: /home/xxthatguyxx/builder\n"
    )
    assert _parse_config_value(text, "repository", "path") == "/home/xxthatguyxx/builder"


def test_parser_does_not_match_a_similarly_named_key_in_an_unrelated_section() -> None:
    """The bug this whole fix originated from: an earlier cross-line regex matched
    database.path instead of repository.path once a comment line separated the two."""
    text = "repository:\n  path: /home/xxthatguyxx/builder\n\ndatabase:\n  path: runtime.db\n"
    assert _parse_config_value(text, "repository", "path") == "/home/xxthatguyxx/builder"
    assert _parse_config_value(text, "database", "path") == "runtime.db"


def test_parser_returns_none_for_a_missing_required_key() -> None:
    text = "repository:\n  not_path: /home/xxthatguyxx/builder\n"
    assert _parse_config_value(text, "repository", "path") is None


def test_parser_returns_none_for_a_missing_section() -> None:
    text = "database:\n  path: runtime.db\n"
    assert _parse_config_value(text, "repository", "path") is None


def test_parser_returns_none_for_a_blank_required_value() -> None:
    text = "repository:\n  path:\n"
    assert _parse_config_value(text, "repository", "path") is None


def test_parser_returns_none_for_a_whitespace_only_value() -> None:
    text = "repository:\n  path:    \n"
    assert _parse_config_value(text, "repository", "path") is None


def test_install_and_uninstall_target_the_same_shortcut_name() -> None:
    install_content = (_WINDOWS_DIR / "install-shortcut.ps1").read_text()
    uninstall_content = (_WINDOWS_DIR / "uninstall-shortcut.ps1").read_text()
    assert "Builder.lnk" in install_content
    assert "Builder.lnk" in uninstall_content


def test_install_shortcut_points_at_builder_cmd() -> None:
    content = (_WINDOWS_DIR / "install-shortcut.ps1").read_text()
    assert "Builder.cmd" in content
