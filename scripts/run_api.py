"""Local-dev entrypoint for the read-only task-snapshot API (Phase 2B, CMP-API).

Starts the Starlette app from ``factory.api.create_app`` behind uvicorn, backed by a
``SQLiteOrchestratorStateReader`` over the existing Orchestrator runtime-state database.
Applies pending runtime migrations first (idempotent — see
``factory.orchestrator.store.runtime_state.apply_migrations``); never modifies the frozen
0001-0003 migrations, only appends the pinned 0004 workstream-membership column.

No writer is constructed or imported here: this process can only ever read.

Usage:
    uv run python scripts/run_api.py --database-path runtime.db
"""

from __future__ import annotations

import argparse
from pathlib import Path

import uvicorn

from factory.api import create_app
from factory.orchestrator.store.runtime_state import (
    SQLiteOrchestratorStateReader,
    apply_migrations,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_MIGRATIONS_ROOT = _REPO_ROOT / "migrations" / "runtime"
_DEFAULT_DATABASE_PATH = _REPO_ROOT / "runtime.db"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-path", type=Path, default=_DEFAULT_DATABASE_PATH)
    parser.add_argument("--migrations-root", type=Path, default=_DEFAULT_MIGRATIONS_ROOT)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    apply_migrations(args.database_path, args.migrations_root)
    reader = SQLiteOrchestratorStateReader(database_path=args.database_path)
    app = create_app(task_reader=reader)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
