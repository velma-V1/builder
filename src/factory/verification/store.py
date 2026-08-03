"""Persistence for Phase 3B's evidence packages and promotion manifests -- the same authoritative
``runtime.db`` as the orchestrator (``migrations/runtime/0007_verification_promotion.sql``), never
a second database. Mirrors the exact transactional-writer / read-only-reader pattern already
established by ``factory.orchestrator.store.runtime_state`` and ``factory.worker_engine.store``.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from factory.contracts.activation.store import _reader_authorizer
from factory.verification.errors import VerificationStoreError
from factory.verification.models import (
    EvidenceItem,
    EvidencePackage,
    ManifestFile,
    PromotionManifest,
    evidence_package_json,
    promotion_manifest_json,
)


def _utcnow() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _connect_readonly(database_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{database_path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.set_authorizer(_reader_authorizer)
    return connection


def _row_to_evidence_package(row: sqlite3.Row) -> EvidencePackage:
    try:
        payload = json.loads(row["package_json"])
        if set(payload) != {"schema_version", "items"} or payload["schema_version"] != 1:
            raise ValueError("unsupported evidence schema")
        items = tuple(EvidenceItem(**item) for item in payload["items"])
        package = EvidencePackage(
            task_id=row["task_id"], run_id=row["run_id"], items=items, created_at=row["created_at"]
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise VerificationStoreError("EVIDENCE_SCHEMA_INVALID", str(exc)) from exc
    if package.digest() != row["package_digest"]:
        raise VerificationStoreError("EVIDENCE_DIGEST_MISMATCH", "stored evidence digest differs")
    return package


def _row_to_manifest(row: sqlite3.Row) -> PromotionManifest:
    try:
        payload = json.loads(row["manifest_json"])
        if set(payload) != {"schema_version", "files"} or payload["schema_version"] != 1:
            raise ValueError("unsupported manifest schema")
        files = tuple(ManifestFile(**item) for item in payload["files"])
        manifest = PromotionManifest(
            task_id=row["task_id"],
            run_id=row["run_id"],
            branch_ref=row["branch_ref"],
            base_sha=row["base_sha"],
            files=files,
            created_at=row["created_at"],
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise VerificationStoreError("MANIFEST_SCHEMA_INVALID", str(exc)) from exc
    if manifest.digest() != row["manifest_digest"]:
        raise VerificationStoreError("MANIFEST_DIGEST_MISMATCH", "stored manifest digest differs")
    return manifest


_SELECT_EVIDENCE_BY_TASK_SQL = (
    "SELECT task_id, run_id, package_json, package_digest, outcome, created_at "
    "FROM evidence_packages WHERE task_id = ? ORDER BY package_id DESC LIMIT 1"
)
_SELECT_MANIFEST_BY_TASK_SQL = (
    "SELECT task_id, run_id, manifest_json, manifest_digest, base_sha, branch_ref, "
    "checkpoint_commit_sha, created_at FROM promotion_manifests "
    "WHERE task_id = ? ORDER BY manifest_id DESC LIMIT 1"
)
_INSERT_EVIDENCE_SQL = (
    "INSERT INTO evidence_packages (task_id, run_id, package_json, package_digest, outcome, "
    "created_at) VALUES (?, ?, ?, ?, ?, ?)"
)
_INSERT_MANIFEST_SQL = (
    "INSERT INTO promotion_manifests (task_id, run_id, manifest_json, manifest_digest, "
    "base_sha, branch_ref, checkpoint_commit_sha, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
)
_SELECT_EVIDENCE_BY_RUN_SQL = (
    "SELECT task_id, run_id, package_json, package_digest, outcome, created_at "
    "FROM evidence_packages WHERE run_id = ?"
)
_SELECT_MANIFEST_BY_RUN_SQL = (
    "SELECT task_id, run_id, manifest_json, manifest_digest, base_sha, branch_ref, "
    "checkpoint_commit_sha, created_at FROM promotion_manifests WHERE run_id = ?"
)


class VerificationReader(Protocol):
    def get_latest_evidence(self, task_id: str) -> EvidencePackage | None: ...
    def get_latest_manifest(self, task_id: str) -> PromotionManifest | None: ...
    def get_manifest_checkpoint_commit(self, task_id: str) -> str | None: ...


@dataclass(frozen=True, slots=True)
class SQLiteVerificationReader:
    database_path: Path

    def get_latest_evidence(self, task_id: str) -> EvidencePackage | None:
        connection = _connect_readonly(self.database_path)
        try:
            row = connection.execute(_SELECT_EVIDENCE_BY_TASK_SQL, (task_id,)).fetchone()
        finally:
            connection.close()
        return None if row is None else _row_to_evidence_package(row)

    def get_latest_manifest(self, task_id: str) -> PromotionManifest | None:
        connection = _connect_readonly(self.database_path)
        try:
            row = connection.execute(_SELECT_MANIFEST_BY_TASK_SQL, (task_id,)).fetchone()
        finally:
            connection.close()
        return None if row is None else _row_to_manifest(row)

    def get_manifest_checkpoint_commit(self, task_id: str) -> str | None:
        connection = _connect_readonly(self.database_path)
        try:
            row = connection.execute(_SELECT_MANIFEST_BY_TASK_SQL, (task_id,)).fetchone()
        finally:
            connection.close()
        return None if row is None else str(row["checkpoint_commit_sha"])


@dataclass(frozen=True, slots=True)
class _VerificationWriter:
    """Not exported from the package -- additive evidence/manifest bookkeeping only, never the
    orchestrator's authoritative task-state writer (R1 stays confined elsewhere)."""

    database_path: Path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.database_path))
        connection.execute("PRAGMA foreign_keys = ON")
        connection.row_factory = sqlite3.Row
        return connection

    def record_evidence(self, package: EvidencePackage, *, outcome: str) -> None:
        payload = evidence_package_json(package)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(_SELECT_EVIDENCE_BY_RUN_SQL, (package.run_id,)).fetchone()
            if existing is not None:
                if (
                    existing["package_digest"] == package.digest()
                    and existing["outcome"] == outcome
                    and existing["task_id"] == package.task_id
                ):
                    connection.rollback()
                    return
                raise VerificationStoreError(
                    "EVIDENCE_DUPLICATE_CONFLICT", f"run {package.run_id} already has evidence"
                )
            connection.execute(
                _INSERT_EVIDENCE_SQL,
                (
                    package.task_id,
                    package.run_id,
                    payload,
                    package.digest(),
                    outcome,
                    package.created_at,
                ),
            )
            connection.commit()
        except VerificationStoreError:
            connection.rollback()
            raise
        except sqlite3.Error as exc:
            connection.rollback()
            raise VerificationStoreError(
                "EVIDENCE_RECORD_FAILED", f"record_evidence failed: {exc}"
            ) from exc
        finally:
            connection.close()

    def record_manifest(self, manifest: PromotionManifest, *, checkpoint_commit_sha: str) -> None:
        payload = promotion_manifest_json(manifest)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            evidence = connection.execute(
                _SELECT_EVIDENCE_BY_RUN_SQL, (manifest.run_id,)
            ).fetchone()
            if (
                evidence is None
                or evidence["task_id"] != manifest.task_id
                or evidence["outcome"] != "PASSED"
            ):
                raise VerificationStoreError(
                    "MANIFEST_EVIDENCE_REQUIRED", "matching passed evidence must exist first"
                )
            existing = connection.execute(
                _SELECT_MANIFEST_BY_RUN_SQL, (manifest.run_id,)
            ).fetchone()
            if existing is not None:
                if (
                    existing["manifest_digest"] == manifest.digest()
                    and existing["checkpoint_commit_sha"] == checkpoint_commit_sha
                    and existing["task_id"] == manifest.task_id
                ):
                    connection.rollback()
                    return
                raise VerificationStoreError(
                    "MANIFEST_DUPLICATE_CONFLICT", f"run {manifest.run_id} already has a manifest"
                )
            connection.execute(
                _INSERT_MANIFEST_SQL,
                (
                    manifest.task_id,
                    manifest.run_id,
                    payload,
                    manifest.digest(),
                    manifest.base_sha,
                    manifest.branch_ref,
                    checkpoint_commit_sha,
                    manifest.created_at,
                ),
            )
            connection.commit()
        except VerificationStoreError:
            connection.rollback()
            raise
        except sqlite3.Error as exc:
            connection.rollback()
            raise VerificationStoreError(
                "MANIFEST_RECORD_FAILED", f"record_manifest failed: {exc}"
            ) from exc
        finally:
            connection.close()


__all__ = ["SQLiteVerificationReader", "VerificationReader"]
