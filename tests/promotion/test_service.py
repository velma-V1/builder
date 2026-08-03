from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from factory.approval.models import ApprovalRecord, ApprovalState, CommitState, action_fingerprint
from factory.git.errors import GitError
from factory.orchestrator.models import TaskState
from factory.orchestrator.store.runtime_state import (
    SQLiteOrchestratorStateReader,
    _OrchestratorStateWriter,
)
from factory.promotion import SQLitePromotionReader
from factory.promotion.errors import PromotionError
from factory.promotion.models import PromotionBinding, PromotionOutcome
from factory.promotion.service import PromotionService
from factory.verification.models import (
    EvidenceItem,
    EvidencePackage,
    ManifestFile,
    PromotionManifest,
)
from factory.verification.store import SQLiteVerificationReader, _VerificationWriter


@dataclass
class FakeGit:
    target: str = "base"
    digest: str = "blob"
    fail_advance: bool = False
    restored: bool = False
    crash_after_advance: bool = False
    fail_restore: bool = False

    def guard_protected_ref(self, ref: str) -> None:
        if ref == "main":
            raise GitError("PROTECTED_REF_WRITE", "protected", security=True)

    def resolve_ref(self, repo: Path, ref: str) -> str:
        return self.target

    def file_digest_at(self, repo: Path, commit: str, path: str) -> str:
        return self.digest

    def fast_forward_ref(self, repo: Path, ref: str, commit: str, expected_old: str) -> None:
        if self.fail_advance:
            raise GitError("GIT_COMMAND_FAILED", "injected")
        self.target = commit
        if self.crash_after_advance:
            raise SimulatedProcessCrash

    def restore_ref(self, repo: Path, ref: str, commit: str, expected_current: str) -> None:
        if self.fail_restore:
            raise GitError("GIT_COMMAND_FAILED", "restore injected")
        self.target = commit
        self.restored = True


class SimulatedProcessCrash(BaseException):
    pass


@dataclass
class FakeApprovalConsumer:
    expected: str

    def consume(self, record: ApprovalRecord, fingerprint: str) -> bool:
        return fingerprint == self.expected


def _setup(
    database: Path, task_id: str, target: str = "integration"
) -> tuple[PromotionBinding, ApprovalRecord]:
    writer = _OrchestratorStateWriter(database)
    for current, new in (
        (TaskState.QUEUED, TaskState.PLANNING),
        (TaskState.PLANNING, TaskState.RUNNING),
        (TaskState.RUNNING, TaskState.VERIFYING),
        (TaskState.VERIFYING, TaskState.AWAITING_APPROVAL),
    ):
        writer.apply_transition(
            task_id=task_id,
            expected_current_state=current,
            new_state=new,
            cause="test",
            actor="test",
        )
    evidence = EvidencePackage(
        task_id, "run-1", (EvidenceItem("scope", "clean", True),), "2026-08-02T00:00:00Z"
    )
    manifest = PromotionManifest(
        task_id,
        "run-1",
        "worker",
        "base",
        (ManifestFile("a.txt", "blob"),),
        "2026-08-02T00:00:01Z",
    )
    verification = _VerificationWriter(database)
    verification.record_evidence(evidence, outcome="PASSED")
    verification.record_manifest(manifest, checkpoint_commit_sha="checkpoint")
    binding = PromotionBinding(
        task_id, "run-1", evidence.digest(), manifest.digest(), target, "base"
    )
    fingerprint = action_fingerprint(
        task_id=task_id,
        tool="promotion",
        action="promote",
        resource=target,
        scope=binding.scope(),
    )
    approval = ApprovalRecord(
        "approval-1",
        task_id,
        "promotion",
        "promote",
        target,
        binding.scope(),
        "promote verified output",
        "target advances",
        "operator",
        1,
        0,
        False,
        9999999999,
        fingerprint,
        ApprovalState.GRANTED,
        CommitState.COMMITTED,
        1,
        1,
    )
    return binding, approval


def _service(database: Path, git: FakeGit, approval: ApprovalRecord) -> PromotionService:
    return PromotionService(
        database,
        Path("."),
        _OrchestratorStateWriter(database),
        SQLiteOrchestratorStateReader(database),
        SQLiteVerificationReader(database),
        FakeApprovalConsumer(approval.action_fingerprint or ""),
        git,
    )


def test_success_is_only_path_to_complete(verification_db: tuple[Path, str]) -> None:
    database, task_id = verification_db
    binding, approval = _setup(database, task_id)
    result = _service(database, FakeGit(), approval).promote(binding, approval, "operator")
    assert result.outcome is PromotionOutcome.PROMOTED
    assert (
        SQLiteOrchestratorStateReader(database).get_task(task_id).current_state
        is TaskState.COMPLETE
    )


def test_manifest_tamper_is_rejected_before_state_change(verification_db: tuple[Path, str]) -> None:
    database, task_id = verification_db
    binding, approval = _setup(database, task_id)
    with pytest.raises(PromotionError, match="PROMOTION_MANIFEST_TAMPERED"):
        _service(database, FakeGit(digest="tampered"), approval).promote(
            binding, approval, "operator"
        )
    assert (
        SQLiteOrchestratorStateReader(database).get_task(task_id).current_state
        is TaskState.AWAITING_APPROVAL
    )


def test_failed_advance_rolls_back_and_fails_task(verification_db: tuple[Path, str]) -> None:
    database, task_id = verification_db
    binding, approval = _setup(database, task_id)
    git = FakeGit(fail_advance=True)
    with pytest.raises(PromotionError, match="PROMOTION_FAILED"):
        _service(database, git, approval).promote(binding, approval, "operator")
    assert git.restored
    assert (
        SQLiteOrchestratorStateReader(database).get_task(task_id).current_state is TaskState.FAILED
    )


def test_protected_target_is_rejected(verification_db: tuple[Path, str]) -> None:
    database, task_id = verification_db
    binding, approval = _setup(database, task_id, target="main")
    with pytest.raises(GitError, match="PROTECTED_REF_WRITE"):
        _service(database, FakeGit(), approval).promote(binding, approval, "operator")


def test_interrupted_promotion_reconciles_to_failed_idempotently(
    verification_db: tuple[Path, str],
) -> None:
    database, task_id = verification_db
    _binding, approval = _setup(database, task_id)
    _OrchestratorStateWriter(database).apply_transition(
        task_id=task_id,
        expected_current_state=TaskState.AWAITING_APPROVAL,
        new_state=TaskState.PROMOTING,
        cause="interrupted",
        actor="test",
    )
    service = _service(database, FakeGit(), approval)
    assert service.reconcile_startup() == (task_id,)
    assert service.reconcile_startup() == ()
    assert (
        SQLiteOrchestratorStateReader(database).get_task(task_id).current_state is TaskState.FAILED
    )


def test_restart_rolls_back_ref_advanced_before_process_crash(
    verification_db: tuple[Path, str],
) -> None:
    database, task_id = verification_db
    binding, approval = _setup(database, task_id)
    git = FakeGit(crash_after_advance=True)
    service = _service(database, git, approval)

    with pytest.raises(SimulatedProcessCrash):
        service.promote(binding, approval, "operator")

    assert git.target == "checkpoint"
    assert service.reconcile_startup() == (task_id,)
    assert git.target == "base"
    assert git.restored
    assert (
        SQLiteOrchestratorStateReader(database).get_task(task_id).current_state is TaskState.FAILED
    )


def test_restart_records_explicit_rollback_failure(
    verification_db: tuple[Path, str],
) -> None:
    database, task_id = verification_db
    binding, approval = _setup(database, task_id)
    git = FakeGit(crash_after_advance=True, fail_restore=True)
    service = _service(database, git, approval)
    with pytest.raises(SimulatedProcessCrash):
        service.promote(binding, approval, "operator")

    assert service.reconcile_startup() == (task_id,)
    record = SQLitePromotionReader(database).get_latest_for_task(task_id)
    assert record is not None
    assert record.outcome is PromotionOutcome.REJECTED
    assert "ROLLBACK_FAILED" in record.reason
