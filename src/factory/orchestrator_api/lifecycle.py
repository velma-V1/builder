"""Phase 3B lifecycle composition across verification, approval, and promotion."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from factory.approval import ApprovalEngine
from factory.approval.models import (
    ApprovalCard,
    ApprovalRecord,
    ApprovalRequest,
    DecisionKind,
    Denial,
    OperatorDecision,
)
from factory.git.manager import GitManager
from factory.orchestrator.models import TaskState
from factory.orchestrator.store.runtime_state import OrchestratorStateReader
from factory.orchestrator_api.errors import OrchestratorApiError
from factory.promotion import (
    PromotionBinding,
    PromotionRecord,
    PromotionService,
    SQLitePromotionReader,
)
from factory.verification.models import EvidencePackage, PromotionManifest
from factory.verification.store import VerificationReader
from factory.worker_engine.models import WorkerRunOutcome, WorkerRunRecord
from factory.worker_engine.store import WorkerRunReader


@dataclass(frozen=True, slots=True)
class Phase3BDetail:
    evidence: EvidencePackage | None
    manifest: PromotionManifest | None
    promotion: PromotionRecord | None
    approval: ApprovalRecord | None


class Verifier(Protocol):
    def verify(self, task_id: str, run: WorkerRunRecord) -> object: ...


@dataclass(slots=True)
class Phase3BLifecycleService:
    orchestrator_reader: OrchestratorStateReader
    verification_reader: VerificationReader
    worker_run_reader: WorkerRunReader
    approval_engine: ApprovalEngine
    promotion_service: PromotionService
    promotion_reader: SQLitePromotionReader
    git: GitManager
    repo_root: Path
    verifier: Verifier | None = None

    def detail(self, task_id: str) -> Phase3BDetail:
        if self.orchestrator_reader.get_task(task_id) is None:
            raise OrchestratorApiError("TASK_NOT_FOUND", f"task {task_id} does not exist")
        return Phase3BDetail(
            evidence=self.verification_reader.get_latest_evidence(task_id),
            manifest=self.verification_reader.get_latest_manifest(task_id),
            promotion=self.promotion_reader.get_latest_for_task(task_id),
            approval=self.approval_engine.reader.get_latest_promotion_for_task(task_id),
        )

    def request_approval(
        self, task_id: str, *, target_ref: str, actor: str, ttl_seconds: int = 3600
    ) -> ApprovalCard:
        task = self.orchestrator_reader.get_task(task_id)
        evidence = self.verification_reader.get_latest_evidence(task_id)
        manifest = self.verification_reader.get_latest_manifest(task_id)
        if (
            task is None
            or task.current_state is not TaskState.AWAITING_APPROVAL
            or evidence is None
            or not evidence.passed
            or manifest is None
        ):
            raise OrchestratorApiError(
                "ACTION_REJECTED", "passed evidence and manifest are required for approval"
            )
        self.git.guard_protected_ref(target_ref)
        target_revision = self.git.resolve_ref(self.repo_root, target_ref)
        binding = PromotionBinding(
            task_id=task_id,
            run_id=manifest.run_id,
            evidence_digest=evidence.digest(),
            manifest_digest=manifest.digest(),
            target_ref=target_ref,
            target_revision=target_revision,
        )
        return self.approval_engine.enqueue(
            ApprovalRequest(
                task_id=task_id,
                tool="promotion",
                action="promote",
                resource=target_ref,
                scope=binding.scope(),
                purpose="Promote independently verified worker output",
                consequences=f"Advance {target_ref} to the verified checkpoint",
                autonomy_level="operator_only",
                ttl_seconds=ttl_seconds,
                actor=actor,
                destructive=True,
            )
        )

    def approve(
        self, approval_id: str, *, operator: str, confirmed_destructive: bool
    ) -> PromotionRecord:
        decided = self.approval_engine.decide(
            approval_id,
            OperatorDecision(
                decision=DecisionKind.GRANT,
                operator=operator,
                confirmed_destructive=confirmed_destructive,
            ),
        )
        if isinstance(decided, Denial):
            raise OrchestratorApiError("ACTION_REJECTED", decided.message)
        try:
            binding = PromotionBinding.from_scope(decided.scope)
        except (TypeError, ValueError) as exc:
            raise OrchestratorApiError("ACTION_REJECTED", "invalid promotion binding") from exc
        return self.promotion_service.promote(binding, decided, operator)

    def reject(self, approval_id: str, *, operator: str, reason: str) -> PromotionRecord:
        pending = self.approval_engine.reader.get_record(approval_id)
        if pending is None:
            raise OrchestratorApiError("ACTION_REJECTED", "approval does not exist")
        try:
            binding = PromotionBinding.from_scope(pending.scope)
        except (TypeError, ValueError) as exc:
            raise OrchestratorApiError("ACTION_REJECTED", "invalid promotion binding") from exc
        denial = self.approval_engine.decide(
            approval_id,
            OperatorDecision(decision=DecisionKind.DENY, operator=operator),
        )
        if not isinstance(denial, Denial):
            raise OrchestratorApiError("ACTION_REJECTED", "approval was not denied")
        return self.promotion_service.reject(binding, approval_id, operator, reason)

    def reconcile_startup(self) -> tuple[str, ...]:
        reconciled = list(self.promotion_service.reconcile_startup())
        if self.verifier is None:
            return tuple(reconciled)
        tasks = self.orchestrator_reader.list_tasks_by_states(frozenset({TaskState.VERIFYING}))
        for task in tasks:
            runs = self.worker_run_reader.list_runs_for_task(task.task_id)
            if not runs:
                continue
            run = runs[-1]
            if run.finished_at is None or run.outcome is not WorkerRunOutcome.SUCCESS:
                continue
            self.verifier.verify(task.task_id, run)
            reconciled.append(task.task_id)
        return tuple(reconciled)


__all__ = ["Phase3BDetail", "Phase3BLifecycleService"]
