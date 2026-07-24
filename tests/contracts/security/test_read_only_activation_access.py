import sqlite3
from pathlib import Path

import pytest

from factory.contracts.activation.store import (
    SQLiteActivationReader,
    _connect_readonly,
    _SQLiteActivationWriter,
    apply_migrations,
)

pytestmark = pytest.mark.security

MIGRATIONS_ROOT = Path("migrations/contracts")


@pytest.fixture
def seeded_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "activation.sqlite3"
    apply_migrations(db_path, MIGRATIONS_ROOT)
    _SQLiteActivationWriter(db_path).activate_transactionally(
        project_id="PROJ-001",
        contract_id="TASK-001",
        contract_version=1,
        schema_version="1.0",
        content_hash="a" * 64,
        canonical_json=b"{}",
        validation_report_json="{}",
        impact_report_json="{}",
        policy_decision_json="{}",
        evidence_json="{}",
        expected_generation=0,
        rollback_contract_version=None,
    )
    return db_path


def test_reader_can_select(seeded_db: Path) -> None:
    connection = _connect_readonly(seeded_db)
    try:
        row = connection.execute("SELECT COUNT(*) FROM active_contracts").fetchone()
        assert row[0] == 1
    finally:
        connection.close()


@pytest.mark.parametrize(
    "statement",
    [
        "INSERT INTO project_generations (project_id, last_generation) VALUES ('X', 0)",
        "UPDATE project_generations SET last_generation = 99",
        "DELETE FROM active_contracts",
        "CREATE TABLE evil (id INTEGER)",
        "DROP TABLE active_contracts",
        "ALTER TABLE active_contracts ADD COLUMN evil TEXT",
    ],
)
def test_reader_denies_mutation_statements(seeded_db: Path, statement: str) -> None:
    connection = _connect_readonly(seeded_db)
    try:
        with pytest.raises(sqlite3.DatabaseError):
            connection.execute(statement)
    finally:
        connection.close()


def test_reader_denies_attach_and_detach(seeded_db: Path, tmp_path: Path) -> None:
    other_db = tmp_path / "other.sqlite3"
    sqlite3.connect(str(other_db)).close()

    connection = _connect_readonly(seeded_db)
    try:
        with pytest.raises(sqlite3.DatabaseError):
            connection.execute(f"ATTACH DATABASE '{other_db}' AS other")
    finally:
        connection.close()


def test_reader_denies_writable_pragma_but_allows_readable_pragma(seeded_db: Path) -> None:
    connection = _connect_readonly(seeded_db)
    try:
        with pytest.raises(sqlite3.DatabaseError):
            connection.execute("PRAGMA journal_mode = DELETE")
        # A read-only pragma invocation (no value being set) is not a write and must succeed.
        connection.execute("PRAGMA table_info(active_contracts)").fetchall()
    finally:
        connection.close()


def test_reader_open_mode_itself_is_read_only_at_the_os_level(seeded_db: Path) -> None:
    # Even without the authorizer, `mode=ro` should make the underlying file handle read-only.
    connection = sqlite3.connect(f"file:{seeded_db}?mode=ro", uri=True)
    try:
        with pytest.raises(sqlite3.OperationalError):
            connection.execute(
                "INSERT INTO project_generations (project_id, last_generation) VALUES ('Y', 0)"
            )
            connection.commit()
    finally:
        connection.close()


def test_public_reader_api_only_ever_issues_reads(seeded_db: Path) -> None:
    reader = SQLiteActivationReader(seeded_db)
    assert reader.get_generation("PROJ-001") == 1
    active = reader.get_active("PROJ-001", "TASK-001")
    assert active is not None and active.contract_version == 1
