"""PH-5 — quarantined staging (inspection gate, promotion authorization, process-tree kill)."""

from __future__ import annotations

from pathlib import Path

import pytest

from factory.staging import (
    FindingKind,
    QuarantinedStaging,
    StagedFile,
    StagingError,
    inspect,
    terminate_process_tree,
)


def _staging(tmp_path: Path) -> QuarantinedStaging:
    return QuarantinedStaging("stg-1", tmp_path, approved_scope=("src/**",))


def _file(path: str, content: bytes = b"clean", **over: object) -> StagedFile:
    base: dict[str, object] = dict(path=path, content=content, provenance="sbx-1")
    base.update(over)
    return StagedFile(**base)  # type: ignore[arg-type]


def test_clean_output_passes_inspection(tmp_path: Path) -> None:
    stg = _staging(tmp_path)
    stg.stage(_file("src/a.py", b"x = 1\n"))
    result = stg.inspect()
    assert result.clean
    assert result.records[0].content_hash


def test_promote_requires_clean_and_authorization(tmp_path: Path) -> None:
    stg = _staging(tmp_path)
    stg.stage(_file("src/a.py", b"x = 1\n"))
    with pytest.raises(StagingError) as exc:
        stg.promote(authorized=False)
    assert exc.value.code == "PROMOTION_UNAUTHORIZED"
    result = stg.promote(authorized=True)
    assert result.promoted


def test_staging_is_sealed_after_promotion(tmp_path: Path) -> None:
    stg = _staging(tmp_path)
    stg.stage(_file("src/a.py", b"x = 1\n"))
    stg.promote(authorized=True)
    with pytest.raises(StagingError) as exc:
        stg.stage(_file("src/b.py"))
    assert exc.value.code == "STAGING_SEALED"


@pytest.mark.security
def test_secret_in_output_blocks_promotion(tmp_path: Path) -> None:
    stg = _staging(tmp_path)
    stg.stage(_file("src/a.py", b"token = hunter2\n"))
    result = stg.inspect(secret_values=["hunter2"])
    assert not result.clean
    assert any(f.kind is FindingKind.SECRET for f in result.findings)
    with pytest.raises(StagingError) as exc:
        stg.promote(authorized=True, secret_values=["hunter2"])
    assert exc.value.code == "STAGING_UNCLEAN"


@pytest.mark.security
def test_executable_output_detected_by_suffix_and_shebang(tmp_path: Path) -> None:
    findings = inspect(
        [_file("src/run.sh", b"echo hi\n"), _file("src/tool", b"#!/bin/sh\n")],
        tmp_path,
        approved_scope=("src/**",),
    ).findings
    kinds = {f.kind for f in findings}
    assert FindingKind.UNEXPECTED_EXECUTABLE in kinds


@pytest.mark.security
def test_scope_violation_and_path_escape(tmp_path: Path) -> None:
    result = inspect(
        [_file("other/x.py", b"y = 1\n"), _file("../escape.py", b"z = 1\n")],
        tmp_path,
        approved_scope=("src/**",),
    )
    kinds = {f.kind for f in result.findings}
    assert FindingKind.SCOPE_VIOLATION in kinds
    assert FindingKind.PATH_ESCAPE in kinds


@pytest.mark.security
def test_archive_bomb_detected(tmp_path: Path) -> None:
    bomb = _file("src/big.bin", b"x" * 10, declared_uncompressed_size=100_000)
    result = inspect([bomb], tmp_path, approved_scope=("src/**",))
    assert any(f.kind is FindingKind.ARCHIVE_BOMB for f in result.findings)


def test_files_returns_staged_inventory(tmp_path: Path) -> None:
    stg = _staging(tmp_path)
    stg.stage(_file("src/a.py"))
    assert len(stg.files()) == 1


def test_process_tree_termination_is_complete() -> None:
    tree = {1: [2, 3], 2: [4], 3: [], 4: [5], 5: []}
    assert terminate_process_tree(tree, root=1) == (1, 2, 3, 4, 5)
    assert terminate_process_tree({}, root=9) == (9,)


def test_process_tree_dedupes_shared_descendants() -> None:
    # A diamond: pid 4 is reachable via both 2 and 3; it is terminated exactly once.
    tree = {1: [2, 3], 2: [4], 3: [4], 4: []}
    assert terminate_process_tree(tree, root=1) == (1, 2, 3, 4)


def test_staging_error_repr() -> None:
    err = StagingError("X", "y")
    assert "StagingError(code='X'" in repr(err)
    assert str(err) == "X: y"
