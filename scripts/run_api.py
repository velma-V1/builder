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
import sqlite3
import sys
from pathlib import Path

import uvicorn

from factory.api import create_app
from factory.orchestrator.errors import OrchestratorError
from factory.orchestrator.store.runtime_state import (
    SQLiteOrchestratorStateReader,
    applied_migration_versions,
    expected_migration_versions,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_MIGRATIONS_ROOT = _REPO_ROOT / "migrations" / "runtime"
_DEFAULT_DATABASE_PATH = _REPO_ROOT / "runtime.db"
_SETUP_COMMAND = "uv run python scripts/setup_api_database.py"


def _format_versions(versions: tuple[int, ...]) -> str:
    return ",".join(str(v) for v in versions) if versions else "(none)"


def _require_current_schema(database_path: Path, migrations_root: Path) -> None:
    try:
        expected_versions = expected_migration_versions(migrations_root)
    except OrchestratorError as exc:
        sys.exit(
            f"Runtime migrations directory is invalid ({exc}).\n"
            f"Check {migrations_root} for a malformed, duplicate, or missing migration file."
        )

    try:
        actual_versions = applied_migration_versions(database_path)
    except sqlite3.OperationalError:
        sys.exit(
            f"Database not found or unreadable at {database_path}.\n"
            f"Run the setup command first:\n"
            f"  {_SETUP_COMMAND} --database-path {database_path}"
        )

    if actual_versions != expected_versions:
        sys.exit(
            "Database migration history does not match the expected runtime schema.\n"
            f"Applied: {_format_versions(actual_versions)}\n"
            f"Expected: {_format_versions(expected_versions)}\n"
            "Run the setup command or restore a valid database.\n"
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
