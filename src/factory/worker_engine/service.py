"""``WorkerEngineService`` -- the Phase 3B orchestration core.

Ties together, without reimplementing any of them: atomic task claiming and crash reconciliation
(reusing ``factory.workers.state_integration.StateIntegration``/``recovery.StartupRecovery`` over
the single authoritative writer, R1), the execution-mode policy boundary
(``execution_policy.ExecutionPolicy``), optional workspace/staging creation, a real Agent Zero
client with an explicit, recorded fallback to Builder's own in-process transport, retry with
bounded backoff, and this package's own additive run/event/artifact persistence (``store.py``).

**Transport choice is explicit and recorded, never silent.** Every run's ``worker_runs`` row
records exactly which transport executed it (``transport_source`` folded into the run's JSON work
order metadata) -- a Builder-native fallback run is never described as "Agent Zero succeeded".

**Retry.** A failed/crashed run with attempts remaining (``RetryPolicy``) is parked at BLOCKED
(the same legal ``RUNNING -> BLOCKED`` edge crash-reconciliation already uses) with a recorded
``retry_pending`` cause, rather than going straight to the terminal-ish FAILED state.
``retry_blocked_tasks()`` finds exactly those tasks (never a task BLOCKED for an unrelated/unknown
reason -- no blind resume) and re-attempts them.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import time
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from factory.git.manager import GitManager
from factory.integrations.agent_zero.adapter import AgentZeroAdapter
from factory.integrations.agent_zero.errors import AgentZeroError
from factory.integrations.agent_zero.models import (
    AgentZeroResult,
    ResourceEnvelope,
    WorkerOutcome,
)
from factory.integrations.agent_zero.policy import ModelRouterPort
from factory.integrations.agent_zero.task_mapping import build_work_order
from factory.integrations.agent_zero.transport import AgentZeroTransport
from factory.orchestrator.models import TERMINAL_STATES, ReconciliationOutcome, TaskState
from factory.orchestrator.store.runtime_state import (
    OrchestratorStateReader,
    _OrchestratorStateWriter,
)
from factory.staging.manager import QuarantinedStaging
from factory.staging.models import StagedFile
from factory.worker_engine.agent_zero_process_client import (
    AgentZeroDeploymentUnavailable,
    AgentZeroProcessClient,
)
from factory.worker_engine.builder_worker_transport import BuilderWorkerTransport
from factory.worker_engine.execution_policy import ExecutionMode, ExecutionPolicy
from factory.worker_engine.models import WorkerRunOutcome
from factory.worker_engine.store import WorkerRunReader, _WorkerRunWriter
from factory.worker_engine.task_classifier import classify_task_description
from factory.worker_engine.workspace import Workspace, WorkspaceManager
from factory.workers.errors import WorkerEngineError
from factory.workers.models import ExecutionResult
from factory.workers.quarantine import QuarantineRegistry
from factory.workers.recovery import RetryPolicy, StartupRecovery
from factory.workers.state_integration import StateIntegration

_DEFAULT_RESOURCES = ResourceEnvelope(
    cpu_millis=2000, memory_mb=2048, disk_mb=4096, wall_clock_s=1800
)
_DEFAULT_TIMEOUT_S = 900
TRANSPORT_AGENT_ZERO_REAL = "agent_zero_real"
TRANSPORT_BUILDER_NATIVE = "builder_native"
_RETRY_PENDING_CAUSE = "retry_pending"
_WRITE_TOOLS = frozenset({"read_file", "edit_file", "search"})
_READ_ONLY_TOOLS = frozenset({"read_file", "search"})


@dataclass(frozen=True, slots=True)
class RunSummary:
    """What a single claim-and-run cycle produced, for callers/tests to assert on."""

    task_id: str
    run_id: str
    transport_source: str
    selected_mode: ExecutionMode
    outcome: WorkerRunOutcome
    reason: str
    retry_scheduled: bool = False


def _staged_files_from_workspace(
    workspace_path: Path, target_paths: tuple[str, ...], provenance: str
) -> list[StagedFile]:
    staged: list[StagedFile] = []
    for target in target_paths:
        absolute = workspace_path / target
        if absolute.is_file():
            staged.append(
                StagedFile(path=target, content=absolute.read_bytes(), provenance=provenance)
            )
    return staged


def _classify_worker_outcome(result: AgentZeroResult) -> tuple[WorkerRunOutcome, str]:
    outcome_map = {
        WorkerOutcome.SUCCESS: WorkerRunOutcome.SUCCESS,
        WorkerOutcome.CANCELLED: WorkerRunOutcome.CANCELLED,
        WorkerOutcome.CRASHED: WorkerRunOutcome.CRASHED,
        WorkerOutcome.FAILURE: WorkerRunOutcome.FAILED,
        WorkerOutcome.TIMED_OUT: WorkerRunOutcome.FAILED,
    }
    if result.malformed:
        return WorkerRunOutcome.FAILED, result.reason or "malformed worker output"
    if result.incomplete and result.worker_claimed_outcome is WorkerOutcome.SUCCESS:
        return WorkerRunOutcome.FAILED, result.reason or "incomplete worker output"
    return outcome_map[result.worker_claimed_outcome], result.reason


def _to_execution_result(task_id: str, outcome: WorkerRunOutcome, reason: str) -> ExecutionResult:
    if outcome is WorkerRunOutcome.SUCCESS:
        return ExecutionResult(
            task_id=task_id,
            exit_code=0,
            output_hash=reason,
            events_captured=0,
            truncated=False,
            failure_cause=None,
        )
    if outcome is WorkerRunOutcome.CANCELLED:
        return ExecutionResult(
            task_id=task_id,
            exit_code=None,
            output_hash="",
            events_captured=0,
            truncated=False,
            failure_cause="cancelled",
        )
    return ExecutionResult(
        task_id=task_id,
        exit_code=1,
        output_hash="",
        events_captured=0,
        truncated=False,
        failure_cause=outcome.value.lower(),
    )


@dataclass(slots=True)
class WorkerEngineService:
    orchestrator_writer: _OrchestratorStateWriter
    orchestrator_reader: OrchestratorStateReader
    run_writer: _WorkerRunWriter
    run_reader: WorkerRunReader
    git: GitManager
    workspace_manager: WorkspaceManager
    repo_root: Path
    model_router: ModelRouterPort
    #: ``None`` means no real Agent Zero deployment is configured at all -- every run uses the
    #: Builder-native fallback, explicitly and honestly (never silently).
    agent_zero_client: AgentZeroProcessClient | None = None
    policy: ExecutionPolicy = field(default_factory=ExecutionPolicy)
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    actor: str = "worker_engine"

    @property
    def _integration(self) -> StateIntegration:
        return StateIntegration(writer=self.orchestrator_writer, reader=self.orchestrator_reader)

    # ---- crash / restart reconciliation ----------------------------------------------------

    def recover_on_startup(self) -> Mapping[str, ReconciliationOutcome]:
        """Apply R3 "no blind resume" to every non-terminal task at Worker Engine startup.

        Reuses ``StartupRecovery`` unchanged -- this never resumes a RUNNING/VERIFYING/etc. task
        blindly; it reconciles each to BLOCKED (or QUARANTINED on a journal mismatch), so a
        subsequent claim pass never silently duplicates in-flight work from a prior process.
        """
        non_terminal = frozenset(TaskState) - TERMINAL_STATES
        in_flight = self.orchestrator_reader.list_tasks_by_states(non_terminal)
        task_ids = [record.task_id for record in in_flight]
        recovery = StartupRecovery(integration=self._integration, quarantine=QuarantineRegistry())
        return recovery.recover(task_ids, actor=self.actor)

    # ---- claim + run ------------------------------------------------------------------------

    def run_all_claimable(self) -> tuple[RunSummary, ...]:
        """Atomically claim and run every currently-QUEUED task once.

        Claiming is exactly ``StateIntegration.start_execution``'s existing QUEUED->PLANNING->
        RUNNING transition, whose optimistic-concurrency check inside ``apply_transition`` (a
        single ``BEGIN IMMEDIATE`` SQLite transaction) is what actually prevents two concurrent
        callers from both claiming the same task -- this service adds no separate lease of its
        own for that guarantee, it reuses the one the writer already provides.
        """
        queued = self.orchestrator_reader.list_tasks_by_states(frozenset({TaskState.QUEUED}))
        summaries: list[RunSummary] = []
        for record in queued:
            summary = self.claim_and_run(record.task_id)
            if summary is not None:
                summaries.append(summary)
        return tuple(summaries)

    def claim_and_run(self, task_id: str) -> RunSummary | None:
        """Claim one task and run it. Returns ``None`` if the claim was lost (someone else, or a
        prior call, already advanced this task past QUEUED) -- never raises for a lost race."""
        try:
            self._integration.start_execution(task_id, actor=self.actor)
        except WorkerEngineError:
            return None
        return self._run_claimed_task(task_id)

    def retry_blocked_tasks(self) -> tuple[RunSummary, ...]:
        """Re-attempt every task BLOCKED specifically for a pending retry (never a task blocked
        for any other/unknown reason -- that would be a blind resume, R3)."""
        blocked = self.orchestrator_reader.list_tasks_by_states(frozenset({TaskState.BLOCKED}))
        summaries: list[RunSummary] = []
        for record in blocked:
            if not self._is_retry_pending(record.task_id):
                continue
            self.orchestrator_writer.apply_transition(
                task_id=record.task_id,
                expected_current_state=TaskState.BLOCKED,
                new_state=TaskState.PLANNING,
                cause="retry_resume",
                actor=self.actor,
            )
            self._integration.start_execution(record.task_id, actor=self.actor)
            summaries.append(self._run_claimed_task(record.task_id))
        return tuple(summaries)

    def _is_retry_pending(self, task_id: str) -> bool:
        events = self.orchestrator_reader.get_events(task_id)
        accepted = [e for e in events if e.accepted]
        if not accepted:
            return False
        return accepted[-1].new_state is TaskState.BLOCKED and accepted[-1].cause == (
            _RETRY_PENDING_CAUSE
        )

    # ---- transport selection (explicit, recorded, never silent) ----------------------------

    def _choose_transport(
        self, *, workspace_path: Path | None, allowed_path_globs: tuple[str, ...]
    ) -> tuple[AgentZeroTransport, str]:
        if self.agent_zero_client is not None:
            try:
                self.agent_zero_client.probe()
            except AgentZeroDeploymentUnavailable:
                pass
            else:
                return self.agent_zero_client, TRANSPORT_AGENT_ZERO_REAL
        fallback = BuilderWorkerTransport(
            model_router=self.model_router,
            workspace_path=workspace_path,
            allowed_path_globs=allowed_path_globs,
        )
        return fallback, TRANSPORT_BUILDER_NATIVE

    # ---- the run itself ---------------------------------------------------------------------

    def _run_claimed_task(self, task_id: str) -> RunSummary:
        request = self.orchestrator_reader.get_task_request(task_id)
        instructions = request.description if request is not None else ""
        workstream_id = (request.workstream_id if request is not None else None) or "unassigned"

        policy_input = classify_task_description(instructions)
        decision = self.policy.decide(policy_input)

        attempt = self.run_writer.next_attempt(task_id)
        run_id = f"run-{uuid.uuid4().hex}"
        branch_ref = f"factory/worker/{task_id}"

        workspace: Workspace | None = None
        workspace_path: Path | None = None
        sandbox_path: str | None = None
        recorded_branch_ref: str | None = None
        base_sha: str | None = None
        staging_id: str | None = None
        staging_dir: Path | None = None

        if decision.selected_mode is ExecutionMode.SANDBOXED_EXECUTION:
            workspace = self.workspace_manager.provision(
                repo=self.repo_root, task_id=task_id, workstream_id=workstream_id
            )
            workspace_path = workspace.path
            sandbox_path = str(workspace.path)
            recorded_branch_ref = workspace.branch_ref
            base_sha = workspace.base_sha
            branch_ref = workspace.branch_ref
        elif decision.selected_mode is ExecutionMode.STAGED_WRITE:
            staging_id = f"staging-{uuid.uuid4().hex}"
            staging_dir = Path(tempfile.mkdtemp(prefix=f"{staging_id}-"))
            workspace_path = staging_dir
            # Reuses the same "output_path" column SANDBOXED_EXECUTION uses for its worktree --
            # exactly one of the two ever applies for a given run -- so the Verification Engine
            # always has a single field to look at for "where does this run's output live on
            # disk, if anywhere".
            sandbox_path = str(staging_dir)

        allowed_path_globs: tuple[str, ...] = (
            () if decision.selected_mode is ExecutionMode.DIRECT_READ_ONLY else ("**",)
        )
        granted_tools = _READ_ONLY_TOOLS if workspace_path is None else _WRITE_TOOLS

        work_order = build_work_order(
            work_order_id=f"wo-{run_id}",
            task_id=task_id,
            workstream_id=workstream_id,
            branch_ref=branch_ref,
            instructions=instructions,
            granted_tools=granted_tools,
            allowed_path_globs=allowed_path_globs,
            resources=_DEFAULT_RESOURCES,
            timeout_s=_DEFAULT_TIMEOUT_S,
            model_route_token=uuid.uuid4().hex,
        )

        transport, transport_source = self._choose_transport(
            workspace_path=workspace_path, allowed_path_globs=allowed_path_globs
        )

        self.run_writer.create_run(
            run_id=run_id,
            task_id=task_id,
            attempt=attempt,
            requested_mode=decision.requested_mode,
            selected_mode=decision.selected_mode,
            mode_reason=decision.reason,
            policy_rule=decision.policy_rule,
            sandbox_path=sandbox_path,
            branch_ref=recorded_branch_ref,
            base_sha=base_sha,
            staging_id=staging_id,
            work_order_json=json.dumps(
                {
                    "work_order_id": work_order.work_order_id,
                    "instructions": work_order.instructions,
                    "allowed_path_globs": list(work_order.allowed_path_globs),
                    "granted_tools": sorted(work_order.granted_tools),
                    "transport_source": transport_source,
                }
            ),
            model_route_token=work_order.model_route_token,
        )

        adapter = AgentZeroAdapter(
            transport=transport, model_router=self.model_router, clock=lambda: int(time.time())
        )

        try:
            run_ref = adapter.submit(work_order)
        except AgentZeroError as exc:
            return self._finalize_run(
                task_id=task_id,
                run_id=run_id,
                attempt=attempt,
                transport_source=transport_source,
                selected_mode=decision.selected_mode,
                workspace=workspace,
                staging_dir=staging_dir,
                outcome=WorkerRunOutcome.FAILED,
                reason=f"submit failed: {exc.detail}",
                exec_result=ExecutionResult(
                    task_id=task_id,
                    exit_code=1,
                    output_hash="",
                    events_captured=0,
                    truncated=False,
                    failure_cause=exc.code.value,
                ),
            )

        result = adapter.collect_result(run_ref, work_order)
        result = adapter.intake_result(result)

        for index, event in enumerate(transport.poll_events(run_ref, after_sequence=-1)):
            self.run_writer.append_event(
                run_id=run_id,
                sequence=index,
                event_type=event.event_type.value,
                payload_json=json.dumps(dict(event.payload)),
            )
        for artifact in result.artifacts:
            self.run_writer.add_artifact(
                run_id=run_id,
                artifact_path=artifact.artifact_path,
                content_digest=artifact.content_digest,
                media_type=artifact.media_type,
            )

        # First-pass sanity gate for any write-capable mode: stage the actually-written files and
        # inspect them immediately. This never *promotes* anything (promotion is a separate,
        # later, approval-gated stage) -- it only catches out-of-scope/secret/executable output
        # early, before spending a verification cycle on output that can never pass anyway.
        outcome, reason = _classify_worker_outcome(result)
        if outcome is WorkerRunOutcome.SUCCESS and workspace_path is not None and result.patches:
            target_paths = tuple(patch.target_path for patch in result.patches)
            staged = _staged_files_from_workspace(workspace_path, target_paths, transport_source)
            staging = QuarantinedStaging(
                staging_id=staging_id or f"sandbox-{run_id}",
                project_root=workspace_path,
                approved_scope=work_order.allowed_path_globs,
            )
            for item in staged:
                staging.stage(item)
            inspection = staging.inspect()
            if not inspection.clean:
                findings = ", ".join(sorted({f.kind.value for f in inspection.findings}))
                outcome = WorkerRunOutcome.FAILED
                reason = f"staging inspection findings: {findings}"

        exec_result = _to_execution_result(task_id, outcome, reason)
        return self._finalize_run(
            task_id=task_id,
            run_id=run_id,
            attempt=attempt,
            transport_source=transport_source,
            selected_mode=decision.selected_mode,
            workspace=workspace,
            staging_dir=staging_dir,
            outcome=outcome,
            reason=reason,
            exec_result=exec_result,
        )

    def _finalize_run(
        self,
        *,
        task_id: str,
        run_id: str,
        attempt: int,
        transport_source: str,
        selected_mode: ExecutionMode,
        workspace: Workspace | None,
        staging_dir: Path | None,
        outcome: WorkerRunOutcome,
        reason: str,
        exec_result: ExecutionResult,
    ) -> RunSummary:
        retry_scheduled = False
        is_retryable_failure = outcome in (WorkerRunOutcome.FAILED, WorkerRunOutcome.CRASHED)

        if is_retryable_failure and not self.retry_policy.is_exhausted(attempt):
            # Park at BLOCKED with a recorded retry-pending cause instead of finalizing to
            # FAILED -- retry_blocked_tasks() is the only thing that will ever resume a task
            # blocked for exactly this reason. Falls back to a normal FAILED finalize if the
            # BLOCKED transition is unexpectedly rejected (e.g. a concurrent cancellation already
            # moved the task elsewhere) rather than silently reporting a retry that never
            # actually happened.
            record = self.orchestrator_reader.get_task(task_id)
            current = record.current_state if record is not None else TaskState.RUNNING
            event = self.orchestrator_writer.apply_transition(
                task_id=task_id,
                expected_current_state=current,
                new_state=TaskState.BLOCKED,
                cause=_RETRY_PENDING_CAUSE,
                actor=self.actor,
            )
            retry_scheduled = event.accepted
            if not retry_scheduled:
                self._integration.finalize(task_id, exec_result, actor=self.actor)
        else:
            self._integration.finalize(task_id, exec_result, actor=self.actor)

        self.run_writer.finish_run(run_id=run_id, outcome=outcome, reason=reason)

        # A failed/cancelled/crashed run's workspace is disposed of immediately -- nothing from
        # it will ever be verified or promoted. A successful run's workspace/staging dir is kept
        # on disk (frozen, not deleted) for the Verification Engine to inspect.
        if outcome is not WorkerRunOutcome.SUCCESS:
            if selected_mode is ExecutionMode.SANDBOXED_EXECUTION and workspace is not None:
                self.workspace_manager.destroy(self.repo_root, workspace)
            elif staging_dir is not None:
                shutil.rmtree(staging_dir, ignore_errors=True)

        return RunSummary(
            task_id=task_id,
            run_id=run_id,
            transport_source=transport_source,
            selected_mode=selected_mode,
            outcome=outcome,
            reason=reason,
            retry_scheduled=retry_scheduled,
        )
