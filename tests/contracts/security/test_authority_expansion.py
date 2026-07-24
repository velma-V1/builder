import json
from pathlib import Path
from typing import Any

import pytest
import yaml

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

pytestmark = pytest.mark.security

SCHEMA_ROOT = Path("schemas")
FIXTURES_ROOT = Path("tests/contracts/fixtures/valid")
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


def _seed(repository: ContractFileRepository) -> None:
    _write(repository, ContractType.PROJECT, _load_fixture("project.json"))
    _write(repository, ContractType.REQUIREMENT, _load_fixture("requirement.json"))
    _write(repository, ContractType.OWNERSHIP, _load_fixture("ownership.json"))
    _write(repository, ContractType.PERMISSION, _load_fixture("permission.json"))
    _write(repository, ContractType.EVIDENCE, _load_fixture("evidence.json"))
    _write(repository, ContractType.TASK, _load_fixture("task.json"))


def _ingest_change(repository: ContractFileRepository, operations: list[dict[str, Any]]):
    document = _load_fixture("change.json")
    document["target"] = {"id": "TASK-001", "version": 1}
    document["operations"] = operations
    document["resulting_version"] = 2
    path = repository.root.parent / "change.yaml"
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return repository.service.ingest(path)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        ("/autonomy_level", 100),
        ("/permitted_routes", ["LOCAL_FAST", "LANE_1_WORKER"]),
    ],
)
def test_authority_expanding_change_requires_human_approval(
    repository: ContractFileRepository,
    change_service: ChangeApplicationService,
    path: str,
    value: object,
) -> None:
    _seed(repository)
    change = _ingest_change(repository, [{"op": "replace", "path": path, "value": value}])

    result = change_service.apply(
        change,
        target_type=ContractType.TASK,
        active_ownership={},
        evidence_passed=True,
        rollback_available=True,
    )
    assert result.policy.outcome is PolicyOutcome.HUMAN_APPROVAL_REQUIRED
    assert result.impact.authority_expanded


def test_ownership_authority_expansion_via_new_allowed_path_requires_approval(
    repository: ContractFileRepository, change_service: ChangeApplicationService
) -> None:
    _seed(repository)
    document = _load_fixture("change.json")
    document["target"] = {"id": "OWN-001", "version": 1}
    document["operations"] = [
        {
            "op": "replace",
            "path": "/allowed_paths",
            "value": ["src/factory/contracts/**", "docs/**"],
        }
    ]
    document["resulting_version"] = 2
    path = repository.root.parent / "ownership_change.yaml"
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    change = repository.service.ingest(path)

    result = change_service.apply(
        change,
        target_type=ContractType.OWNERSHIP,
        active_ownership={},
        evidence_passed=True,
        rollback_available=True,
    )
    assert result.policy.outcome is PolicyOutcome.HUMAN_APPROVAL_REQUIRED
    assert result.impact.authority_expanded


def test_authority_expansion_cannot_be_activated_without_an_approval_record(
    repository: ContractFileRepository, change_service: ChangeApplicationService
) -> None:
    from factory.contracts.activation.service import ActivationService
    from factory.contracts.activation.store import _SQLiteActivationWriter, apply_migrations
    from factory.contracts.cache.runtime_cache import RuntimeContractCache

    _seed(repository)
    operations = [{"op": "replace", "path": "/autonomy_level", "value": 100}]
    change = _ingest_change(repository, operations)
    result = change_service.apply(
        change,
        target_type=ContractType.TASK,
        active_ownership={},
        evidence_passed=True,
        rollback_available=True,
    )
    assert result.policy.outcome is PolicyOutcome.HUMAN_APPROVAL_REQUIRED

    db_path = repository.root.parent / "activation.sqlite3"
    apply_migrations(db_path, Path("migrations/contracts"))
    activation = ActivationService(
        writer=_SQLiteActivationWriter(db_path), cache=RuntimeContractCache()
    )
    with pytest.raises(ContractError) as raised:
        activation.activate(
            result.proposed,
            impact=result.impact,
            policy=result.policy,
            evidence={},
            expected_generation=0,
        )
    assert raised.value.code is ErrorCode.APPROVAL_REQUIRED
