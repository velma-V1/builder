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
    payload = json.loads(row["package_json"])
    items = tuple(EvidenceItem(**item) for item in payload["items"])
    return EvidencePackage(
        task_id=row["task_id"], run_id=row["run_id"], items=items, created_at=row["created_at"]
    )


def _row_to_manifest(row: sqlite3.Row) -> PromotionManifest:
    payload = json.loads(row["manifest_json"])
    files = tuple(ManifestFile(**item) for item in payload["files"])
    return PromotionManifest(
        task_id=row["task_id"],
        run_id=row["run_id"],
        branch_ref=row["branch_ref"],
        base_sha=row["base_sha"],
        files=files,
        created_at=row["created_at"],
    )


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
        except sqlite3.Error as exc:
            connection.rollback()
            raise VerificationStoreError(
                "MANIFEST_RECORD_FAILED", f"record_manifest failed: {exc}"
            ) from exc
        finally:
            connection.close()


__all__ = ["SQLiteVerificationReader", "VerificationReader"]
