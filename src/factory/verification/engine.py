"""``VerificationEngine`` -- Phase 3B's independent, deterministic verifier.

Never calls the worker model or any ``ModelRouterPort``: every check here is a plain, repeatable,
deterministic function of the frozen output on disk, run by Builder itself, never the worker that
produced the output. This is the structural meaning of "independent" -- the same code path runs
identically whether the run came from the real Agent Zero deployment or the Builder-native
fallback, and neither can influence its own verdict.

Verifies, per the required scope: changed paths against the work order's approved scope; a
second, independent staging/inspection pass (secrets, unexpected executables, archive bombs,
scope) even though the Worker Engine already ran one; Python syntax validity and (best-effort,
bounded) lint for every changed ``.py`` file; a bounded test run if the output looks like it
contains tests; and a minimal, explicit acceptance-criteria check against the task's own
``expected_result``, when the operator supplied one.

On success: builds an immutable :class:`EvidencePackage` and (for STAGED_WRITE/SANDBOXED_EXECUTION
runs) a :class:`PromotionManifest` pinning the *exact* files/content that may later be promoted,
persists both, and moves the task VERIFYING -> AWAITING_APPROVAL. On any failure: persists the
evidence explaining why, and moves the task VERIFYING -> FAILED. Never transitions to COMPLETE --
that is promotion's job, gated by a separate, explicit approval.
"""

from __future__ import annotations

import ast
import hashlib
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from factory.contracts.validation.paths import PathAuthority
from factory.git.manager import GitManager
from factory.git.models import CommitTrailers, VerificationStatus
from factory.git.trailers import render_message
from factory.orchestrator.models import TaskState
from factory.orchestrator.store.runtime_state import (
    OrchestratorStateReader,
    _OrchestratorStateWriter,
)
from factory.staging.manager import QuarantinedStaging
from factory.staging.models import StagedFile
from factory.verification.models import (
    EvidenceItem,
    EvidencePackage,
    ManifestFile,
    PromotionManifest,
)
from factory.verification.store import _VerificationWriter
from factory.worker_engine.models import WorkerRunRecord

_VERIFICATION_ACTOR = "verification_engine"
_TIMEOUT_S = 60


def _utcnow() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _all_files(root: Path) -> tuple[str, ...]:
    return tuple(
        sorted(
            str(p.relative_to(root))
            for p in root.rglob("*")
            if p.is_file() and ".git" not in p.parts
        )
    )


@dataclass(frozen=True, slots=True)
class VerificationOutcome:
    passed: bool
    evidence: EvidencePackage
    manifest: PromotionManifest | None


@dataclass(slots=True)
class VerificationEngine:
    orchestrator_writer: _OrchestratorStateWriter
    orchestrator_reader: OrchestratorStateReader
    verification_writer: _VerificationWriter
    git: GitManager
    repo_root: Path
    actor: str = _VERIFICATION_ACTOR

    def verify(self, task_id: str, run: WorkerRunRecord) -> VerificationOutcome:
        items: list[EvidenceItem] = []
        manifest: PromotionManifest | None = None
        allowed_path_globs = self._allowed_path_globs(run)

        if run.selected_mode.name == "DIRECT_READ_ONLY" or run.sandbox_path is None:
            items.append(
                EvidenceItem(
                    kind="scope",
                    detail="DIRECT_READ_ONLY: no files changed, nothing to verify "
                    "beyond the recorded analysis",
                    passed=True,
                )
            )
            return self._conclude(task_id, run, items, manifest=None)

        output_root = Path(run.sandbox_path)
        checkpoint_commit_sha = ""

        if run.branch_ref is not None and run.base_sha is not None:
            # SANDBOXED_EXECUTION: freeze by checkpoint-committing the worktree's changes before
            # inspecting anything further -- nothing can mutate it again after this point.
            checkpoint_ok, checkpoint_detail, checkpoint_commit_sha = self._freeze_worktree(
                task_id, run, output_root
            )
            items.append(
                EvidenceItem(kind="freeze", detail=checkpoint_detail, passed=checkpoint_ok)
            )
            if not checkpoint_ok:
                return self._conclude(task_id, run, items, manifest=None)
            changed_paths = self.git.changed_files(output_root, run.base_sha, "HEAD").all_paths()
        else:
            # STAGED_WRITE: the temp directory itself, in its entirety, is the frozen output --
            # nothing further ever writes to it after the run completed.
            changed_paths = _all_files(output_root)

        if not changed_paths:
            items.append(EvidenceItem(kind="scope", detail="no changed files found", passed=False))
            return self._conclude(task_id, run, items, manifest=None)

        scope_ok, scope_detail = self._check_scope(output_root, changed_paths, allowed_path_globs)
        items.append(EvidenceItem(kind="scope", detail=scope_detail, passed=scope_ok))

        staging_ok, staging_detail = self._independent_staging_pass(
            output_root, changed_paths, allowed_path_globs
        )
        items.append(EvidenceItem(kind="security", detail=staging_detail, passed=staging_ok))

        syntax_ok, syntax_detail = self._check_python_syntax(output_root, changed_paths)
        items.append(EvidenceItem(kind="types", detail=syntax_detail, passed=syntax_ok))

        lint_ok, lint_detail = self._check_lint(output_root, changed_paths)
        items.append(EvidenceItem(kind="lint", detail=lint_detail, passed=lint_ok))

        tests_ok, tests_detail = self._check_tests(output_root)
        items.append(EvidenceItem(kind="tests", detail=tests_detail, passed=tests_ok))

        acceptance_ok, acceptance_detail = self._check_acceptance(
            task_id, output_root, changed_paths
        )
        items.append(
            EvidenceItem(kind="acceptance", detail=acceptance_detail, passed=acceptance_ok)
        )

        all_passed = all(item.passed for item in items)
        if all_passed:
            manifest = PromotionManifest(
                task_id=task_id,
                run_id=run.run_id,
                branch_ref=run.branch_ref or "",
                base_sha=run.base_sha or "",
                files=tuple(
                    ManifestFile(path=p, content_digest=_sha256_file(output_root / p))
                    for p in changed_paths
                ),
                created_at=_utcnow(),
            )
            self.verification_writer.record_manifest(
                manifest, checkpoint_commit_sha=checkpoint_commit_sha
            )

        return self._conclude(task_id, run, items, manifest=manifest)

    # ---- individual checks -----------------------------------------------------------------

    def _allowed_path_globs(self, run: WorkerRunRecord) -> tuple[str, ...]:
        import json

        payload = json.loads(run.work_order_json)
        return tuple(payload.get("allowed_path_globs", ()))

    def _freeze_worktree(
        self, task_id: str, run: WorkerRunRecord, output_root: Path
    ) -> tuple[bool, str, str]:
        if not self.git.has_unexplained_changes(output_root):
            return False, "no changes to freeze (empty worktree)", ""
        record = self.orchestrator_reader.get_task(task_id)
        workstream_id = record.workstream_id if record is not None else "unassigned"
        trailers = CommitTrailers(
            task_id=task_id,
            stage_id="worker-verify",
            workstream_id=workstream_id or "unassigned",
            checkpoint_id=f"chk-{run.run_id}",
            verification_status=VerificationStatus.CHECKPOINT,
        )
        try:
            checkpoint = self.git.checkpoint(
                output_root,
                task_id=task_id,
                owned_paths=self._allowed_path_globs(run),
                subject=render_message(f"Phase 3B verification checkpoint for {task_id}", trailers)[
                    :72
                ].splitlines()[0],
                trailers=trailers,
            )
        except Exception as exc:
            return False, f"checkpoint failed: {exc}", ""
        return True, f"frozen at checkpoint commit {checkpoint.commit_sha}", checkpoint.commit_sha

    def _check_scope(
        self, output_root: Path, changed_paths: tuple[str, ...], allowed_path_globs: tuple[str, ...]
    ) -> tuple[bool, str]:
        authority = PathAuthority(output_root)
        out_of_scope = [
            path
            for path in changed_paths
            if not authority.evaluate(
                path,
                operation="write",
                allowed=list(allowed_path_globs),
                forbidden=(),
                read_only=(),
                active_exclusive_paths=(),
            ).allowed
        ]
        if out_of_scope:
            return False, f"out-of-scope changes: {sorted(out_of_scope)}"
        return True, f"all {len(changed_paths)} changed path(s) within approved scope"

    def _independent_staging_pass(
        self, output_root: Path, changed_paths: tuple[str, ...], allowed_path_globs: tuple[str, ...]
    ) -> tuple[bool, str]:
        staging = QuarantinedStaging(
            staging_id=f"verify-{hashlib.sha256(str(output_root).encode()).hexdigest()[:12]}",
            project_root=output_root,
            approved_scope=allowed_path_globs,
        )
        for path in changed_paths:
            absolute = output_root / path
            if absolute.is_file():
                staging.stage(
                    StagedFile(path=path, content=absolute.read_bytes(), provenance="verification")
                )
        inspection = staging.inspect()
        if not inspection.clean:
            findings = sorted({f.kind.value for f in inspection.findings})
            return False, f"independent inspection findings: {findings}"
        return True, "independent staging inspection clean"

    def _check_python_syntax(
        self, output_root: Path, changed_paths: tuple[str, ...]
    ) -> tuple[bool, str]:
        python_files = [p for p in changed_paths if p.endswith(".py")]
        if not python_files:
            return True, "no Python files changed"
        errors: list[str] = []
        for path in python_files:
            try:
                ast.parse((output_root / path).read_text(encoding="utf-8"), filename=path)
            except SyntaxError as exc:
                errors.append(f"{path}: {exc}")
        if errors:
            return False, f"syntax errors: {errors}"
        return True, f"{len(python_files)} Python file(s) parse cleanly"

    def _check_lint(self, output_root: Path, changed_paths: tuple[str, ...]) -> tuple[bool, str]:
        python_files = [p for p in changed_paths if p.endswith(".py")]
        if not python_files:
            return True, "no Python files to lint"
        ruff = shutil.which("ruff")
        if ruff is None:
            return True, "ruff not available in this environment -- lint skipped, not failed"
        try:
            result = subprocess.run(  # noqa: S603 - fixed executable path, literal argv
                [ruff, "check", *python_files],
                cwd=output_root,
                capture_output=True,
                text=True,
                timeout=_TIMEOUT_S,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return False, f"ruff check exceeded {_TIMEOUT_S}s"
        if result.returncode != 0:
            return False, f"ruff check failed: {result.stdout.strip()[:500]}"
        return True, "ruff check clean"

    def _check_tests(self, output_root: Path) -> tuple[bool, str]:
        has_tests = any(output_root.rglob("test_*.py")) or (output_root / "tests").is_dir()
        if not has_tests:
            return True, "no tests present -- skipped, not failed"
        try:
            result = subprocess.run(  # noqa: S603 - fixed argv, no shell
                [sys.executable, "-m", "pytest", "-q", str(output_root)],
                capture_output=True,
                text=True,
                timeout=_TIMEOUT_S,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return False, f"test run exceeded {_TIMEOUT_S}s"
        if result.returncode != 0:
            return False, f"tests failed: {result.stdout.strip()[:500]}"
        return True, "tests passed"

    def _check_acceptance(
        self, task_id: str, output_root: Path, changed_paths: tuple[str, ...]
    ) -> tuple[bool, str]:
        request = self.orchestrator_reader.get_task_request(task_id)
        expected = (request.expected_result if request is not None else None) or ""
        if not expected.strip():
            return True, "no explicit acceptance criteria supplied -- trivially satisfied"
        haystack = "\n".join(
            (output_root / p).read_text(encoding="utf-8", errors="replace")
            for p in changed_paths
            if (output_root / p).is_file()
        )
        if expected.strip().lower() in haystack.lower():
            return True, "expected_result text found in changed output"
        return False, f"expected_result {expected!r} not found in changed output"

    def _conclude(
        self,
        task_id: str,
        run: WorkerRunRecord,
        items: list[EvidenceItem],
        *,
        manifest: PromotionManifest | None,
    ) -> VerificationOutcome:
        evidence = EvidencePackage(
            task_id=task_id, run_id=run.run_id, items=tuple(items), created_at=_utcnow()
        )
        passed = evidence.passed
        self.verification_writer.record_evidence(evidence, outcome="PASSED" if passed else "FAILED")

        record = self.orchestrator_reader.get_task(task_id)
        current = record.current_state if record is not None else TaskState.VERIFYING
        if passed:
            self.orchestrator_writer.apply_transition(
                task_id=task_id,
                expected_current_state=current,
                new_state=TaskState.AWAITING_APPROVAL,
                cause="verification_passed",
                actor=self.actor,
            )
        else:
            self.orchestrator_writer.apply_transition(
                task_id=task_id,
                expected_current_state=current,
                new_state=TaskState.FAILED,
                cause="verification_failed",
                actor=self.actor,
            )
        return VerificationOutcome(passed=passed, evidence=evidence, manifest=manifest)
