from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from factory.approval.models import ApprovalRecord, ApprovalState, CommitState, action_fingerprint
from factory.git.manager import GitManager
from factory.orchestrator.models import TaskState
from factory.orchestrator.store.runtime_state import (
    OrchestratorStateReader,
    _OrchestratorStateWriter,
)
from factory.promotion.errors import PromotionError
from factory.promotion.models import PromotionBinding, PromotionOutcome, PromotionRecord
from factory.promotion.store import _PromotionWriter
from factory.verification.store import VerificationReader


class ApprovalConsumer(Protocol):
    def consume(self, record: ApprovalRecord, action_fingerprint_value: str) -> bool: ...


_LOCKS: dict[str, threading.Lock] = {}
_LOCKS_GUARD = threading.Lock()


def _utcnow() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _target_lock(target: str) -> threading.Lock:
    with _LOCKS_GUARD:
        return _LOCKS.setdefault(target, threading.Lock())


@dataclass(slots=True)
class PromotionService:
    database_path: Path
    repo_root: Path
    orchestrator_writer: _OrchestratorStateWriter
    orchestrator_reader: OrchestratorStateReader
    verification_reader: VerificationReader
    approval_consumer: ApprovalConsumer
    git: GitManager
    actor: str = "promotion_service"
    _writer: _PromotionWriter = field(init=False)

    def __post_init__(self) -> None:
        self._writer = _PromotionWriter(self.database_path)

    def reject(
        self, binding: PromotionBinding, approval_id: str, operator: str, reason: str
    ) -> PromotionRecord:
        record = self.orchestrator_reader.get_task(binding.task_id)
        if record is None or record.current_state is not TaskState.AWAITING_APPROVAL:
            raise PromotionError("PROMOTION_STATE_INVALID", "task is not awaiting approval")
        self.orchestrator_writer.apply_transition(
            task_id=binding.task_id,
            expected_current_state=TaskState.AWAITING_APPROVAL,
            new_state=TaskState.REJECTED,
            cause="operator_rejected_promotion",
            actor=operator,
        )
        result = self._record(binding, approval_id, operator, PromotionOutcome.REJECTED, reason)
        return result

    def reconcile_startup(self) -> tuple[str, ...]:
        """Fail closed for interrupted promotions; never infer completion after restart."""
        reconciled: list[str] = []
        tasks = self.orchestrator_reader.list_tasks_by_states(frozenset({TaskState.PROMOTING}))
        for task in tasks:
            manifest = self.verification_reader.get_latest_manifest(task.task_id)
            run_id = manifest.run_id if manifest is not None else "unknown-run"
            self.orchestrator_writer.apply_transition(
                task_id=task.task_id,
                expected_current_state=TaskState.PROMOTING,
                new_state=TaskState.FAILED,
                cause="promotion_interrupted_reconcile",
                actor=self.actor,
            )
            self._writer.record(
                PromotionRecord(
                    promotion_id=f"reconcile-{task.task_id}-{task.sequence}",
                    task_id=task.task_id,
                    run_id=run_id,
                    approval_card_id="unavailable-after-interruption",
                    decided_by=self.actor,
                    promoted_branch=None,
                    promoted_commit_sha=None,
                    outcome=PromotionOutcome.REJECTED,
                    reason=(
                        "INTERRUPTED_PROMOTION: completion and rollback not provable; "
                        "manual recovery required"
                    ),
                    created_at=_utcnow(),
                )
            )
            reconciled.append(task.task_id)
        return tuple(reconciled)

    def promote(
        self, binding: PromotionBinding, approval: ApprovalRecord, operator: str
    ) -> PromotionRecord:
        with _target_lock(binding.target_ref):
            return self._promote_locked(binding, approval, operator)

    def _promote_locked(
        self, binding: PromotionBinding, approval: ApprovalRecord, operator: str
    ) -> PromotionRecord:
        task = self.orchestrator_reader.get_task(binding.task_id)
        if task is None or task.current_state is not TaskState.AWAITING_APPROVAL:
            raise PromotionError("PROMOTION_STATE_INVALID", "task is not awaiting approval")
        evidence = self.verification_reader.get_latest_evidence(binding.task_id)
        manifest = self.verification_reader.get_latest_manifest(binding.task_id)
        checkpoint = self.verification_reader.get_manifest_checkpoint_commit(binding.task_id)
        if evidence is None or manifest is None or checkpoint is None or not evidence.passed:
            raise PromotionError(
                "PROMOTION_EVIDENCE_INVALID", "passed evidence and manifest required"
            )
        if (
            evidence.run_id != binding.run_id
            or evidence.digest() != binding.evidence_digest
            or manifest.run_id != binding.run_id
            or manifest.digest() != binding.manifest_digest
        ):
            raise PromotionError(
                "PROMOTION_BINDING_MISMATCH", "approval binding does not match evidence"
            )
        if (
            approval.state is not ApprovalState.GRANTED
            or approval.commit_state is not CommitState.COMMITTED
        ):
            raise PromotionError("PROMOTION_APPROVAL_INVALID", "explicit committed grant required")
        self.git.guard_protected_ref(binding.target_ref)
        if self.git.resolve_ref(self.repo_root, binding.target_ref) != binding.target_revision:
            raise PromotionError("PROMOTION_TARGET_DRIFT", "target revision changed after approval")
        mismatches = [
            item.path
            for item in manifest.files
            if self.git.file_digest_at(self.repo_root, checkpoint, item.path) != item.content_digest
        ]
        if mismatches:
            raise PromotionError(
                "PROMOTION_MANIFEST_TAMPERED", f"checkpoint differs for {sorted(mismatches)}"
            )
        fingerprint = action_fingerprint(
            task_id=binding.task_id,
            tool="promotion",
            action="promote",
            resource=binding.target_ref,
            scope=binding.scope(),
        )
        if not self.approval_consumer.consume(approval, fingerprint):
            raise PromotionError(
                "PROMOTION_APPROVAL_INVALID", "bound approval could not be consumed"
            )
        self.orchestrator_writer.apply_transition(
            task_id=binding.task_id,
            expected_current_state=TaskState.AWAITING_APPROVAL,
            new_state=TaskState.PROMOTING,
            cause="promotion_approved",
            actor=self.actor,
        )
        try:
            self.git.fast_forward_ref(
                self.repo_root, binding.target_ref, checkpoint, binding.target_revision
            )
            result = self._record(
                binding,
                approval.approval_id,
                operator,
                PromotionOutcome.PROMOTED,
                "manifest revalidated and target advanced",
                checkpoint,
            )
            self.orchestrator_writer.apply_transition(
                task_id=binding.task_id,
                expected_current_state=TaskState.PROMOTING,
                new_state=TaskState.COMPLETE,
                cause="promotion_complete",
                actor=self.actor,
            )
        except Exception as exc:
            try:
                self.git.restore_ref(
                    self.repo_root, binding.target_ref, binding.target_revision, checkpoint
                )
                outcome, reason = (
                    PromotionOutcome.ROLLED_BACK,
                    f"promotion failed; rolled back: {exc}",
                )
            except Exception as rollback_exc:
                outcome = PromotionOutcome.REJECTED
                reason = f"ROLLBACK_FAILED: promotion={exc}; rollback={rollback_exc}"
            current = self.orchestrator_reader.get_task(binding.task_id)
            if current is not None and current.current_state is TaskState.PROMOTING:
                self.orchestrator_writer.apply_transition(
                    task_id=binding.task_id,
                    expected_current_state=TaskState.PROMOTING,
                    new_state=TaskState.FAILED,
                    cause="promotion_failed",
                    actor=self.actor,
                )
            result = self._record(binding, approval.approval_id, operator, outcome, reason)
            raise PromotionError("PROMOTION_FAILED", result.reason) from exc
        return result

    def _record(
        self,
        binding: PromotionBinding,
        approval_id: str,
        operator: str,
        outcome: PromotionOutcome,
        reason: str,
        commit: str | None = None,
    ) -> PromotionRecord:
        record = PromotionRecord(
            promotion_id=f"promotion-{uuid.uuid4().hex}",
            task_id=binding.task_id,
            run_id=binding.run_id,
            approval_card_id=approval_id,
            decided_by=operator,
            promoted_branch=binding.target_ref,
            promoted_commit_sha=commit,
            outcome=outcome,
            reason=reason,
            created_at=_utcnow(),
        )
        self._writer.record(record)
        return record
