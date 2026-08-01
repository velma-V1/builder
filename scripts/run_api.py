"""Local-dev entrypoint for the read-only task-snapshot API (Phase 2B, CMP-API).

Starts the Starlette app from ``factory.api.create_app`` behind uvicorn, backed by a
``SQLiteOrchestratorStateReader`` over the existing Orchestrator runtime-state database.

This process is read-only end to end: it never calls ``apply_migrations`` and never opens
a writable connection to the database. Startup only checks (read-only) that the database
exists and its recorded schema version is current; if the database is missing or its
schema is out of date, startup fails with a clear, bounded message pointing at
``scripts/setup_api_database.py`` instead of silently mutating the schema.

Usage:
    uv run python scripts/setup_api_database.py --database-path runtime.db   # once, or after
                                                                              # a migration bump
    uv run python scripts/run_api.py --database-path runtime.db
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

import uvicorn

from factory.api import create_app
from factory.orchestrator.store.runtime_state import (
    SQLiteOrchestratorStateReader,
    applied_schema_version,
    latest_migration_version,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_MIGRATIONS_ROOT = _REPO_ROOT / "migrations" / "runtime"
_DEFAULT_DATABASE_PATH = _REPO_ROOT / "runtime.db"
_SETUP_COMMAND = "uv run python scripts/setup_api_database.py"


def _require_current_schema(database_path: Path, migrations_root: Path) -> None:
    expected_version = latest_migration_version(migrations_root)
    try:
        actual_version = applied_schema_version(database_path)
    except sqlite3.OperationalError:
        sys.exit(
            f"Database not found or unreadable at {database_path}.\n"
            f"Run the setup command first:\n"
            f"  {_SETUP_COMMAND} --database-path {database_path}"
        )

    if actual_version < expected_version:
        sys.exit(
            f"Database schema at {database_path} is out of date "
            f"(applied version {actual_version}, expected {expected_version}).\n"
            f"Run the setup command first:\n"
            f"  {_SETUP_COMMAND} --database-path {database_path}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-path", type=Path, default=_DEFAULT_DATABASE_PATH)
    parser.add_argument("--migrations-root", type=Path, default=_DEFAULT_MIGRATIONS_ROOT)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    _require_current_schema(args.database_path, args.migrations_root)

    reader = SQLiteOrchestratorStateReader(database_path=args.database_path)
    app = create_app(task_reader=reader)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
