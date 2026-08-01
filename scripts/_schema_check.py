"""Shared read-only schema-currentness check (Phase 3A) for local-dev API entrypoints.

Used by both ``scripts/run_api.py`` and ``scripts/run_orchestrator.py`` so the two never
duplicate (and risk diverging on) this logic. A maximum-version-only check cannot detect a gap
(e.g. ``{1, 2, 4}`` has the same maximum as ``{1, 2, 3, 4}``), which is exactly why this compares
the full applied/expected version sets rather than a count or a maximum.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

from factory.orchestrator.errors import OrchestratorError
from factory.orchestrator.store.runtime_state import (
    applied_migration_versions,
    expected_migration_versions,
)


def _format_versions(versions: tuple[int, ...]) -> str:
    return ",".join(str(v) for v in versions) if versions else "(none)"


def require_current_schema_or_exit(
    database_path: Path, migrations_root: Path, setup_command: str
) -> None:
    """Exit with a clear, bounded message unless the database's applied migration set exactly
    equals the expected set on disk. Read-only: never applies or repairs anything itself."""
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
            f"  {setup_command} --database-path {database_path}"
        )

    if actual_versions != expected_versions:
        sys.exit(
            "Database migration history does not match the expected runtime schema.\n"
            f"Applied: {_format_versions(actual_versions)}\n"
            f"Expected: {_format_versions(expected_versions)}\n"
            "Run the setup command or restore a valid database.\n"
            f"  {setup_command} --database-path {database_path}"
        )
