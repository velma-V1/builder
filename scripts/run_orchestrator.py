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
import sys
from pathlib import Path

import uvicorn

from factory.orchestrator.store.runtime_state import (
    SQLiteOrchestratorStateReader,
    _OrchestratorStateWriter,
)
from factory.orchestrator_api import create_app
from factory.orchestrator_api.service import TaskOperatorService

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _schema_check import require_current_schema_or_exit

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_MIGRATIONS_ROOT = _REPO_ROOT / "migrations" / "runtime"
_DEFAULT_DATABASE_PATH = _REPO_ROOT / "runtime.db"
_SETUP_COMMAND = "uv run python scripts/setup_api_database.py"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-path", type=Path, default=_DEFAULT_DATABASE_PATH)
    parser.add_argument("--migrations-root", type=Path, default=_DEFAULT_MIGRATIONS_ROOT)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8100)
    args = parser.parse_args()

    require_current_schema_or_exit(args.database_path, args.migrations_root, _SETUP_COMMAND)

    writer = _OrchestratorStateWriter(database_path=args.database_path)
    reader = SQLiteOrchestratorStateReader(database_path=args.database_path)
    service = TaskOperatorService(writer=writer, reader=reader)
    app = create_app(service=service)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
