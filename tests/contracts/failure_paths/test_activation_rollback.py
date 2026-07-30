from pathlib import Path

import pytest

from factory.contracts.activation.store import (
    SQLiteActivationReader,
    _SQLiteActivationWriter,
    apply_migrations,
)
from factory.contracts.errors import ContractError
from factory.contracts.models import ErrorCode

pytestmark = pytest.mark.failure_path

MIGRATIONS_ROOT = Path("migrations/contracts")


def test_failed_activation_transaction_preserves_prior_state(tmp_path: Path) -> None:
    db_path = tmp_path / "activation.sqlite3"
    apply_migrations(db_path, MIGRATIONS_ROOT)
    writer = _SQLiteActivationWriter(db_path)
    reader = SQLiteActivationReader(db_path)

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

    with pytest.raises(ContractError) as raised:
        writer.activate_transactionally(
            project_id="PROJ-001",
            contract_id="TASK-001",
            contract_version=-1,  # violates the `contract_version > 0` CHECK constraint
            schema_version="1.0",
            content_hash="b" * 64,
            canonical_json=b"{}",
            validation_report_json="{}",
            impact_report_json="{}",
            policy_decision_json="{}",
            evidence_json="{}",
            expected_generation=1,
            rollback_contract_version=None,
        )
    assert raised.value.code is ErrorCode.ACTIVATION_ROLLED_BACK

    assert reader.get_generation("PROJ-001") == 1
    active = reader.get_active("PROJ-001", "TASK-001")
    assert active is not None
    assert active.contract_version == 1
    assert active.content_hash == "a" * 64


def test_rollback_with_stale_generation_is_rejected_and_preserves_state(tmp_path: Path) -> None:
    db_path = tmp_path / "activation.sqlite3"
    apply_migrations(db_path, MIGRATIONS_ROOT)
    writer = _SQLiteActivationWriter(db_path)
    reader = SQLiteActivationReader(db_path)

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

    with pytest.raises(ContractError) as raised:
        writer.rollback_transactionally(
            project_id="PROJ-001",
            contract_id="TASK-001",
            target_version=1,
            expected_generation=99,
            reason="stale generation probe",
        )
    assert raised.value.code is ErrorCode.ACTIVATION_ROLLED_BACK

    assert reader.get_generation("PROJ-001") == 1
    active = reader.get_active("PROJ-001", "TASK-001")
    assert active is not None
    assert active.contract_version == 1


def test_rollback_to_nonexistent_version_is_rejected_and_preserves_state(tmp_path: Path) -> None:
    db_path = tmp_path / "activation.sqlite3"
    apply_migrations(db_path, MIGRATIONS_ROOT)
    writer = _SQLiteActivationWriter(db_path)
    reader = SQLiteActivationReader(db_path)

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

    with pytest.raises(ContractError) as raised:
        writer.rollback_transactionally(
            project_id="PROJ-001",
            contract_id="TASK-001",
            target_version=99,
            expected_generation=1,
            reason="target never existed",
        )
    assert raised.value.code is ErrorCode.REFERENCE_REJECTED

    assert reader.get_generation("PROJ-001") == 1
    active = reader.get_active("PROJ-001", "TASK-001")
    assert active is not None
    assert active.contract_version == 1
