"""Phase 3B ``WorkerEngineService`` integration tests: atomic claiming, all three execution
modes end to end, crash/restart reconciliation, retry/exhaustion, and Agent Zero unavailable ->
Builder-native fallback (explicit, recorded, never silent).
"""

from __future__ import annotations

import threading
from pathlib import Path

from factory.git.manager import GitManager
from factory.orchestrator.models import TaskState
from factory.orchestrator.store.runtime_state import (
    SQLiteOrchestratorStateReader,
    _OrchestratorStateWriter,
)
from factory.worker_engine.execution_policy import ExecutionMode
from factory.worker_engine.model_router import FakeModelRouter
from factory.worker_engine.models import WorkerRunOutcome
from factory.worker_engine.service import (
    TRANSPORT_AGENT_ZERO_REAL,
    TRANSPORT_BUILDER_NATIVE,
    WorkerEngineService,
)
from factory.worker_engine.store import SQLiteWorkerRunReader, _WorkerRunWriter
from factory.worker_engine.workspace import WorkspaceManager
from factory.workers.recovery import RetryPolicy


def current_state(reader: SQLiteOrchestratorStateReader, task_id: str) -> TaskState:
    record = reader.get_task(task_id)
    assert record is not None, f"task {task_id} does not exist"
    return record.current_state


def submit_task(
    writer: _OrchestratorStateWriter,
    *,
    description: str,
    workstream_id: str = "ws-1",
    idempotency_key: str = "k1",
) -> str:
    result = writer.submit_task_request(
        project_ref="builder",
        workstream_id=workstream_id,
        description=description,
        priority="normal",
        model_preference=None,
        expected_result=None,
        submitted_by="tester",
        idempotency_key=idempotency_key,
    )
    return result.task_id


def test_direct_read_only_task_completes_with_no_sandbox_or_staging(
    service: WorkerEngineService,
    orchestrator_writer: _OrchestratorStateWriter,
    orchestrator_reader: SQLiteOrchestratorStateReader,
) -> None:
    task_id = submit_task(orchestrator_writer, description="Explain what this repo does.")
    summary = service.claim_and_run(task_id)
    assert summary is not None
    assert summary.selected_mode is ExecutionMode.DIRECT_READ_ONLY
    assert summary.outcome is WorkerRunOutcome.SUCCESS
    run = service.run_reader.get_run(summary.run_id)
    assert run is not None
    assert run.sandbox_path is None
    assert run.staging_id is None
    assert current_state(orchestrator_reader, task_id) is TaskState.VERIFYING


def test_staged_write_task_uses_a_temp_staging_dir_not_a_git_worktree(
    service: WorkerEngineService,
    orchestrator_writer: _OrchestratorStateWriter,
) -> None:
    task_id = submit_task(
        orchestrator_writer,
        description="mode: staged_write\ncommand: edit_file\nwrite_intent: true\n"
        "target: notes.md\nWrite some notes.",
    )
    summary = service.claim_and_run(task_id)
    assert summary is not None
    assert summary.selected_mode is ExecutionMode.STAGED_WRITE
    run = service.run_reader.get_run(summary.run_id)
    assert run is not None
    assert run.staging_id is not None
    # sandbox_path is populated (it means "where this run's output lives", not "is this a git
    # worktree") but it must be a plain temp dir, never a git worktree/branch.
    assert run.sandbox_path is not None
    assert run.branch_ref is None
    assert run.base_sha is None


def test_sandboxed_execution_task_provisions_a_real_worktree(
    service: WorkerEngineService,
    orchestrator_writer: _OrchestratorStateWriter,
) -> None:
    task_id = submit_task(
        orchestrator_writer,
        description="mode: sandboxed_execution\ncommand: run_tests\ntarget: hello.txt\nWrite.",
    )
    summary = service.claim_and_run(task_id)
    assert summary is not None
    assert summary.selected_mode is ExecutionMode.SANDBOXED_EXECUTION
    run = service.run_reader.get_run(summary.run_id)
    assert run is not None
    assert run.sandbox_path is not None
    assert Path(run.sandbox_path).is_dir()  # kept on disk (frozen) for verification


def test_policy_forces_sandbox_even_for_a_read_only_request(
    service: WorkerEngineService,
    orchestrator_writer: _OrchestratorStateWriter,
) -> None:
    task_id = submit_task(
        orchestrator_writer,
        description="command: install_dependency\nAdd a new package.",
    )
    summary = service.claim_and_run(task_id)
    assert summary is not None
    assert summary.selected_mode is ExecutionMode.SANDBOXED_EXECUTION
    run = service.run_reader.get_run(summary.run_id)
    assert run is not None
    assert run.requested_mode is ExecutionMode.DIRECT_READ_ONLY
    assert run.selected_mode is ExecutionMode.SANDBOXED_EXECUTION


def test_duplicate_claim_race_only_one_thread_wins(
    orchestrator_writer: _OrchestratorStateWriter,
    orchestrator_reader: SQLiteOrchestratorStateReader,
    run_writer: _WorkerRunWriter,
    run_reader: SQLiteWorkerRunReader,
    git: GitManager,
    workspace_manager: WorkspaceManager,
    repo: Path,
    successful_router: FakeModelRouter,
) -> None:
    """Two WorkerEngineService instances (simulating two worker processes) racing to claim the
    exact same QUEUED task must never both succeed -- exactly one wins, the other loses the
    race cleanly (returns None, never raises, never double-executes)."""
    task_id = submit_task(orchestrator_writer, description="Explain what this repo does.")

    services = [
        WorkerEngineService(
            orchestrator_writer=orchestrator_writer,
            orchestrator_reader=orchestrator_reader,
            run_writer=run_writer,
            run_reader=run_reader,
            git=git,
            workspace_manager=workspace_manager,
            repo_root=repo,
            model_router=successful_router,
        )
        for _ in range(8)
    ]
    results: list[object] = [None] * 8

    def _attempt(index: int) -> None:
        results[index] = services[index].claim_and_run(task_id)

    threads = [threading.Thread(target=_attempt, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    winners = [r for r in results if r is not None]
    assert len(winners) == 1, f"expected exactly one winner, got {len(winners)}: {winners}"

    runs = run_reader.list_runs_for_task(task_id)
    assert len(runs) == 1, "the task must have been executed exactly once, never duplicated"


def test_crash_reconciliation_never_blindly_resumes_a_running_task(
    orchestrator_writer: _OrchestratorStateWriter,
    orchestrator_reader: SQLiteOrchestratorStateReader,
    run_writer: _WorkerRunWriter,
    run_reader: SQLiteWorkerRunReader,
    git: GitManager,
    workspace_manager: WorkspaceManager,
    repo: Path,
    successful_router: FakeModelRouter,
) -> None:
    task_id = submit_task(orchestrator_writer, description="Explain what this repo does.")
    # Simulate a prior process having claimed the task and then crashing mid-RUNNING.
    orchestrator_writer.apply_transition(
        task_id=task_id,
        expected_current_state=TaskState.QUEUED,
        new_state=TaskState.PLANNING,
        cause="dispatch",
        actor="prior-process",
    )
    orchestrator_writer.apply_transition(
        task_id=task_id,
        expected_current_state=TaskState.PLANNING,
        new_state=TaskState.RUNNING,
        cause="worker_ready",
        actor="prior-process",
    )

    service = WorkerEngineService(
        orchestrator_writer=orchestrator_writer,
        orchestrator_reader=orchestrator_reader,
        run_writer=run_writer,
        run_reader=run_reader,
        git=git,
        workspace_manager=workspace_manager,
        repo_root=repo,
        model_router=successful_router,
    )
    outcomes = service.recover_on_startup()
    assert task_id in outcomes

    assert current_state(orchestrator_reader, task_id) is TaskState.BLOCKED, (
        "a RUNNING task found at startup must reconcile to BLOCKED, never silently resume"
    )


def test_retry_exhaustion_eventually_finalizes_to_failed(
    orchestrator_writer: _OrchestratorStateWriter,
    orchestrator_reader: SQLiteOrchestratorStateReader,
    run_writer: _WorkerRunWriter,
    run_reader: SQLiteWorkerRunReader,
    git: GitManager,
    workspace_manager: WorkspaceManager,
    repo: Path,
    failing_router: FakeModelRouter,
) -> None:
    task_id = submit_task(
        orchestrator_writer,
        description="mode: sandboxed_execution\ncommand: run_tests\ntarget: x.txt\nWrite.",
    )
    service = WorkerEngineService(
        orchestrator_writer=orchestrator_writer,
        orchestrator_reader=orchestrator_reader,
        run_writer=run_writer,
        run_reader=run_reader,
        git=git,
        workspace_manager=workspace_manager,
        repo_root=repo,
        model_router=failing_router,
        retry_policy=RetryPolicy(max_attempts=1),
    )
    first = service.claim_and_run(task_id)
    assert first is not None
    assert first.retry_scheduled is True
    assert current_state(orchestrator_reader, task_id) is TaskState.BLOCKED

    retried = service.retry_blocked_tasks()
    assert len(retried) == 1
    assert retried[0].retry_scheduled is False
    assert current_state(orchestrator_reader, task_id) is TaskState.FAILED

    runs = run_reader.list_runs_for_task(task_id)
    assert len(runs) == 2, "exactly two attempts should have been made (1 initial + 1 retry)"


def test_retry_blocked_tasks_never_touches_a_task_blocked_for_an_unrelated_reason(
    orchestrator_writer: _OrchestratorStateWriter,
    orchestrator_reader: SQLiteOrchestratorStateReader,
    run_writer: _WorkerRunWriter,
    run_reader: SQLiteWorkerRunReader,
    git: GitManager,
    workspace_manager: WorkspaceManager,
    repo: Path,
    successful_router: FakeModelRouter,
) -> None:
    task_id = submit_task(orchestrator_writer, description="Explain what this repo does.")
    orchestrator_writer.apply_transition(
        task_id=task_id,
        expected_current_state=TaskState.QUEUED,
        new_state=TaskState.PLANNING,
        cause="dispatch",
        actor="x",
    )
    orchestrator_writer.apply_transition(
        task_id=task_id,
        expected_current_state=TaskState.PLANNING,
        new_state=TaskState.RUNNING,
        cause="worker_ready",
        actor="x",
    )
    orchestrator_writer.apply_transition(
        task_id=task_id,
        expected_current_state=TaskState.RUNNING,
        new_state=TaskState.BLOCKED,
        cause="manual_review_requested",
        actor="operator",
    )

    service = WorkerEngineService(
        orchestrator_writer=orchestrator_writer,
        orchestrator_reader=orchestrator_reader,
        run_writer=run_writer,
        run_reader=run_reader,
        git=git,
        workspace_manager=workspace_manager,
        repo_root=repo,
        model_router=successful_router,
    )
    retried = service.retry_blocked_tasks()
    assert retried == ()
    assert current_state(orchestrator_reader, task_id) is TaskState.BLOCKED


def test_agent_zero_unavailable_falls_back_to_builder_native_explicitly(
    orchestrator_writer: _OrchestratorStateWriter,
    orchestrator_reader: SQLiteOrchestratorStateReader,
    run_writer: _WorkerRunWriter,
    run_reader: SQLiteWorkerRunReader,
    git: GitManager,
    workspace_manager: WorkspaceManager,
    repo: Path,
    successful_router: FakeModelRouter,
) -> None:
    from factory.worker_engine.agent_zero_process_client import AgentZeroProcessClient

    task_id = submit_task(orchestrator_writer, description="Explain what this repo does.")
    unreachable_client = AgentZeroProcessClient(
        base_url="http://127.0.0.1:1",
        ollama_base_url="http://127.0.0.1:11434",
        model_tag="devstral-small-2:24b",
        timeout_s=1,
    )
    service = WorkerEngineService(
        orchestrator_writer=orchestrator_writer,
        orchestrator_reader=orchestrator_reader,
        run_writer=run_writer,
        run_reader=run_reader,
        git=git,
        workspace_manager=workspace_manager,
        repo_root=repo,
        model_router=successful_router,
        agent_zero_client=unreachable_client,
    )
    summary = service.claim_and_run(task_id)
    assert summary is not None
    assert summary.transport_source == TRANSPORT_BUILDER_NATIVE
    run = run_reader.get_run(summary.run_id)
    assert run is not None
    assert TRANSPORT_BUILDER_NATIVE in run.work_order_json
    assert TRANSPORT_AGENT_ZERO_REAL not in run.work_order_json


def test_cancellation_before_execution_starts_is_honored(
    orchestrator_writer: _OrchestratorStateWriter,
    orchestrator_reader: SQLiteOrchestratorStateReader,
    run_writer: _WorkerRunWriter,
    run_reader: SQLiteWorkerRunReader,
    git: GitManager,
    workspace_manager: WorkspaceManager,
    repo: Path,
) -> None:
    """A cancellation requested for a QUEUED task before any claim attempt must leave the task
    CANCELLED, and a later claim attempt must not run it."""
    from factory.orchestrator.queue.scheduler import finalize_cancellation, request_cancellation

    task_id = submit_task(orchestrator_writer, description="Explain what this repo does.")
    # QUEUED's only legal edge is PLANNING (matches orchestrator_api's TaskOperatorService.cancel
    # pre-step) -- request_cancellation/finalize_cancellation only walk ->STOPPING->CANCELLED.
    orchestrator_writer.apply_transition(
        task_id=task_id,
        expected_current_state=TaskState.QUEUED,
        new_state=TaskState.PLANNING,
        cause="pre_cancel_planning",
        actor="op",
    )
    request_cancellation(
        orchestrator_writer, orchestrator_reader, task_id, reason="operator", actor="op"
    )
    finalize_cancellation(orchestrator_writer, orchestrator_reader, task_id, actor="op")
    assert current_state(orchestrator_reader, task_id) is TaskState.CANCELLED

    service = WorkerEngineService(
        orchestrator_writer=orchestrator_writer,
        orchestrator_reader=orchestrator_reader,
        run_writer=run_writer,
        run_reader=run_reader,
        git=git,
        workspace_manager=workspace_manager,
        repo_root=repo,
        model_router=FakeModelRouter(),
    )
    # A CANCELLED task is not QUEUED, so claim_and_run must lose the "claim" (no legal
    # CANCELLED -> PLANNING edge) and never execute it.
    result = service.claim_and_run(task_id)
    assert result is None
    assert run_reader.list_runs_for_task(task_id) == ()
