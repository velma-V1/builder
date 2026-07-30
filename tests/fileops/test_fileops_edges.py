"""RPH3-T5 — file-op edge/error branches (read/write/delete OS failures, error str, dir entry)."""

from __future__ import annotations

import zipfile
from collections.abc import Callable
from pathlib import Path

import pytest

from factory.approval import (
    ApprovalEngine,
    ApprovalRecord,
    ApprovalRequest,
    DecisionKind,
    OperatorDecision,
    action_fingerprint,
)
from factory.fileops import ArchiveLimits, FileOpError, FileOpService
from factory.permission import PermissionGrant, TaskAuthority

GrantFactory = Callable[[str], PermissionGrant]


def test_fileop_error_str() -> None:
    assert str(FileOpError("CODE", "msg")) == "CODE: msg"


def test_read_missing_file_fails(
    service: FileOpService, authority: TaskAuthority, write_grant: GrantFactory
) -> None:
    grant = write_grant("src/nope.txt")
    with pytest.raises(FileOpError) as exc:
        service.read("src/nope.txt", authority, grant)
    assert exc.value.code == "FILEOP_READ_FAILED"


def test_write_over_directory_fails(
    service: FileOpService, authority: TaskAuthority, project_root: Path, write_grant: GrantFactory
) -> None:
    (project_root / "src" / "adir").mkdir()
    grant = write_grant("src/adir")
    with pytest.raises(FileOpError) as exc:
        service.write_atomic("src/adir", b"x", authority, grant)
    assert exc.value.code == "FILEOP_WRITE_FAILED"


def test_delete_of_directory_fails(
    service: FileOpService, authority: TaskAuthority, approval_engine: ApprovalEngine,
    project_root: Path,
) -> None:
    (project_root / "src" / "ddir").mkdir()
    card = approval_engine.enqueue(
        ApprovalRequest(
            task_id="task-1", tool="fs", action="delete", scope="src", purpose="c",
            consequences="x", autonomy_level="L2-supervised", ttl_seconds=100, resource="src/ddir",
            destructive=True,
        )
    )
    record = approval_engine.decide(
        card.approval_id,
        OperatorDecision(decision=DecisionKind.GRANT, operator="op", confirmed_destructive=True),
    )
    assert isinstance(record, ApprovalRecord)
    fingerprint = action_fingerprint(
        task_id="task-1", tool="fs", action="delete", resource="src/ddir", scope="src"
    )
    with pytest.raises(FileOpError) as exc:
        service.delete("src/ddir", authority, record, fingerprint)
    assert exc.value.code == "FILEOP_DELETE_FAILED"


def test_archive_with_directory_entry(
    service: FileOpService, authority: TaskAuthority, project_root: Path
) -> None:
    arc = project_root / "src" / "withdir.zip"
    with zipfile.ZipFile(arc, "w") as z:
        z.writestr("subdir/", "")  # a directory entry
        z.writestr("subdir/f.txt", "hi")
    result = service.extract_archive(
        "src/withdir.zip", "src/od",
        ArchiveLimits(max_entries=10, max_depth=5, max_total_bytes=999), authority,
    )
    assert result.entries == 1  # only the file counted; the dir entry skipped
    assert (project_root / "src" / "od" / "subdir" / "f.txt").read_text() == "hi"
