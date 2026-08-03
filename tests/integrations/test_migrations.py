from pathlib import Path

import pytest

from factory.integrations.migrations import (
    IntegrationMigrationError,
    applied_versions,
    apply_integration_migrations,
    require_current_schema,
)

ROOT = Path(__file__).resolve().parents[2] / "migrations" / "integrations"


def test_integration_migration_is_pinned_idempotent_and_current(tmp_path: Path) -> None:
    database = tmp_path / "integrations.db"
    apply_integration_migrations(database, ROOT)
    apply_integration_migrations(database, ROOT)
    assert applied_versions(database) == (1,)
    require_current_schema(database, ROOT)


def test_tampered_or_unknown_schema_fails_closed(tmp_path: Path) -> None:
    database = tmp_path / "integrations.db"
    root = tmp_path / "migrations"
    root.mkdir()
    source = ROOT / "0001_managed_integrations.sql"
    (root / source.name).write_bytes(source.read_bytes() + b"\n-- tampered\n")
    with pytest.raises(IntegrationMigrationError, match="integrity"):
        apply_integration_migrations(database, root)

    apply_integration_migrations(database, ROOT)
    import sqlite3

    with sqlite3.connect(database) as connection:
        connection.execute("INSERT INTO schema_migrations VALUES (99, 'now')")
    with pytest.raises(IntegrationMigrationError, match="unknown applied"):
        apply_integration_migrations(database, ROOT)
