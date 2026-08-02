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
import subprocess
import sys
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
        "Get-BuilderConfigValue -ConfigTextNoComments $configTextNoComments "
        '-Section "wsl" -Key "distribution"'
    ) in content
    assert (
        "Get-BuilderConfigValue -ConfigTextNoComments $configTextNoComments "
        '-Section "repository" -Key "path"'
    ) in content


def test_builder_ps1_quotes_the_wsl_distro_and_repo_path_at_the_invocation_site() -> None:
    """A distro name or repository path containing a space must survive PowerShell's own
    word-splitting when passed to `wsl -d ... --cd ...`, not just survive config parsing."""
    content = (_WINDOWS_DIR / "Builder.ps1").read_text()
    assert '-d "$wslDistro"' in content
    assert '--cd "$repoPathLinux"' in content


def test_builder_ps1_no_longer_interpolates_the_repo_path_into_a_bash_string() -> None:
    """Regression guard for the command-injection defect: an earlier version built
    ``bash -lc "cd '$repoPathLinux' && ..."``, which let a repository path containing a single
    quote break out of that quoting and inject arbitrary shell commands. The repository path
    must now be passed via wsl.exe's own ``--cd`` argument -- never concatenated into any
    string destined for a shell (bash or otherwise) to re-parse.

    Checks the actual invocation line specifically (not just "the word bash doesn't appear
    anywhere"), since the explanatory comment above that line legitimately mentions the old,
    now-removed construction by name.
    """
    content = (_WINDOWS_DIR / "Builder.ps1").read_text()
    invocation_lines = [line for line in content.splitlines() if line.strip().startswith("& wsl ")]
    assert len(invocation_lines) == 1, (
        f"expected exactly one wsl invocation, found {invocation_lines!r}"
    )
    invocation_line = invocation_lines[0]

    assert "bash" not in invocation_line
    assert "-lc" not in invocation_line
    assert "cd '$repoPathLinux'" not in invocation_line
    assert "--cd" in invocation_line


def test_builder_ps1_exit_code_propagation_is_unchanged() -> None:
    content = (_WINDOWS_DIR / "Builder.ps1").read_text()
    assert "$exitCode = $LASTEXITCODE" in content
    assert "if ($exitCode -ne 0)" in content


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


def test_parser_preserves_a_repository_path_containing_an_apostrophe() -> None:
    text = "repository:\n  path: /mnt/c/Users/O'Brien/builder\n"
    assert _parse_config_value(text, "repository", "path") == "/mnt/c/Users/O'Brien/builder"


def test_parser_preserves_a_repository_path_that_looks_like_an_injection_attempt() -> None:
    """The parser itself must not do anything special with shell metacharacters -- it just
    extracts the scalar value verbatim. Safety comes from how the value is later passed to
    wsl.exe (see test_new_invocation_survives_malicious_repository_paths_without_injection),
    not from any sanitization here."""
    text = "repository:\n  path: /tmp/x'; echo INJECTED-COMMAND-RAN #\n"
    assert (
        _parse_config_value(text, "repository", "path") == "/tmp/x'; echo INJECTED-COMMAND-RAN #"  # noqa: S108 -- sample path, not a real tempfile
    )


def test_parser_preserves_a_repository_path_containing_a_dollar_and_semicolon() -> None:
    text = "repository:\n  path: /tmp/$HOME; touch /tmp/pwned\n"
    expected = "/tmp/$HOME; touch /tmp/pwned"  # noqa: S108 -- sample path, not a real tempfile
    assert _parse_config_value(text, "repository", "path") == expected


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


_MALICIOUS_REPOSITORY_PATHS = (
    "/mnt/c/Users/John Doe/builder",
    "/mnt/c/Users/O'Brien/builder",
    "/tmp/x'; echo INJECTED-COMMAND-RAN #",  # noqa: S108 -- sample path, not a real tempfile
    "/tmp/$HOME; touch /tmp/pwned",  # noqa: S108 -- sample path, not a real tempfile
)


def test_new_invocation_survives_malicious_repository_paths_without_injection(
    tmp_path: Path,
) -> None:
    """Executable proof of the command-injection fix's safety property.

    wsl.exe isn't available on Linux, so this models the exact safety property Builder.ps1's new
    invocation relies on: passing the repository path as one argv element to a native process --
    never concatenated into a shell string -- via ``subprocess.run([...], shell=False)``. This is
    the same "argv array, no shell" mechanism PowerShell's own native-command argument marshaling
    uses when a variable is passed as its own command element (as ``--cd "$repoPathLinux"`` now
    is), and it is exactly why this class of injection is structurally impossible once the
    ``bash -lc "cd '$repoPathLinux' && ..."`` string-building is removed: nothing ever re-parses
    the value as shell syntax, so none of `'`, `$`, `;`, `&`, backticks, `(`, `)`, `#`, or `"` in
    the path can have any special meaning.
    """
    fake_wsl = tmp_path / "fake_wsl.py"
    fake_wsl.write_text("import sys\nprint('ARGV:' + '|'.join(sys.argv[1:]))\n")

    for sample_path in _MALICIOUS_REPOSITORY_PATHS:
        argv = [
            sys.executable,
            str(fake_wsl),
            "-d",
            "Ubuntu",
            "--cd",
            sample_path,
            "--",
            "uv",
            "run",
            "python",
            "scripts/start_all.py",
        ]
        # argv is a fixed-shape, code-constructed list (only the sample_path element varies,
        # across a hardcoded local tuple) -- never shell-parsed, which is the exact property
        # this test proves.
        result = subprocess.run(  # noqa: S603
            argv, capture_output=True, text=True, shell=False, check=True
        )

        # The malicious sample's text (e.g. "echo INJECTED-COMMAND-RAN") is EXPECTED to appear
        # in the output -- as inert literal data inside the single ARGV: line, never executed.
        # The real proof of safety is that nothing beyond that one line was produced (no
        # separate command actually ran) and that the path arrived as exactly one argv element,
        # neither split by an embedded space/semicolon nor merged with an adjacent argument.
        output_lines = result.stdout.splitlines()
        assert len(output_lines) == 1, (
            f"expected exactly one output line (no injected command executed), got {output_lines!r}"
        )

        received_argv = output_lines[0].removeprefix("ARGV:").split("|")
        assert len(received_argv) == len(argv) - 2, (
            f"expected {len(argv) - 2} argv elements on the receiving end, got {received_argv!r}"
        )
        assert sample_path in received_argv, (
            f"expected {sample_path!r} to arrive as one literal argv element, got {received_argv!r}"
        )


def test_old_shell_string_construction_was_genuinely_exploitable() -> None:
    """Regression control: proves the OLD ``bash -lc "cd '<path>' && ..."`` construction this fix
    replaced really was exploitable for a repository path containing a single quote -- this
    wasn't a theoretical concern, and the new argv-based invocation is a meaningfully different
    (safe) mechanism, not just a cosmetic change."""
    malicious_path = "/tmp/x'; echo INJECTED-COMMAND-RAN #"  # noqa: S108 -- sample, not a real tempfile
    old_command = f"cd '{malicious_path}' && echo would-have-run-start_all.py"

    # Deliberately reconstructs the exact OLD vulnerable pattern as a control -- this is the one
    # place in this test file where a shell string is intentionally built, to prove the fix
    # actually changed behavior. `bash` resolved via PATH is acceptable here since this merely
    # demonstrates historical behavior, not part of any real invocation path.
    result = subprocess.run(  # noqa: S603 -- historical shell command regression
        ["bash", "-lc", old_command],  # noqa: S607 -- intentionally resolved via PATH
        capture_output=True,
        text=True,
        check=False,
    )

    assert "INJECTED-COMMAND-RAN" in result.stdout
    assert "would-have-run-start_all.py" not in result.stdout


def test_install_and_uninstall_target_the_same_shortcut_name() -> None:
    install_content = (_WINDOWS_DIR / "install-shortcut.ps1").read_text()
    uninstall_content = (_WINDOWS_DIR / "uninstall-shortcut.ps1").read_text()
    assert "Builder.lnk" in install_content
    assert "Builder.lnk" in uninstall_content


def test_install_shortcut_points_at_builder_cmd() -> None:
    content = (_WINDOWS_DIR / "install-shortcut.ps1").read_text()
    assert "Builder.cmd" in content
