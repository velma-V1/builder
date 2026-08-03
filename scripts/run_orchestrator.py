"""Local-dev entrypoint for the write-authorized orchestrator API (Phase 3A, CMP-ORCH-API).

Starts the Starlette app from ``factory.orchestrator_api.create_app`` behind uvicorn, backed
by a ``TaskOperatorService`` that holds the single authoritative writer
(``_OrchestratorStateWriter``, R1) plus a read-only reader. Separate from ``scripts/run_api.py``
(the read-only snapshot API, :8000, never holds a writer) — this process is where all Phase 3A
write authority lives.

This process never calls ``apply_migrations`` itself; startup only checks (read-only) that the
database's applied migration-version set exactly equals the expected set on disk, exactly like
``run_api.py``, via the shared ``scripts/_schema_check`` helper. If the schema is missing or
outdated, startup fails with a clear, bounded message pointing at
``scripts/setup_api_database.py`` instead of silently mutating or repairing anything.

No approve/reject route exists here (Phase 3A) -- nothing can legitimately be approved before a
real worker produces results.

Usage:
    uv run python scripts/setup_api_database.py --database-path runtime.db   # once, or after
                                                                              # a migration bump
    uv run python scripts/run_orchestrator.py --database-path runtime.db
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import uvicorn
from _config import load_config
from _schema_check import require_current_schema_or_exit

from factory.approval import ApprovalEngine, SystemClock
from factory.audit import AuditWriter
from factory.git.manager import GitManager
from factory.integrations.agent_zero.official_client import AgentZeroOfficialClient
from factory.integrations.control import IntegrationControlService
from factory.integrations.loopback_transport import LoopbackHttpTransport
from factory.integrations.migrations import require_current_schema
from factory.integrations.model_gateway import ModelGateway
from factory.integrations.runtime import (
    IntegrationName,
    IntegrationRuntime,
    IntegrationStore,
    ManagedServiceSpec,
    SubprocessCommandRunner,
)
from factory.integrations.worldmonitor.official_client import WorldMonitorOfficialClient
from factory.models.ollama_adapter.live_ollama import OllamaClient
from factory.orchestrator.models import TaskState
from factory.orchestrator.store.runtime_state import (
    SQLiteOrchestratorStateReader,
    _OrchestratorStateWriter,
)
from factory.orchestrator_api import OperatorSession, Phase3BLifecycleService, create_app
from factory.orchestrator_api.service import TaskOperatorService
from factory.promotion import PromotionService, SQLitePromotionReader
from factory.verification import DockerIsolatedCommandRunner, SQLiteVerificationReader
from factory.verification.engine import VerificationEngine
from factory.verification.store import _VerificationWriter
from factory.worker_engine.agent_zero_process_client import (
    AgentZeroTransportFactory,
    OfficialAgentZeroTransportFactory,
)
from factory.worker_engine.model_router import LiveOllamaModelRouter
from factory.worker_engine.service import WorkerEngineService
from factory.worker_engine.store import SQLiteWorkerRunReader, _WorkerRunWriter
from factory.worker_engine.workspace import WorkspaceManager

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_MIGRATIONS_ROOT = _REPO_ROOT / "migrations" / "runtime"
_DEFAULT_DATABASE_PATH = _REPO_ROOT / "runtime.db"
_SETUP_COMMAND = "uv run python scripts/setup_api_database.py"


def _build_phase3b(
    args: argparse.Namespace,
    writer: _OrchestratorStateWriter,
    reader: SQLiteOrchestratorStateReader,
    agent_zero_factory: AgentZeroTransportFactory | None = None,
) -> tuple[Phase3BLifecycleService, WorkerEngineService | None]:
    assert args.security_database_path is not None
    assert args.audit_database_path is not None
    git = GitManager()
    verification_reader = SQLiteVerificationReader(args.database_path)
    verifier = VerificationEngine(
        writer,
        reader,
        _VerificationWriter(args.database_path),
        git,
        _REPO_ROOT,
        command_runner=DockerIsolatedCommandRunner(args.verifier_image),
    )
    approval = ApprovalEngine(args.security_database_path, args.audit_database_path, SystemClock())
    promotion = PromotionService(
        args.database_path,
        _REPO_ROOT,
        writer,
        reader,
        verification_reader,
        approval,
        git,
    )
    phase3b = Phase3BLifecycleService(
        reader,
        verification_reader,
        SQLiteWorkerRunReader(args.database_path),
        approval,
        promotion,
        SQLitePromotionReader(args.database_path),
        git,
        _REPO_ROOT,
        verifier,
    )
    phase3b.reconcile_startup()
    worker = None
    if args.enable_worker:
        run_reader = SQLiteWorkerRunReader(args.database_path)
        worker = WorkerEngineService(
            orchestrator_writer=writer,
            orchestrator_reader=reader,
            run_writer=_WorkerRunWriter(args.database_path),
            run_reader=run_reader,
            git=git,
            workspace_manager=WorkspaceManager(git, args.sandbox_root),
            repo_root=_REPO_ROOT,
            model_router=LiveOllamaModelRouter(OllamaClient(), args.ollama_model),
            verifier=verifier,
            agent_zero_factory=agent_zero_factory,
        )
        worker.recover_on_startup()
    return phase3b, worker


def _build_integrations(args: argparse.Namespace) -> IntegrationControlService:
    transport = LoopbackHttpTransport()
    config = load_config(getattr(args, "config_path", _REPO_ROOT / "config" / "builder.yaml"))
    if config.integrations is None:
        raise RuntimeError("managed integration configuration is unavailable")
    agent_config = config.integrations.agent_zero
    world_config = config.integrations.worldmonitor
    specs = {
        IntegrationName.AGENT_ZERO: ManagedServiceSpec(
            IntegrationName.AGENT_ZERO,
            agent_config.release,
            agent_config.commit,
            _REPO_ROOT / "deploy" / "integrations" / "agent-zero" / "compose.yaml",
            agent_config.port,
            f"http://127.0.0.1:{agent_config.port}",
            agent_config.timeout_s,
            agent_config.enabled,
            True,
            True,
        ),
        IntegrationName.WORLDMONITOR: ManagedServiceSpec(
            IntegrationName.WORLDMONITOR,
            world_config.release,
            world_config.commit,
            _REPO_ROOT / "deploy" / "integrations" / "worldmonitor" / "compose.yaml",
            world_config.port,
            f"http://127.0.0.1:{world_config.port}",
            world_config.timeout_s,
            world_config.enabled,
            True,
            True,
        ),
    }
    require_current_schema(args.integration_state_path, _REPO_ROOT / "migrations" / "integrations")
    store = IntegrationStore(args.integration_state_path)
    runtime = IntegrationRuntime(store, SubprocessCommandRunner(), lambda: int(time.time()))
    service = IntegrationControlService(
        runtime,
        specs,
        WorldMonitorOfficialClient(
            f"http://127.0.0.1:{world_config.port}", transport, world_config.timeout_s
        ),
        AuditWriter(args.audit_database_path),
        lambda: int(time.time() * 1000),
    )
    runtime.reconcile(tuple(specs.values()))
    service.reconcile_operations(
        lambda task_id: (
            record.current_state
            if (record := SQLiteOrchestratorStateReader(args.database_path).get_task(task_id))
            else None
        )
    )
    return service


def _worker_loop(worker: WorkerEngineService, poll_interval_s: float) -> None:
    while True:
        worker.run_all_claimable()
        worker.retry_blocked_tasks()
        time.sleep(poll_interval_s)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-path", type=Path, default=_DEFAULT_DATABASE_PATH)
    parser.add_argument("--migrations-root", type=Path, default=_DEFAULT_MIGRATIONS_ROOT)
    parser.add_argument("--security-database-path", type=Path)
    parser.add_argument("--audit-database-path", type=Path)
    parser.add_argument("--enable-worker", action="store_true")
    parser.add_argument("--verifier-image", default="builder-verifier:phase3b")
    parser.add_argument("--ollama-model", default="devstral-small-2:24b")
    parser.add_argument("--sandbox-root", type=Path, default=_REPO_ROOT / ".builder-sandboxes")
    parser.add_argument("--worker-poll-interval", type=float, default=1.0)
    parser.add_argument(
        "--integration-state-path", type=Path, default=_REPO_ROOT / "integrations.db"
    )
    parser.add_argument("--config-path", type=Path, default=_REPO_ROOT / "config" / "builder.yaml")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8100)
    args = parser.parse_args()

    require_current_schema_or_exit(args.database_path, args.migrations_root, _SETUP_COMMAND)

    writer = _OrchestratorStateWriter(database_path=args.database_path)
    reader = SQLiteOrchestratorStateReader(database_path=args.database_path)
    phase3b = None
    worker = None
    operator_session = None
    integration_control = None
    model_gateway = None
    if (args.security_database_path is None) != (args.audit_database_path is None):
        parser.error("security and audit database paths must be supplied together")
    if args.security_database_path is not None and args.audit_database_path is not None:
        credential = os.environ.get("BUILDER_OPERATOR_SESSION_TOKEN")
        if not credential:
            parser.error("BUILDER_OPERATOR_SESSION_TOKEN is required for Phase 3B")
        operator_session = OperatorSession(credential=credential, operator="local-operator")
        config = load_config(args.config_path)
        if config.integrations is None:
            parser.error("managed integration configuration is unavailable")
        agent_config = config.integrations.agent_zero
        agent_zero_credential = os.environ.get("BUILDER_AGENT_ZERO_API_KEY", "")
        if agent_config.enabled and not agent_zero_credential:
            parser.error("BUILDER_AGENT_ZERO_API_KEY is required when Agent Zero is enabled")
        agent_zero_factory = (
            OfficialAgentZeroTransportFactory(
                lambda: AgentZeroOfficialClient(
                    f"http://127.0.0.1:{agent_config.port}",
                    agent_zero_credential,
                    LoopbackHttpTransport(),
                    agent_config.timeout_s,
                ),
                lambda task_id: (
                    (record := reader.get_task(task_id)) is not None
                    and record.current_state in {TaskState.STOPPING, TaskState.CANCELLED}
                ),
            )
            if agent_config.enabled
            else None
        )
        phase3b, worker = _build_phase3b(args, writer, reader, agent_zero_factory)
        integration_control = _build_integrations(args)
        if agent_config.enabled:
            gateway_credential = os.environ.get("BUILDER_MODEL_GATEWAY_TOKEN")
            if not gateway_credential:
                parser.error("BUILDER_MODEL_GATEWAY_TOKEN is required when Agent Zero is enabled")
            model_gateway = ModelGateway(
                LiveOllamaModelRouter(OllamaClient(), args.ollama_model),
                gateway_credential,
                args.ollama_model,
            )
    service = TaskOperatorService(writer=writer, reader=reader, phase3b=phase3b)
    app = create_app(
        service=service,
        operator_session=operator_session,
        integration_control=integration_control,
        model_gateway=model_gateway,
    )
    if worker is not None:
        threading.Thread(
            target=_worker_loop,
            args=(worker, args.worker_poll_interval),
            daemon=True,
            name="builder-worker-loop",
        ).start()
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
