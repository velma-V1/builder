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
from factory.contracts.models import ContractType, ErrorCode, PolicyOutcome
from factory.contracts.policy.engine import PolicyEngine
from factory.contracts.references.resolver import ReferenceResolver
from factory.contracts.repository.filesystem import ContractFileRepository
from factory.contracts.service import ChangeApplicationService, ContractService
from factory.contracts.validation.paths import PathAuthority
from factory.contracts.validation.schema_registry import SchemaRegistry
from factory.contracts.validation.semantic import SemanticValidator

SCHEMA_ROOT = Path("schemas")
FIXTURES_ROOT = Path("tests/contracts/fixtures/valid")
MIGRATIONS_ROOT = Path("migrations/contracts")

APPROVED_ROUTES = frozenset({"LOCAL_FAST", "LOCAL_SUPERVISOR"})


def _load_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES_ROOT / name).read_text(encoding="utf-8"))


def _write(
    repository: ContractFileRepository, contract_type: ContractType, document: dict[str, Any]
) -> None:
    text = yaml.safe_dump(document, sort_keys=False)
    repository.create_version(
        contract_type, document["project_id"], document["id"], document["version"], text
    )


class _Harness:
    def __init__(self, tmp_path: Path) -> None:
        self.service = ContractService(SchemaRegistry.load(SCHEMA_ROOT))
        self.repository = ContractFileRepository(root=tmp_path / "contracts", service=self.service)
        self.resolver = ReferenceResolver(repository=self.repository)
        self.semantic_validator = SemanticValidator(
            resolver=self.resolver,
            path_authority_factory=lambda root: PathAuthority(project_root=root),
            approved_routes=APPROVED_ROUTES,
        )
        self.impact_analyzer = ImpactAnalyzer()
        self.policy_engine = PolicyEngine()
        self.change_service = ChangeApplicationService(
            repository=self.repository,
            semantic_validator=self.semantic_validator,
            impact_analyzer=self.impact_analyzer,
            policy_engine=self.policy_engine,
        )

        self.db_path = tmp_path / "activation.sqlite3"
        apply_migrations(self.db_path, MIGRATIONS_ROOT)
        self.writer = _SQLiteActivationWriter(self.db_path)
        self.reader = SQLiteActivationReader(self.db_path)
        self.cache = RuntimeContractCache()
        self.activation = ActivationService(writer=self.writer, cache=self.cache)


@pytest.fixture
def harness(tmp_path: Path) -> _Harness:
    return _Harness(tmp_path)


def _seed_full_set(harness: _Harness) -> None:
    _write(harness.repository, ContractType.PROJECT, _load_fixture("project.json"))
    _write(harness.repository, ContractType.REQUIREMENT, _load_fixture("requirement.json"))
    _write(harness.repository, ContractType.OWNERSHIP, _load_fixture("ownership.json"))
    _write(harness.repository, ContractType.PERMISSION, _load_fixture("permission.json"))
    _write(harness.repository, ContractType.EVIDENCE, _load_fixture("evidence.json"))
    _write(harness.repository, ContractType.TASK, _load_fixture("task.json"))


def _activate_initial_versions(harness: _Harness) -> None:
    for contract_type, contract_id in (
        (ContractType.PROJECT, "PROJ-001"),
        (ContractType.REQUIREMENT, "REQ-001"),
        (ContractType.OWNERSHIP, "OWN-001"),
        (ContractType.PERMISSION, "PERM-001"),
        (ContractType.EVIDENCE, "EVID-001"),
        (ContractType.TASK, "TASK-001"),
    ):
        contract = harness.repository.load(contract_type, "PROJ-001", contract_id, 1)
        report = harness.semantic_validator.validate(contract, active_ownership={})
        assert report.valid, (contract_id, report.issues)
        impact = harness.impact_analyzer.compare(contract, contract, linked={})
        policy = harness.policy_engine.decide(
            candidate=contract,
            impact=impact,
            validation=report,
            evidence_passed=True,
            rollback_available=False,
            deletion_classification=None,
        )
        needs_approval = policy.outcome is not PolicyOutcome.ALLOW_WITH_CHECKPOINT
        approval = {"approved_by": "operator"} if needs_approval else None
        harness.activation.activate(
            contract,
            impact=impact,
            policy=policy,
            evidence={"summary": "initial activation"},
            expected_generation=harness.reader.get_generation("PROJ-001"),
            approval_record=approval,
        )


def test_full_section1_lifecycle(harness: _Harness) -> None:
    # 1-2: create, ingest, and validate a full linked contract set.
    _seed_full_set(harness)

    # 3: activate the initial versions automatically.
    _activate_initial_versions(harness)
    assert harness.reader.get_generation("PROJ-001") == 6

    # 4: read the task through the immutable cache.
    cached = harness.cache.get("PROJ-001", "TASK-001", harness.reader)
    assert cached.record.contract_version == 1
    assert cached.document["objective"] == "Implement contract ingestion."

    # 5-6: create a safe Change Contract editing only flexible intent, and activate v2
    # without human approval (a bounded owned edit).
    change_doc = _load_fixture("change.json")
    change_doc["target"] = {"id": "TASK-001", "version": 1}
    change_doc["operations"] = [
        {"op": "replace", "path": "/objective", "value": "Implement contract ingestion, safely."}
    ]
    change_doc["resulting_version"] = 2
    change_path = harness.repository.root.parent / "change.yaml"
    change_path.write_text(yaml.safe_dump(change_doc, sort_keys=False), encoding="utf-8")
    change = harness.service.ingest(change_path)

    result = harness.change_service.apply(
        change,
        target_type=ContractType.TASK,
        active_ownership={},
        evidence_passed=True,
        rollback_available=True,
    )
    assert result.policy.outcome is PolicyOutcome.ALLOW_WITH_CHECKPOINT

    generation_before_v2_activation = harness.reader.get_generation("PROJ-001")
    v2_record = harness.activation.activate(
        result.proposed,
        impact=result.impact,
        policy=result.policy,
        evidence={"summary": "v2 evidence"},
        expected_generation=generation_before_v2_activation,
    )

    # 7: prove generation increments exactly once.
    assert harness.reader.get_generation("PROJ-001") == generation_before_v2_activation + 1
    assert v2_record.contract_version == 2

    # 8: prove version 1 remains immutable and loadable.
    v1 = harness.repository.load(ContractType.TASK, "PROJ-001", "TASK-001", 1)
    assert v1.document["objective"] == "Implement contract ingestion."

    # 9: attempt authority expansion and receive HUMAN_APPROVAL_REQUIRED.
    expansion_doc = _load_fixture("change.json")
    expansion_doc["id"] = "CHG-002"
    expansion_doc["target"] = {"id": "TASK-001", "version": 2}
    expansion_doc["operations"] = [{"op": "replace", "path": "/autonomy_level", "value": 100}]
    expansion_doc["resulting_version"] = 3
    expansion_path = harness.repository.root.parent / "change_expansion.yaml"
    expansion_path.write_text(yaml.safe_dump(expansion_doc, sort_keys=False), encoding="utf-8")
    expansion_change = harness.service.ingest(expansion_path)

    expansion_result = harness.change_service.apply(
        expansion_change,
        target_type=ContractType.TASK,
        active_ownership={},
        evidence_passed=True,
        rollback_available=True,
    )
    assert expansion_result.policy.outcome is PolicyOutcome.HUMAN_APPROVAL_REQUIRED

    generation_before_v3 = harness.reader.get_generation("PROJ-001")
    with pytest.raises(ContractError) as raised:
        harness.activation.activate(
            expansion_result.proposed,
            impact=expansion_result.impact,
            policy=expansion_result.policy,
            evidence={},
            expected_generation=generation_before_v3,
        )
    assert raised.value.code is ErrorCode.APPROVAL_REQUIRED
    assert harness.reader.get_generation("PROJ-001") == generation_before_v3

    # 10: attempt cross-project injection and receive a security denial at ingestion/validation.
    injection_doc = _load_fixture("task.json")
    injection_doc["id"] = "TASK-INJECT"
    injection_doc["parent_requirements"] = [{"id": "REQ-001", "version": 1}]
    injection_doc["ownership_contract"] = {"id": "OWN-001", "version": 1}
    injection_doc["project_id"] = "PROJ-999"  # a different project than its own repository path
    injection_path = harness.repository.root.parent / "injection.yaml"
    injection_path.write_text(yaml.safe_dump(injection_doc, sort_keys=False), encoding="utf-8")
    injection_contract = harness.service.ingest(injection_path)
    with pytest.raises(ContractError):
        harness.resolver.resolve(
            {"id": "REQ-001", "version": 1}, ContractType.REQUIREMENT, injection_contract.project_id
        )

    # 11: force an activation failure (generation conflict) and prove v2 remains active.
    active_v2 = harness.repository.load(ContractType.TASK, "PROJ-001", "TASK-001", 2)
    with pytest.raises(ContractError):
        harness.activation.activate(
            active_v2,
            impact=result.impact,
            policy=result.policy,
            evidence={},
            expected_generation=999,  # deliberately wrong
        )
    active_after_failure = harness.reader.get_active("PROJ-001", "TASK-001")
    assert active_after_failure is not None
    assert active_after_failure.contract_version == 2

    # 12: rollback to version 1 and prove a new generation is assigned.
    generation_before_rollback = harness.reader.get_generation("PROJ-001")
    rollback_record = harness.activation.rollback(
        project_id="PROJ-001",
        contract_id="TASK-001",
        target_version=1,
        expected_generation=generation_before_rollback,
        reason="v2 caused a regression",
    )
    assert rollback_record.contract_version == 1
    assert rollback_record.generation == generation_before_rollback + 1
    final_active = harness.reader.get_active("PROJ-001", "TASK-001")
    assert final_active is not None
    assert final_active.contract_version == 1
