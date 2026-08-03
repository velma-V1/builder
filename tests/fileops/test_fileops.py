"""RPH3-T5 — safe file-op service: path safety #10, Decision B delete, archive limits, atomicity."""

from __future__ import annotations

import zipfile
from collections.abc import Callable
from pathlib import Path

import pytest

from factory.approval import (
    ApprovalEngine,
    ApprovalRequest,
    DecisionKind,
    OperatorDecision,
    action_fingerprint,
)
from factory.audit import AuditValidator, AuditWriter, RecordKind
from factory.fileops import ArchiveLimits, FileOpError, FileOpService
from factory.permission import PermissionGrant, TaskAuthority

pytestmark = pytest.mark.security

GrantFactory = Callable[[str], PermissionGrant]


def _delete_approval(approval_engine: ApprovalEngine, resource: str) -> tuple[object, str]:
    card = approval_engine.enqueue(
        ApprovalRequest(
            task_id="task-1",
            tool="fs",
            action="delete",
            scope="src",
            purpose="cleanup",
            consequences="removes a file",
            autonomy_level="L2-supervised",
            ttl_seconds=100,
            resource=resource,
            destructive=True,
        )
    )
    record = approval_engine.decide(
        card.approval_id,
        OperatorDecision(decision=DecisionKind.GRANT, operator="op", confirmed_destructive=True),
    )
    fingerprint = action_fingerprint(
        task_id="task-1", tool="fs", action="delete", resource=resource, scope="src"
    )
    return record, fingerprint


def test_write_atomic_and_read(
    service: FileOpService, authority: TaskAuthority, project_root: Path, write_grant: GrantFactory
) -> None:
    grant = write_grant("src/new.txt")
    result = service.write_atomic("src/new.txt", b"hello", authority, grant)
    assert result.canonical_path == "src/new.txt"
    assert (project_root / "src" / "new.txt").read_bytes() == b"hello"
    assert service.read("src/new.txt", authority, grant) == b"hello"


@pytest.mark.parametrize(
    "bad", ["../escape.txt", "/etc/passwd", "src/main.py:ads", "src/CON", "src/x\x00y"]
)
def test_path_escapes_denied(
    service: FileOpService, authority: TaskAuthority, write_grant: GrantFactory, bad: str
) -> None:
    grant = write_grant("src/main.py")
    with pytest.raises(FileOpError) as exc:
        service.write_atomic(bad, b"x", authority, grant)
    assert exc.value.code == "FILEOP_PATH_ESCAPE"


def test_write_to_read_only_path_denied(
    service: FileOpService, authority: TaskAuthority, permission_engine: object
) -> None:
    from factory.permission import ActionRequest, PermissionClass

    # README.md is read-only for writes; a WRITE decision is denied upstream, but even a forged
    # grant is contained by the file-op path authority.
    decision = permission_engine.decide(  # type: ignore[attr-defined]
        ActionRequest(
            task_id="task-1",
            tool="fs",
            action="w",
            permission_class=PermissionClass.WRITE,
            scope="src",
            purpose="p",
            resource="src/main.py",
        ),
        authority,
    )
    grant = permission_engine.issue_grant(decision, 100)  # type: ignore[attr-defined]
    with pytest.raises(FileOpError) as exc:
        service.write_atomic("README.md", b"x", authority, grant)
    assert exc.value.code == "FILEOP_PATH_ESCAPE"


def test_delete_requires_valid_approval_decision_b(
    service: FileOpService,
    authority: TaskAuthority,
    approval_engine: ApprovalEngine,
    project_root: Path,
) -> None:
    (project_root / "src" / "g.txt").write_text("g")
    record, _fingerprint = _delete_approval(approval_engine, "src/g.txt")
    # a wrong fingerprint means the approval is NOT consumed → deletion denied (no delete path)
    with pytest.raises(FileOpError) as exc:
        service.delete("src/g.txt", authority, record, "wrong-fingerprint")  # type: ignore[arg-type]
    assert exc.value.code == "FILEOP_DELETE_REQUIRES_APPROVAL"
    assert (project_root / "src" / "g.txt").exists()  # still there


def test_delete_with_valid_approval_is_class3_audited(
    service: FileOpService,
    authority: TaskAuthority,
    approval_engine: ApprovalEngine,
    project_root: Path,
    clock: object,
) -> None:
    target = project_root / "src" / "d.txt"
    target.write_text("d")
    record, fingerprint = _delete_approval(approval_engine, "src/d.txt")
    result = service.delete("src/d.txt", authority, record, fingerprint)  # type: ignore[arg-type]
    assert result.deleted is True
    assert not target.exists()
    # Class-3: exactly one INTENT + one COMPLETION audit for the delete op, joined by op_key
    records = AuditWriter(database_path=service.audit_database_path).export()
    delete_ops = [r for r in records if r.action_class == "fileop.delete"]
    by_op: dict[str, set[RecordKind]] = {}
    for r in delete_ops:
        by_op.setdefault(r.op_key, set()).add(r.record_kind)
    assert any(k == {RecordKind.INTENT, RecordKind.COMPLETION} for k in by_op.values())
    assert AuditValidator(database_path=service.audit_database_path).verify_chain().valid is True


def test_archive_entry_count_capped(
    service: FileOpService, authority: TaskAuthority, project_root: Path
) -> None:
    arc = project_root / "src" / "a.zip"
    with zipfile.ZipFile(arc, "w") as z:
        for i in range(5):
            z.writestr(f"e{i}.txt", "x" * 10)
    with pytest.raises(FileOpError) as exc:
        service.extract_archive(
            "src/a.zip",
            "src/out",
            ArchiveLimits(max_entries=3, max_depth=5, max_total_bytes=99999),
            authority,
        )
    assert exc.value.code == "FILEOP_ARCHIVE_LIMIT"


def test_archive_decompressed_size_capped(
    service: FileOpService, authority: TaskAuthority, project_root: Path
) -> None:
    arc = project_root / "src" / "b.zip"
    with zipfile.ZipFile(arc, "w") as z:
        z.writestr("big.txt", "x" * 10000)
    with pytest.raises(FileOpError) as exc:
        service.extract_archive(
            "src/b.zip",
            "src/out2",
            ArchiveLimits(max_entries=10, max_depth=5, max_total_bytes=100),
            authority,
        )
    assert exc.value.code == "FILEOP_ARCHIVE_LIMIT"


def test_archive_zip_slip_blocked(
    service: FileOpService, authority: TaskAuthority, project_root: Path
) -> None:
    arc = project_root / "src" / "c.zip"
    with zipfile.ZipFile(arc, "w") as z:
        z.writestr("../../evil.txt", "pwned")
    with pytest.raises(FileOpError) as exc:
        service.extract_archive(
            "src/c.zip",
            "src/out3",
            ArchiveLimits(max_entries=10, max_depth=9, max_total_bytes=99999),
            authority,
        )
    assert exc.value.code in {"FILEOP_ARCHIVE_ESCAPE", "FILEOP_ARCHIVE_LIMIT"}


def test_archive_valid_extract(
    service: FileOpService, authority: TaskAuthority, project_root: Path
) -> None:
    arc = project_root / "src" / "ok.zip"
    with zipfile.ZipFile(arc, "w") as z:
        z.writestr("a/b.txt", "hello")
    result = service.extract_archive(
        "src/ok.zip",
        "src/dest",
        ArchiveLimits(max_entries=10, max_depth=5, max_total_bytes=99999),
        authority,
    )
    assert result.entries == 1
    assert (project_root / "src" / "dest" / "a" / "b.txt").read_text() == "hello"


def test_bad_archive_rejected(
    service: FileOpService, authority: TaskAuthority, project_root: Path
) -> None:
    (project_root / "src" / "notzip.zip").write_text("not a zip")
    with pytest.raises(FileOpError) as exc:
        service.extract_archive(
            "src/notzip.zip",
            "src/out4",
            ArchiveLimits(max_entries=10, max_depth=5, max_total_bytes=99999),
            authority,
        )
    assert exc.value.code == "FILEOP_ARCHIVE_INVALID"


def test_canonicalize_and_escape(service: FileOpService, authority: TaskAuthority) -> None:
    assert service.canonicalize("src/./main.py", authority) == "src/main.py"
    with pytest.raises(FileOpError):
        service.canonicalize("../outside", authority)


def test_read_without_valid_grant_denied(
    service: FileOpService,
    authority: TaskAuthority,
    write_grant: GrantFactory,
    permission_engine: object,
) -> None:
    grant = write_grant("src/main.py")
    permission_engine.revoke(grant.grant_id)  # type: ignore[attr-defined]
    with pytest.raises(FileOpError) as exc:
        service.read("src/main.py", authority, grant)
    assert exc.value.code == "FILEOP_DENIED"
