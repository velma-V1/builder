import sqlite3
from pathlib import Path

import pytest

from factory.contracts.activation.store import (
    SQLiteActivationReader,
    _SQLiteActivationWriter,
    apply_migrations,
)
from factory.contracts.errors import ContractError
from factory.contracts.models import ErrorCode

MIGRATIONS_ROOT = Path("migrations/contracts")


def test_apply_migrations_creates_expected_schema(tmp_path: Path) -> None:
    db_path = tmp_path / "activation.sqlite3"
    apply_migrations(db_path, MIGRATIONS_ROOT)

    connection = sqlite3.connect(str(db_path))
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
    finally:
        connection.close()

    assert {
        "schema_migrations",
        "project_generations",
        "contract_activations",
        "active_contracts",
        "activation_events",
    } <= tables


def test_apply_migrations_is_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "activation.sqlite3"
    apply_migrations(db_path, MIGRATIONS_ROOT)
    apply_migrations(db_path, MIGRATIONS_ROOT)  # must not raise or duplicate the migration

    connection = sqlite3.connect(str(db_path))
    try:
        count = connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]
    finally:
        connection.close()
    assert count == 1


def test_apply_migrations_rejects_tampered_migration_content(tmp_path: Path) -> None:
    tampered_root = tmp_path / "migrations"
    tampered_root.mkdir()
    original = (MIGRATIONS_ROOT / "0001_activation_store.sql").read_text(encoding="utf-8")
    tampered = original + "\n-- an attacker appended this comment\n"
    (tampered_root / "0001_activation_store.sql").write_text(tampered, encoding="utf-8")

    db_path = tmp_path / "activation.sqlite3"
    with pytest.raises(ContractError) as raised:
        apply_migrations(db_path, tampered_root)
    assert raised.value.code is ErrorCode.SECURITY_DENIED


def test_activation_events_are_append_only(tmp_path: Path) -> None:
    db_path = tmp_path / "activation.sqlite3"
    apply_migrations(db_path, MIGRATIONS_ROOT)
    writer = _SQLiteActivationWriter(db_path)
    writer.activate_transactionally(
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

    connection = sqlite3.connect(str(db_path))
    try:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("UPDATE activation_events SET event_type = 'TAMPERED'")
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("DELETE FROM activation_events")
    finally:
        connection.close()


def test_reader_reflects_writer_state(tmp_path: Path) -> None:
    db_path = tmp_path / "activation.sqlite3"
    apply_migrations(db_path, MIGRATIONS_ROOT)
    reader = SQLiteActivationReader(db_path)
    writer = _SQLiteActivationWriter(db_path)

    assert reader.get_generation("PROJ-001") == 0
    assert reader.get_active("PROJ-001", "TASK-001") is None

    writer.activate_transactionally(
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

    assert reader.get_generation("PROJ-001") == 1
    record = reader.get_active("PROJ-001", "TASK-001")
    assert record is not None
    assert record.contract_version == 1
    assert record.generation == 1


def test_activation_rejects_generation_conflict(tmp_path: Path) -> None:
    db_path = tmp_path / "activation.sqlite3"
    apply_migrations(db_path, MIGRATIONS_ROOT)
    writer = _SQLiteActivationWriter(db_path)

    with pytest.raises(ContractError) as raised:
        writer.activate_transactionally(
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
            expected_generation=5,
            rollback_contract_version=None,
        )
    assert raised.value.code is ErrorCode.ACTIVATION_ROLLED_BACK
