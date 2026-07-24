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
from factory.contracts.models import ContractType, ErrorCode
from factory.contracts.policy.engine import PolicyEngine
from factory.contracts.references.resolver import ReferenceResolver
from factory.contracts.repository.filesystem import ContractFileRepository
from factory.contracts.service import ChangeApplicationService, ContractService
from factory.contracts.validation.paths import PathAuthority
from factory.contracts.validation.schema_registry import SchemaRegistry
from factory.contracts.validation.semantic import SemanticValidator

pytestmark = pytest.mark.failure_path

SCHEMA_ROOT = Path("schemas")
FIXTURES_ROOT = Path("tests/contracts/fixtures/valid")
MIGRATIONS_ROOT = Path("migrations/contracts")
APPROVED_ROUTES = frozenset({"LOCAL_FAST", "LOCAL_SUPERVISOR"})


def _load_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES_ROOT / name).read_text(encoding="utf-8"))


@pytest.fixture
def repository(tmp_path: Path) -> ContractFileRepository:
    service = ContractService(SchemaRegistry.load(SCHEMA_ROOT))
    return ContractFileRepository(root=tmp_path, service=service)


@pytest.fixture
def change_service(repository: ContractFileRepository) -> ChangeApplicationService:
    resolver = ReferenceResolver(repository=repository)
    validator = SemanticValidator(
        resolver=resolver,
        path_authority_factory=lambda root: PathAuthority(project_root=root),
        approved_routes=APPROVED_ROUTES,
    )
    return ChangeApplicationService(
        repository=repository,
        semantic_validator=validator,
        impact_analyzer=ImpactAnalyzer(),
        policy_engine=PolicyEngine(),
    )


def _write(
    repository: ContractFileRepository, contract_type: ContractType, document: dict[str, Any]
) -> None:
    text = yaml.safe_dump(document, sort_keys=False)
    repository.create_version(
        contract_type, document["project_id"], document["id"], document["version"], text
    )


def _seed_task(repository: ContractFileRepository) -> None:
    _write(repository, ContractType.PROJECT, _load_fixture("project.json"))
    _write(repository, ContractType.REQUIREMENT, _load_fixture("requirement.json"))
    _write(repository, ContractType.OWNERSHIP, _load_fixture("ownership.json"))
    _write(repository, ContractType.PERMISSION, _load_fixture("permission.json"))
    _write(repository, ContractType.EVIDENCE, _load_fixture("evidence.json"))
    _write(repository, ContractType.TASK, _load_fixture("task.json"))


def test_change_application_failure_leaves_no_new_version_and_active_version_intact(
    repository: ContractFileRepository, change_service: ChangeApplicationService
) -> None:
    _seed_task(repository)

    change_doc = _load_fixture("change.json")
    change_doc["target"] = {"id": "TASK-001", "version": 1}
    change_doc["operations"] = [{"op": "remove", "path": "/objective"}]  # required field
    change_doc["resulting_version"] = 2
    path = repository.root.parent / "change.yaml"
    path.write_text(yaml.safe_dump(change_doc, sort_keys=False), encoding="utf-8")
    change = repository.service.ingest(path)

    with pytest.raises(ContractError) as raised:
        change_service.apply(
            change,
            target_type=ContractType.TASK,
            active_ownership={},
            evidence_passed=True,
            rollback_available=True,
        )
    assert raised.value.code is ErrorCode.SCHEMA_REJECTED

    assert repository.list_versions(ContractType.TASK, "PROJ-001", "TASK-001") == (1,)
    v1 = repository.load(ContractType.TASK, "PROJ-001", "TASK-001", 1)
    assert v1.document["objective"] == "Implement contract ingestion."


def test_activation_failure_leaves_previously_active_version_and_cache_untouched(
    repository: ContractFileRepository,
) -> None:
    _seed_task(repository)
    db_path = repository.root.parent / "activation.sqlite3"
    apply_migrations(db_path, MIGRATIONS_ROOT)
    writer = _SQLiteActivationWriter(db_path)
    reader = SQLiteActivationReader(db_path)
    cache = RuntimeContractCache()
    activation = ActivationService(writer=writer, cache=cache)

    task_v1 = repository.load(ContractType.TASK, "PROJ-001", "TASK-001", 1)
    impact = ImpactAnalyzer().compare(task_v1, task_v1, linked={})
    policy = PolicyEngine().decide(
        candidate=task_v1,
        impact=impact,
        validation=task_v1.validation,
        evidence_passed=True,
        rollback_available=True,
        deletion_classification=None,
    )
    activation.activate(task_v1, impact=impact, policy=policy, evidence={}, expected_generation=0)
    cached_before = cache.get("PROJ-001", "TASK-001", reader)

    # Attempt a second activation with a deliberately wrong expected_generation.
    with pytest.raises(ContractError) as raised:
        activation.activate(
            task_v1, impact=impact, policy=policy, evidence={}, expected_generation=999
        )
    assert raised.value.code is ErrorCode.ACTIVATION_ROLLED_BACK

    assert reader.get_generation("PROJ-001") == 1
    active = reader.get_active("PROJ-001", "TASK-001")
    assert active is not None
    assert active.contract_version == 1

    cached_after = cache.get("PROJ-001", "TASK-001", reader)
    assert cached_after.record.content_hash == cached_before.record.content_hash
