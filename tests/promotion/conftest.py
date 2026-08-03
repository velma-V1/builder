from __future__ import annotations

from pathlib import Path

import pytest

from factory.orchestrator.store.runtime_state import _OrchestratorStateWriter, apply_migrations
from factory.worker_engine.execution_policy import ExecutionMode
from factory.worker_engine.store import _WorkerRunWriter

MIGRATIONS_ROOT = Path(__file__).resolve().parents[2] / "migrations" / "runtime"


@pytest.fixture
def verification_db(tmp_path: Path) -> tuple[Path, str]:
    path = tmp_path / "runtime.db"
    apply_migrations(path, MIGRATIONS_ROOT)
    task = _OrchestratorStateWriter(path).submit_task_request(
        project_ref="builder",
        workstream_id="ws-1",
        description="promote",
        priority="normal",
        model_preference=None,
        expected_result=None,
        submitted_by="tester",
        idempotency_key="promotion-fixture",
    )
    _WorkerRunWriter(path).create_run(
        run_id="run-1",
        task_id=task.task_id,
        attempt=1,
        requested_mode=ExecutionMode.SANDBOXED_EXECUTION,
        selected_mode=ExecutionMode.SANDBOXED_EXECUTION,
        mode_reason="test",
        policy_rule="test",
        work_order_json="{}",
        model_route_token="",
    )
    return path, task.task_id
