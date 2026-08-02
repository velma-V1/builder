"""Shared fixtures for Phase 3B's worker-engine service tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from factory.git.manager import GitManager
from factory.integrations.agent_zero.policy import AgentZeroModelResult
from factory.orchestrator.store.runtime_state import (
    SQLiteOrchestratorStateReader,
    _OrchestratorStateWriter,
    apply_migrations,
)
from factory.worker_engine.model_router import FakeModelRouter
from factory.worker_engine.service import WorkerEngineService
from factory.worker_engine.store import SQLiteWorkerRunReader, _WorkerRunWriter
from factory.worker_engine.workspace import WorkspaceManager

MIGRATIONS_ROOT = Path(__file__).resolve().parents[2] / "migrations" / "runtime"

_SUCCESSFUL_OUTPUT = "---BEGIN NEW CONTENT---\nHello\n---END NEW CONTENT---"


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "runtime.db"
    apply_migrations(path, MIGRATIONS_ROOT)
    return path


@pytest.fixture
def orchestrator_writer(db_path: Path) -> _OrchestratorStateWriter:
    return _OrchestratorStateWriter(database_path=db_path)


@pytest.fixture
def orchestrator_reader(db_path: Path) -> SQLiteOrchestratorStateReader:
    return SQLiteOrchestratorStateReader(database_path=db_path)


@pytest.fixture
def run_writer(db_path: Path) -> _WorkerRunWriter:
    return _WorkerRunWriter(database_path=db_path)


@pytest.fixture
def run_reader(db_path: Path) -> SQLiteWorkerRunReader:
    return SQLiteWorkerRunReader(database_path=db_path)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    GitManager().init_repo(path)
    return path


@pytest.fixture
def git() -> GitManager:
    return GitManager()


@pytest.fixture
def workspace_manager(git: GitManager, tmp_path: Path) -> WorkspaceManager:
    return WorkspaceManager(git, tmp_path / "sandboxes")


@pytest.fixture
def successful_router() -> FakeModelRouter:
    return FakeModelRouter(
        default=AgentZeroModelResult(
            ok=True,
            output=_SUCCESSFUL_OUTPUT,
            model_fingerprint="fp",
            provider_route="fake",
        )
    )


@pytest.fixture
def failing_router() -> FakeModelRouter:
    return FakeModelRouter(
        default=AgentZeroModelResult(
            ok=False,
            output="",
            model_fingerprint="fp",
            provider_route="fake",
            reason="boom",
        )
    )


@pytest.fixture
def service(
    orchestrator_writer: _OrchestratorStateWriter,
    orchestrator_reader: SQLiteOrchestratorStateReader,
    run_writer: _WorkerRunWriter,
    run_reader: SQLiteWorkerRunReader,
    git: GitManager,
    workspace_manager: WorkspaceManager,
    repo: Path,
    successful_router: FakeModelRouter,
) -> WorkerEngineService:
    return WorkerEngineService(
        orchestrator_writer=orchestrator_writer,
        orchestrator_reader=orchestrator_reader,
        run_writer=run_writer,
        run_reader=run_reader,
        git=git,
        workspace_manager=workspace_manager,
        repo_root=repo,
        model_router=successful_router,
    )


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
