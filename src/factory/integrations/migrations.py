"""Pinned, transactional schema management for managed-integration state."""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

from factory.contracts.activation.store import (
    _MIGRATION_FILENAME,
    _apply_single_migration,
    _table_exists,
)

_HASHES = {
    "0001_managed_integrations.sql": (
        "180af8e864bfed8073dd8357f1b23ab61600f6cc003643d883a116a57742ac32"
    )
}


class IntegrationMigrationError(RuntimeError):
    pass


def expected_versions(migrations_root: Path) -> tuple[int, ...]:
    versions: list[int] = []
    for path in sorted(migrations_root.glob("*.sql")):
        match = _MIGRATION_FILENAME.match(path.name)
        if match is None or path.name not in _HASHES:
            raise IntegrationMigrationError(f"unknown integration migration: {path.name}")
        versions.append(int(match.group(1)))
    if not versions or len(versions) != len(set(versions)):
        raise IntegrationMigrationError("integration migration set is missing or duplicated")
    return tuple(versions)


def applied_versions(database_path: Path) -> tuple[int, ...]:
    if not database_path.exists():
        return ()
    with sqlite3.connect(database_path) as connection:
        if not _table_exists(connection, "schema_migrations"):
            return ()
        rows = connection.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall()
    return tuple(int(row[0]) for row in rows)


def apply_integration_migrations(database_path: Path, migrations_root: Path) -> None:
    paths = sorted(migrations_root.glob("*.sql"))
    expected = expected_versions(migrations_root)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database_path) as connection:
        applied: set[int] = set()
        if _table_exists(connection, "schema_migrations"):
            applied = {
                int(row[0]) for row in connection.execute("SELECT version FROM schema_migrations")
            }
        unknown = applied - set(expected)
        if unknown:
            raise IntegrationMigrationError(
                f"unknown applied integration schema: {sorted(unknown)}"
            )
        for path in paths:
            match = _MIGRATION_FILENAME.match(path.name)
            assert match is not None
            version = int(match.group(1))
            content = path.read_bytes()
            if hashlib.sha256(content).hexdigest() != _HASHES[path.name]:
                raise IntegrationMigrationError(
                    f"integration migration integrity failed: {path.name}"
                )
            if version in applied:
                continue
            try:
                _apply_single_migration(connection, content)
                connection.execute(
                    "INSERT INTO schema_migrations(version, applied_at) "
                    "VALUES (?, datetime('now'))",
                    (version,),
                )
                connection.commit()
            except sqlite3.Error as exc:
                connection.rollback()
                raise IntegrationMigrationError(
                    f"integration migration failed: {path.name}: {exc}"
                ) from exc


def require_current_schema(database_path: Path, migrations_root: Path) -> None:
    expected = expected_versions(migrations_root)
    actual = applied_versions(database_path)
    if actual != expected:
        raise IntegrationMigrationError(
            f"integration schema mismatch: expected {expected}, applied {actual}"
        )


__all__ = [
    "IntegrationMigrationError",
    "applied_versions",
    "apply_integration_migrations",
    "expected_versions",
    "require_current_schema",
]
