from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from factory.approval import ApprovalEngine, SystemClock, apply_security_migrations
from factory.audit import apply_audit_migrations
from factory.orchestrator.models import TaskState
from factory.orchestrator.store.runtime_state import (
    SQLiteOrchestratorStateReader,
    _OrchestratorStateWriter,
    apply_migrations,
)
from factory.orchestrator_api.lifecycle import Phase3BLifecycleService
from factory.promotion import PromotionService, SQLitePromotionReader
from factory.verification.models import (
    EvidenceItem,
    EvidencePackage,
    ManifestFile,
    PromotionManifest,
)
from factory.verification.store import SQLiteVerificationReader, _VerificationWriter
from factory.worker_engine.execution_policy import ExecutionMode
from factory.worker_engine.store import SQLiteWorkerRunReader, _WorkerRunWriter

ROOT = Path(__file__).resolve().parents[2]


@dataclass
class FakeGit:
    target: str = "base"

    def guard_protected_ref(self, ref: str) -> None:
        if ref == "main":
            raise RuntimeError("protected")

    def resolve_ref(self, repo: Path, ref: str) -> str:
        return self.target

    def file_digest_at(self, repo: Path, commit: str, path: str) -> str:
        return "blob"

    def fast_forward_ref(self, repo: Path, ref: str, commit: str, expected_old: str) -> None:
        self.target = commit

    def restore_ref(self, repo: Path, ref: str, commit: str, expected_current: str) -> None:
        self.target = commit


def _service(tmp_path: Path) -> tuple[Phase3BLifecycleService, str]:
    runtime = tmp_path / "runtime.db"
    security = tmp_path / "security.db"
    audit = tmp_path / "audit.db"
    apply_migrations(runtime, ROOT / "migrations/runtime")
    apply_security_migrations(security, ROOT / "migrations/security")
    apply_audit_migrations(audit, ROOT / "migrations/audit")
    writer = _OrchestratorStateWriter(runtime)
    task_id = writer.submit_task_request(
        project_ref="builder",
        workstream_id="ws-1",
        description="promote",
        priority="normal",
        model_preference=None,
        expected_result=None,
        submitted_by="test",
        idempotency_key="phase3b-lifecycle",
    ).task_id
    _WorkerRunWriter(runtime).create_run(
        run_id="run-1",
        task_id=task_id,
        attempt=1,
        requested_mode=ExecutionMode.SANDBOXED_EXECUTION,
        selected_mode=ExecutionMode.SANDBOXED_EXECUTION,
        mode_reason="test",
        policy_rule="test",
        work_order_json="{}",
        model_route_token="route-token-placeholder",  # noqa: S106
    )
    for old, new in (
        (TaskState.QUEUED, TaskState.PLANNING),
        (TaskState.PLANNING, TaskState.RUNNING),
        (TaskState.RUNNING, TaskState.VERIFYING),
        (TaskState.VERIFYING, TaskState.AWAITING_APPROVAL),
    ):
        writer.apply_transition(
            task_id=task_id,
            expected_current_state=old,
            new_state=new,
            cause="test",
            actor="test",
        )
    evidence = EvidencePackage(
        task_id,
        "run-1",
        (EvidenceItem("tests", "passed", True),),
        "2026-08-02T00:00:00Z",
    )
    manifest = PromotionManifest(
        task_id,
        "run-1",
        "worker",
        "base",
        (ManifestFile("a.txt", "blob"),),
        "2026-08-02T00:00:01Z",
    )
    verification_writer = _VerificationWriter(runtime)
    verification_writer.record_evidence(evidence, outcome="PASSED")
    verification_writer.record_manifest(manifest, checkpoint_commit_sha="checkpoint")
    reader = SQLiteOrchestratorStateReader(runtime)
    verification_reader = SQLiteVerificationReader(runtime)
    approvals = ApprovalEngine(security, audit, SystemClock())
    git = FakeGit()
    promotion = PromotionService(
        runtime,
        tmp_path,
        writer,
        reader,
        verification_reader,
        approvals,
        git,  # type: ignore[arg-type]
    )
    return (
        Phase3BLifecycleService(
            reader,
            verification_reader,
            SQLiteWorkerRunReader(runtime),
            approvals,
            promotion,
            SQLitePromotionReader(runtime),
            git,  # type: ignore[arg-type]
            tmp_path,
        ),
        task_id,
    )


def test_explicit_bound_approval_promotes_and_detail_reflects_durable_state(
    tmp_path: Path,
) -> None:
    service, task_id = _service(tmp_path)
    card = service.request_approval(task_id, target_ref="integration", actor="operator")

    result = service.approve(card.approval_id, operator="operator", confirmed_destructive=True)

    assert result.promoted_commit_sha == "checkpoint"
    assert service.orchestrator_reader.get_task(task_id).current_state is TaskState.COMPLETE
    assert service.detail(task_id).promotion == result


def test_operator_rejection_uses_real_approval_boundary_and_is_durable(tmp_path: Path) -> None:
    service, task_id = _service(tmp_path)
    card = service.request_approval(task_id, target_ref="integration", actor="operator")

    result = service.reject(card.approval_id, operator="operator", reason="not acceptable")

    assert result.reason == "not acceptable"
    assert service.orchestrator_reader.get_task(task_id).current_state is TaskState.REJECTED


def test_approval_requires_separate_explicit_confirmation(tmp_path: Path) -> None:
    service, task_id = _service(tmp_path)
    card = service.request_approval(task_id, target_ref="integration", actor="operator")

    try:
        service.approve(card.approval_id, operator="operator", confirmed_destructive=False)
    except Exception as exc:
        assert "confirmation" in str(exc).lower()
    else:
        raise AssertionError("promotion succeeded without explicit confirmation")
    assert (
        service.orchestrator_reader.get_task(task_id).current_state is TaskState.AWAITING_APPROVAL
    )
