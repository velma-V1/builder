"""Explicit schema setup for the read-only task-snapshot API (Phase 2B, CMP-API).

Applies pending runtime migrations to the Orchestrator's runtime-state database. This is
the only script in the Phase 2B API path that opens a writable connection to the runtime
database — ``scripts/run_api.py`` never does (see its docstring). Reuses the exact same
idempotent, SHA-256-pinned, fail-closed migration mechanism as the rest of the Orchestrator
(``apply_migrations``); this is not a second migration system.

Usage:
    uv run python scripts/setup_api_database.py --database-path runtime.db
"""

from __future__ import annotations

import argparse
from pathlib import Path

from factory.orchestrator.store.runtime_state import apply_migrations

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_MIGRATIONS_ROOT = _REPO_ROOT / "migrations" / "runtime"
_DEFAULT_DATABASE_PATH = _REPO_ROOT / "runtime.db"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-path", type=Path, default=_DEFAULT_DATABASE_PATH)
    parser.add_argument("--migrations-root", type=Path, default=_DEFAULT_MIGRATIONS_ROOT)
    args = parser.parse_args()

    apply_migrations(args.database_path, args.migrations_root)
    print(f"Schema applied at {args.database_path}")


if __name__ == "__main__":
    main()
