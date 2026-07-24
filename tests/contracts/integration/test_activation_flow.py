import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from factory.contracts.activation.service import ActivationService
from factory.contracts.activation.store import (
    SQLiteActivationReader,
    _SQLiteActivationWriter,
    apply_migrations,
)
from factory.contracts.cache.runtime_cache import RuntimeContractCache
from factory.contracts.errors import ContractError
from factory.contracts.impact.analyzer import ImpactAnalyzer
from factory.contracts.models import CanonicalContract, ErrorCode, PolicyDecision, PolicyOutcome
from factory.contracts.service import ContractService
from factory.contracts.validation.schema_registry import SchemaRegistry

SCHEMA_ROOT = Path("schemas")
FIXTURES_ROOT = Path("tests/contracts/fixtures/valid")
MIGRATIONS_ROOT = Path("migrations/contracts")


def _load_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES_ROOT / name).read_text(encoding="utf-8"))


def _ingest(
    service: ContractService, tmp_path: Path, filename: str, document: dict[str, Any]
) -> CanonicalContract:
    path = tmp_path / filename
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return service.ingest(path)


@pytest.fixture
def service() -> ContractService:
    return ContractService(SchemaRegistry.load(SCHEMA_ROOT))


@pytest.fixture
def activation_service(tmp_path: Path) -> tuple[ActivationService, Path]:
    db_path = tmp_path / "activation.sqlite3"
    apply_migrations(db_path, MIGRATIONS_ROOT)
    writer = _SQLiteActivationWriter(db_path)
    cache = RuntimeContractCache()
    return ActivationService(writer=writer, cache=cache), db_path


def _fresh_impact(contract: CanonicalContract):
    return ImpactAnalyzer().compare(previous=contract, proposed=contract, linked={})


def _allow_decision() -> PolicyDecision:
    return PolicyDecision(
        outcome=PolicyOutcome.ALLOW_WITH_CHECKPOINT,
        reasons=("bounded owned edit",),
        required_approvals=(),
        required_tests=(),
    )


def _approval_decision() -> PolicyDecision:
    return PolicyDecision(
        outcome=PolicyOutcome.HUMAN_APPROVAL_REQUIRED,
        reasons=("expands authority",),
        required_approvals=("authority_expansion_review",),
        required_tests=(),
    )


def _deny_decision() -> PolicyDecision:
    return PolicyDecision(
        outcome=PolicyOutcome.DENY_SECURITY_VIOLATION,
        reasons=("path traversal detected",),
        required_approvals=(),
        required_tests=(),
    )


def test_activate_bounded_edit_without_approval_succeeds_and_publishes_cache(
    service: ContractService, activation_service: tuple[ActivationService, Path], tmp_path: Path
) -> None:
    activation, db_path = activation_service
    contract = _ingest(service, tmp_path, "task.yaml", _load_fixture("task.json"))

    record = activation.activate(
        contract,
        impact=_fresh_impact(contract),
        policy=_allow_decision(),
        evidence={"summary": "all tests passed"},
        expected_generation=0,
    )

    assert record.generation == 1
    reader = SQLiteActivationReader(db_path)
    cached = activation.cache.get(contract.project_id, contract.contract_id, reader)
    assert cached.record.contract_version == contract.version


def test_activate_requiring_approval_without_record_is_rejected(
    service: ContractService, activation_service: tuple[ActivationService, Path], tmp_path: Path
) -> None:
    activation, _ = activation_service
    contract = _ingest(service, tmp_path, "task.yaml", _load_fixture("task.json"))

    with pytest.raises(ContractError) as raised:
        activation.activate(
            contract,
            impact=_fresh_impact(contract),
            policy=_approval_decision(),
            evidence={},
            expected_generation=0,
        )
    assert raised.value.code is ErrorCode.APPROVAL_REQUIRED


def test_activate_requiring_approval_with_record_succeeds(
    service: ContractService, activation_service: tuple[ActivationService, Path], tmp_path: Path
) -> None:
    activation, _ = activation_service
    contract = _ingest(service, tmp_path, "task.yaml", _load_fixture("task.json"))

    record = activation.activate(
        contract,
        impact=_fresh_impact(contract),
        policy=_approval_decision(),
        evidence={},
        expected_generation=0,
        approval_record={"approved_by": "operator"},
    )
    assert record.generation == 1


def test_activate_denied_by_security_policy_is_rejected_even_with_approval(
    service: ContractService, activation_service: tuple[ActivationService, Path], tmp_path: Path
) -> None:
    activation, _ = activation_service
    contract = _ingest(service, tmp_path, "task.yaml", _load_fixture("task.json"))

    with pytest.raises(ContractError) as raised:
        activation.activate(
            contract,
            impact=_fresh_impact(contract),
            policy=_deny_decision(),
            evidence={},
            expected_generation=0,
            approval_record={"approved_by": "operator"},
        )
    assert raised.value.code is ErrorCode.SECURITY_DENIED


def test_rollback_reverts_active_version_and_quarantines_cache(
    service: ContractService, activation_service: tuple[ActivationService, Path], tmp_path: Path
) -> None:
    activation, db_path = activation_service
    v1 = _ingest(service, tmp_path, "task_v1.yaml", _load_fixture("task.json"))
    activation.activate(
        v1, impact=_fresh_impact(v1), policy=_allow_decision(), evidence={}, expected_generation=0
    )

    v2_doc = _load_fixture("task.json")
    v2_doc["version"] = 2
    v2 = _ingest(service, tmp_path, "task_v2.yaml", v2_doc)
    activation.activate(
        v2, impact=_fresh_impact(v2), policy=_allow_decision(), evidence={}, expected_generation=1
    )

    reader = SQLiteActivationReader(db_path)
    active = reader.get_active(v2.project_id, v2.contract_id)
    assert active is not None
    assert active.contract_version == 2

    record = activation.rollback(
        project_id=v1.project_id,
        contract_id=v1.contract_id,
        target_version=1,
        expected_generation=2,
        reason="v2 caused a regression",
    )
    assert record.contract_version == 1
    assert record.generation == 3

    with pytest.raises(ContractError) as raised:
        activation.cache.get(v1.project_id, v1.contract_id, reader)
    assert raised.value.code is ErrorCode.CACHE_QUARANTINED
