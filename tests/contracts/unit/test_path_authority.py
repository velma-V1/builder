from pathlib import Path

from factory.contracts.validation.paths import PathAuthority


def _authority(tmp_path: Path) -> PathAuthority:
    return PathAuthority(project_root=tmp_path)


def test_allowed_path_within_allowed_glob_is_permitted(tmp_path: Path) -> None:
    authority = _authority(tmp_path)
    result = authority.evaluate(
        "src/factory/contracts/service.py",
        operation="write",
        allowed=["src/factory/contracts/**"],
        forbidden=[],
        read_only=[],
        active_exclusive_paths=[],
    )
    assert result.allowed
    assert result.normalized_relative == "src/factory/contracts/service.py"


def test_path_outside_allowed_globs_is_denied(tmp_path: Path) -> None:
    authority = _authority(tmp_path)
    result = authority.evaluate(
        "docs/other.md",
        operation="write",
        allowed=["src/factory/contracts/**"],
        forbidden=[],
        read_only=[],
        active_exclusive_paths=[],
    )
    assert not result.allowed


def test_forbidden_overrides_allowed(tmp_path: Path) -> None:
    authority = _authority(tmp_path)
    result = authority.evaluate(
        "src/factory/contracts/service.py",
        operation="write",
        allowed=["**"],
        forbidden=["src/factory/contracts/**"],
        read_only=[],
        active_exclusive_paths=[],
    )
    assert not result.allowed
    assert "forbidden" in result.reason


def test_read_only_denies_write_but_allows_read(tmp_path: Path) -> None:
    authority = _authority(tmp_path)
    write_result = authority.evaluate(
        "schemas/contracts/task/v1.schema.json",
        operation="write",
        allowed=["**"],
        forbidden=[],
        read_only=["schemas/**"],
        active_exclusive_paths=[],
    )
    assert not write_result.allowed

    read_result = authority.evaluate(
        "schemas/contracts/task/v1.schema.json",
        operation="read",
        allowed=["**"],
        forbidden=[],
        read_only=["schemas/**"],
        active_exclusive_paths=[],
    )
    assert read_result.allowed


def test_active_exclusive_ownership_denies_concurrent_write(tmp_path: Path) -> None:
    authority = _authority(tmp_path)
    result = authority.evaluate(
        "src/factory/contracts/service.py",
        operation="write",
        allowed=["**"],
        forbidden=[],
        read_only=[],
        active_exclusive_paths=["src/factory/contracts/**"],
    )
    assert not result.allowed
    assert "exclusive" in result.reason


def test_allowed_path_not_overriding_forbidden_or_protected(tmp_path: Path) -> None:
    authority = _authority(tmp_path)
    result = authority.evaluate(
        "docs/PROJECT_DEFINITION.md",
        operation="write",
        allowed=["docs/**"],
        forbidden=["docs/PROJECT_DEFINITION.md"],
        read_only=[],
        active_exclusive_paths=[],
    )
    assert not result.allowed


def test_star_matches_exactly_one_segment(tmp_path: Path) -> None:
    authority = _authority(tmp_path)
    matched = authority.evaluate(
        "contracts/tasks/PROJ-001/TASK-1/v1.yaml",
        operation="read",
        allowed=["contracts/*/*/*/*.yaml"],
        forbidden=[],
        read_only=[],
        active_exclusive_paths=[],
    )
    assert matched.allowed

    too_deep = authority.evaluate(
        "contracts/tasks/PROJ-001/TASK-1/extra/v1.yaml",
        operation="read",
        allowed=["contracts/*/*/*/*.yaml"],
        forbidden=[],
        read_only=[],
        active_exclusive_paths=[],
    )
    assert not too_deep.allowed


def test_double_star_matches_zero_or_more_segments(tmp_path: Path) -> None:
    authority = _authority(tmp_path)
    zero_segments = authority.evaluate(
        "src/file.py",
        operation="read",
        allowed=["src/**"],
        forbidden=[],
        read_only=[],
        active_exclusive_paths=[],
    )
    assert zero_segments.allowed

    many_segments = authority.evaluate(
        "src/a/b/c/file.py",
        operation="read",
        allowed=["src/**"],
        forbidden=[],
        read_only=[],
        active_exclusive_paths=[],
    )
    assert many_segments.allowed


def test_nonexistent_child_under_existing_directory_resolves(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    authority = _authority(tmp_path)
    result = authority.evaluate(
        "src/does/not/exist/yet.py",
        operation="write",
        allowed=["src/**"],
        forbidden=[],
        read_only=[],
        active_exclusive_paths=[],
    )
    assert result.allowed
    expected = tmp_path / "src" / "does" / "not" / "exist" / "yet.py"
    assert result.resolved_path == expected.resolve()


def test_revalidate_before_use_succeeds_when_unchanged(tmp_path: Path) -> None:
    authority = _authority(tmp_path)
    result = authority.evaluate(
        "src/file.py",
        operation="write",
        allowed=["src/**"],
        forbidden=[],
        read_only=[],
        active_exclusive_paths=[],
    )
    authority.revalidate_before_use(result)
