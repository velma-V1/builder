"""Local-dev entrypoint for the read-only task-snapshot API (Phase 2B, CMP-API).

Starts the Starlette app from ``factory.api.create_app`` behind uvicorn, backed by a
``SQLiteOrchestratorStateReader`` over the existing Orchestrator runtime-state database.

This process is read-only end to end: it never calls ``apply_migrations`` and never opens
a writable connection to the database. Startup only checks (read-only) that the database's
complete applied migration-version set exactly equals the complete expected set on disk; if
the database is missing, or its migration history is anything other than an exact match
(missing entirely, gapped, or containing unexpected future versions), startup fails with a
clear, bounded message pointing at ``scripts/setup_api_database.py`` instead of silently
mutating or repairing the schema. A maximum-version-only check cannot detect a gap (e.g.
``{1, 2, 4}`` has the same maximum as ``{1, 2, 3, 4}``), which is exactly why this compares
the full sets.

Usage:
    uv run python scripts/setup_api_database.py --database-path runtime.db   # once, or after
                                                                              # a migration bump
    uv run python scripts/run_api.py --database-path runtime.db
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import uvicorn

from factory.api import create_app
from factory.orchestrator.store.runtime_state import SQLiteOrchestratorStateReader

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
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    require_current_schema_or_exit(args.database_path, args.migrations_root, _SETUP_COMMAND)

    reader = SQLiteOrchestratorStateReader(database_path=args.database_path)
    app = create_app(task_reader=reader)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
