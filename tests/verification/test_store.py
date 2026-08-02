from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from factory.verification.errors import VerificationStoreError
from factory.verification.models import (
    EvidenceItem,
    EvidencePackage,
    ManifestFile,
    PromotionManifest,
)
from factory.verification.store import SQLiteVerificationReader, _VerificationWriter


def _evidence(task_id: str, detail: str = "clean") -> EvidencePackage:
    return EvidencePackage(
        task_id=task_id,
        run_id="run-1",
        items=(EvidenceItem("scope", detail, True),),
        created_at="2026-08-02T00:00:00Z",
    )


def _manifest(task_id: str, digest: str = "abc") -> PromotionManifest:
    return PromotionManifest(
        task_id=task_id,
        run_id="run-1",
        branch_ref="factory/task-1",
        base_sha="base",
        files=(ManifestFile("src/a.py", digest),),
        created_at="2026-08-02T00:00:01Z",
    )


def test_round_trip_and_idempotent_recovery(verification_db: tuple[Path, str]) -> None:
    verification_db, task_id = verification_db
    writer = _VerificationWriter(verification_db)
    reader = SQLiteVerificationReader(verification_db)
    writer.record_evidence(_evidence(task_id), outcome="PASSED")
    writer.record_evidence(_evidence(task_id), outcome="PASSED")
    writer.record_manifest(_manifest(task_id), checkpoint_commit_sha="checkpoint")
    writer.record_manifest(_manifest(task_id), checkpoint_commit_sha="checkpoint")

    assert reader.get_latest_evidence(task_id) == _evidence(task_id)
    assert reader.get_latest_manifest(task_id) == _manifest(task_id)
    assert reader.get_manifest_checkpoint_commit(task_id) == "checkpoint"
    with sqlite3.connect(verification_db) as connection:
        assert connection.execute("SELECT COUNT(*) FROM evidence_packages").fetchone() == (1,)
        assert connection.execute("SELECT COUNT(*) FROM promotion_manifests").fetchone() == (1,)


def test_conflicting_duplicate_run_is_rejected(verification_db: tuple[Path, str]) -> None:
    verification_db, task_id = verification_db
    writer = _VerificationWriter(verification_db)
    writer.record_evidence(_evidence(task_id), outcome="PASSED")
    with pytest.raises(VerificationStoreError, match="EVIDENCE_DUPLICATE_CONFLICT"):
        writer.record_evidence(_evidence(task_id, "changed"), outcome="PASSED")


def test_tampered_evidence_digest_is_rejected(verification_db: tuple[Path, str]) -> None:
    verification_db, task_id = verification_db
    writer = _VerificationWriter(verification_db)
    writer.record_evidence(_evidence(task_id), outcome="PASSED")
    with sqlite3.connect(verification_db) as connection:
        connection.execute("DROP TRIGGER evidence_packages_no_update")
        connection.execute("UPDATE evidence_packages SET package_digest = 'tampered'")
    with pytest.raises(VerificationStoreError, match="EVIDENCE_DIGEST_MISMATCH"):
        SQLiteVerificationReader(verification_db).get_latest_evidence(task_id)


def test_manifest_requires_matching_passed_evidence(verification_db: tuple[Path, str]) -> None:
    verification_db, task_id = verification_db
    with pytest.raises(VerificationStoreError, match="MANIFEST_EVIDENCE_REQUIRED"):
        _VerificationWriter(verification_db).record_manifest(
            _manifest(task_id), checkpoint_commit_sha="checkpoint"
        )


def test_append_only_triggers_reject_mutation(verification_db: tuple[Path, str]) -> None:
    verification_db, task_id = verification_db
    writer = _VerificationWriter(verification_db)
    writer.record_evidence(_evidence(task_id), outcome="PASSED")
    with (
        sqlite3.connect(verification_db) as connection,
        pytest.raises(sqlite3.IntegrityError, match="append-only"),
    ):
        connection.execute("DELETE FROM evidence_packages")
