"""The safe file-op service (CMP-FILEOP, roadmap PH-3 / RPH3-T5).

The single safe path for file operations. Every raw path is canonicalized + contained (reusing
the tested ``PathAuthority``); every escape class is blocked. Decision B is absolute: ``delete``
has **no** path without a valid CMP-APPROVAL (consumed single-use); the delete is a XSC-RPH3
**Class-3** op (durable INTENT before the effect, COMPLETION after). Writes are atomic (temp +
rename — no partial file on interruption) and bounded to scope. Archive extraction is capped on
entry-count / nesting-depth / decompressed-size (archive-bomb defense) and blocks zip-slip escapes.
"""

from __future__ import annotations

import hashlib
import os
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path

from factory.approval import ApprovalEngine, ApprovalRecord
from factory.audit import AuditEvent, AuditWriter, RecordKind
from factory.contracts.validation.paths import PathAuthority
from factory.fileops.errors import FileOpError
from factory.fileops.models import ArchiveLimits, DeleteResult, ExtractResult, WriteResult
from factory.permission import Clock, PermissionEngine, PermissionGrant, TaskAuthority

_SEP = "\x1f"

_CLASS_OPERATION = {"read": "read", "write": "write", "delete": "delete"}


@dataclass(frozen=True, slots=True)
class FileOpService:
    permission_engine: PermissionEngine
    approval_engine: ApprovalEngine
    audit_database_path: Path
    clock: Clock

    # --- path authority --------------------------------------------------------------------------

    def _validate(self, raw_path: str, authority: TaskAuthority, operation: str) -> Path:
        path_authority = PathAuthority(project_root=Path(authority.project_root))
        result = path_authority.evaluate(
            raw_path, operation=operation,
            allowed=authority.allowed_paths or ("**",),
            forbidden=authority.forbidden_paths,
            read_only=authority.read_only_paths,
            active_exclusive_paths=authority.exclusive_paths,
        )
        if not result.allowed:
            raise FileOpError("FILEOP_PATH_ESCAPE", f"path denied: {result.reason}")
        return result.resolved_path

    def canonicalize(self, raw_path: str, authority: TaskAuthority) -> str:
        """Canonicalize + contain a raw path; raise on any escape class."""
        path_authority = PathAuthority(project_root=Path(authority.project_root))
        result = path_authority.evaluate(
            raw_path, operation="read", allowed=("**",),
            forbidden=authority.forbidden_paths, read_only=(), active_exclusive_paths=(),
        )
        if not result.allowed:
            raise FileOpError("FILEOP_PATH_ESCAPE", f"path denied: {result.reason}")
        return result.normalized_relative

    # --- read / write ----------------------------------------------------------------------------

    def read(self, raw_path: str, authority: TaskAuthority, grant: PermissionGrant) -> bytes:
        if not self.permission_engine.revalidate(grant, self.clock.now_ts()):
            raise FileOpError("FILEOP_DENIED", "no valid permission grant at use time")
        resolved = self._validate(raw_path, authority, "read")
        try:
            return resolved.read_bytes()
        except OSError as exc:
            raise FileOpError("FILEOP_READ_FAILED", f"read failed: {exc}") from exc

    def write_atomic(
        self, raw_path: str, data: bytes, authority: TaskAuthority, grant: PermissionGrant
    ) -> WriteResult:
        if not self.permission_engine.revalidate(grant, self.clock.now_ts()):
            raise FileOpError("FILEOP_DENIED", "no valid permission grant at use time")
        resolved = self._validate(raw_path, authority, "write")
        resolved.parent.mkdir(parents=True, exist_ok=True)
        tmp = resolved.parent / f".{resolved.name}.{uuid.uuid4().hex}.tmp"
        try:
            tmp.write_bytes(data)
            os.replace(tmp, resolved)  # atomic on POSIX; no partial target on interruption
        except OSError as exc:
            tmp.unlink(missing_ok=True)
            raise FileOpError("FILEOP_WRITE_FAILED", f"atomic write failed: {exc}") from exc
        rel = self._relative(resolved, authority)
        return WriteResult(canonical_path=rel, bytes_written=len(data))

    # --- delete (Decision B — approval mandatory; Class-3) ---------------------------------------

    def delete(
        self,
        raw_path: str,
        authority: TaskAuthority,
        approval: ApprovalRecord,
        action_fingerprint: str,
    ) -> DeleteResult:
        """Delete a file. There is NO path here without a valid, consumed approval (Decision B)."""
        resolved = self._validate(raw_path, authority, "delete")
        # Decision B: the delete is authorized ONLY by consuming a valid approval (single-use).
        if not self.approval_engine.consume(approval, action_fingerprint):
            raise FileOpError(
                "FILEOP_DELETE_REQUIRES_APPROVAL",
                "deletion requires a valid CMP-APPROVAL (Decision B)",
            )
        rel = self._relative(resolved, authority)
        op_key = hashlib.sha256(
            f"delete{_SEP}{rel}{_SEP}{uuid.uuid4().hex}".encode()
        ).hexdigest()
        payload = hashlib.sha256(rel.encode()).hexdigest()
        writer = AuditWriter(database_path=self.audit_database_path)
        # Class-3: durable INTENT before the irreversible effect.
        writer.append(
            AuditEvent(
                op_key=op_key, record_kind=RecordKind.INTENT, operation_class=3, actor="cmp-fileop",
                action_class="fileop.delete", payload_hash=payload,
                occurred_at=self.clock.now_iso(), target_ref=rel,
            )
        )
        try:
            resolved.unlink()
        except OSError as exc:
            raise FileOpError("FILEOP_DELETE_FAILED", f"delete failed: {exc}") from exc
        # Class-3: COMPLETION after the proven effect.
        writer.append(
            AuditEvent(
                op_key=op_key, record_kind=RecordKind.COMPLETION, operation_class=3,
                actor="cmp-fileop", action_class="fileop.delete", payload_hash=payload,
                occurred_at=self.clock.now_iso(), target_ref=rel,
            )
        )
        return DeleteResult(canonical_path=rel, deleted=True)

    # --- archive extraction (bomb + zip-slip defense) --------------------------------------------

    def extract_archive(
        self, archive_path: str, dest: str, limits: ArchiveLimits, authority: TaskAuthority
    ) -> ExtractResult:
        archive = self._validate(archive_path, authority, "read")
        dest_resolved = self._validate(dest, authority, "write")
        dest_resolved.mkdir(parents=True, exist_ok=True)
        dest_authority = PathAuthority(project_root=dest_resolved)
        total = 0
        count = 0
        try:
            with zipfile.ZipFile(archive) as zf:
                infos = zf.infolist()
                if len(infos) > limits.max_entries:
                    raise FileOpError(
                        "FILEOP_ARCHIVE_LIMIT", f"archive entry count exceeds {limits.max_entries}"
                    )
                for info in infos:
                    name = info.filename
                    depth = len([s for s in name.replace("\\", "/").split("/") if s and s != "."])
                    if depth > limits.max_depth:
                        raise FileOpError(
                            "FILEOP_ARCHIVE_LIMIT", f"archive nesting exceeds {limits.max_depth}"
                        )
                    # zip-slip: every entry must stay contained under dest.
                    entry = dest_authority.evaluate(
                        name, operation="write", allowed=("**",), forbidden=(), read_only=(),
                        active_exclusive_paths=(),
                    )
                    if not entry.allowed:
                        raise FileOpError(
                            "FILEOP_ARCHIVE_ESCAPE", f"archive entry escapes dest: {entry.reason}"
                        )
                    total += info.file_size
                    if total > limits.max_total_bytes:
                        raise FileOpError(
                            "FILEOP_ARCHIVE_LIMIT",
                            f"decompressed size exceeds {limits.max_total_bytes}",
                        )
                    if not info.is_dir():
                        target = dest_resolved / entry.normalized_relative
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with zf.open(info) as src:
                            target.write_bytes(src.read())
                        count += 1
        except zipfile.BadZipFile as exc:
            raise FileOpError("FILEOP_ARCHIVE_INVALID", f"bad archive: {exc}") from exc
        return ExtractResult(dest=self._relative(dest_resolved, authority), entries=count,
                             total_bytes=total)

    @staticmethod
    def _relative(resolved: Path, authority: TaskAuthority) -> str:
        root = Path(authority.project_root).resolve()
        try:
            return resolved.resolve().relative_to(root).as_posix()
        except ValueError:  # pragma: no cover - _validate already contained it
            return resolved.name


__all__ = ["FileOpService"]
