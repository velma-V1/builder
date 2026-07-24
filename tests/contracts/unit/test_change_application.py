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
def resolver(repository: ContractFileRepository) -> ReferenceResolver:
    return ReferenceResolver(repository=repository)


@pytest.fixture
def change_service(
    repository: ContractFileRepository, resolver: ReferenceResolver
) -> ChangeApplicationService:
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


def _seed_full_set(repository: ContractFileRepository) -> None:
    _write(repository, ContractType.PROJECT, _load_fixture("project.json"))
    _write(repository, ContractType.REQUIREMENT, _load_fixture("requirement.json"))
    _write(repository, ContractType.OWNERSHIP, _load_fixture("ownership.json"))
    _write(repository, ContractType.PERMISSION, _load_fixture("permission.json"))
    _write(repository, ContractType.EVIDENCE, _load_fixture("evidence.json"))
    _write(repository, ContractType.TASK, _load_fixture("task.json"))


def _change_document(
    *, operations: list[dict[str, Any]], resulting_version: int = 2
) -> dict[str, Any]:
    document = _load_fixture("change.json")
    document["target"] = {"id": "TASK-001", "version": 1}
    document["operations"] = operations
    document["resulting_version"] = resulting_version
    return document


def _ingest_change(repository: ContractFileRepository, document: dict[str, Any]):
    service = repository.service
    path = Path(repository.root) / "change.yaml"
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return service.ingest(path)


def test_apply_bounded_flexible_edit_allows_with_checkpoint(
    repository: ContractFileRepository, change_service: ChangeApplicationService
) -> None:
    _seed_full_set(repository)
    change_doc = _change_document(
        operations=[{"op": "replace", "path": "/objective", "value": "Implement it more safely."}]
    )
    change = _ingest_change(repository, change_doc)

    result = change_service.apply(
        change,
        target_type=ContractType.TASK,
        active_ownership={},
        evidence_passed=True,
        rollback_available=True,
    )

    assert result.policy.outcome is PolicyOutcome.ALLOW_WITH_CHECKPOINT
    assert result.proposed.version == 2
    assert result.proposed.document["objective"] == "Implement it more safely."
    assert repository.list_versions(ContractType.TASK, "PROJ-001", "TASK-001") == (1, 2)


def test_apply_rejects_resulting_version_mismatch(
    repository: ContractFileRepository, change_service: ChangeApplicationService
) -> None:
    _seed_full_set(repository)
    change_doc = _change_document(
        operations=[{"op": "replace", "path": "/objective", "value": "x"}], resulting_version=5
    )
    change = _ingest_change(repository, change_doc)

    with pytest.raises(ContractError) as raised:
        change_service.apply(
            change,
            target_type=ContractType.TASK,
            active_ownership={},
            evidence_passed=True,
            rollback_available=True,
        )
    assert raised.value.code is ErrorCode.SEMANTIC_REJECTED


def test_apply_rejects_modification_of_protected_envelope_field(
    repository: ContractFileRepository, change_service: ChangeApplicationService
) -> None:
    _seed_full_set(repository)
    change_doc = _change_document(
        operations=[{"op": "replace", "path": "/id", "value": "TASK-999"}]
    )
    change = _ingest_change(repository, change_doc)

    with pytest.raises(ContractError) as raised:
        change_service.apply(
            change,
            target_type=ContractType.TASK,
            active_ownership={},
            evidence_passed=True,
            rollback_available=True,
        )
    assert raised.value.code is ErrorCode.SEMANTIC_REJECTED
    assert "protected envelope field" in raised.value.message


def test_apply_rejects_removal_of_required_field(
    repository: ContractFileRepository, change_service: ChangeApplicationService
) -> None:
    _seed_full_set(repository)
    change_doc = _change_document(operations=[{"op": "remove", "path": "/objective"}])
    change = _ingest_change(repository, change_doc)

    with pytest.raises(ContractError) as raised:
        change_service.apply(
            change,
            target_type=ContractType.TASK,
            active_ownership={},
            evidence_passed=True,
            rollback_available=True,
        )
    assert raised.value.code is ErrorCode.SCHEMA_REJECTED


def test_apply_authority_expansion_requires_human_approval_but_still_writes(
    repository: ContractFileRepository, change_service: ChangeApplicationService
) -> None:
    _seed_full_set(repository)
    change_doc = _change_document(
        operations=[{"op": "replace", "path": "/autonomy_level", "value": 100}]
    )
    change = _ingest_change(repository, change_doc)

    result = change_service.apply(
        change,
        target_type=ContractType.TASK,
        active_ownership={},
        evidence_passed=True,
        rollback_available=True,
    )
    assert result.policy.outcome is PolicyOutcome.HUMAN_APPROVAL_REQUIRED
    assert result.impact.authority_expanded
    assert repository.list_versions(ContractType.TASK, "PROJ-001", "TASK-001") == (1, 2)


def test_apply_never_overwrites_an_existing_version(
    repository: ContractFileRepository, change_service: ChangeApplicationService
) -> None:
    _seed_full_set(repository)
    change_doc = _change_document(
        operations=[{"op": "replace", "path": "/objective", "value": "first revision"}]
    )
    change = _ingest_change(repository, change_doc)
    change_service.apply(
        change,
        target_type=ContractType.TASK,
        active_ownership={},
        evidence_passed=True,
        rollback_available=True,
    )

    duplicate_change_doc = _change_document(
        operations=[{"op": "replace", "path": "/objective", "value": "second attempt at v2"}]
    )
    duplicate_change = _ingest_change(repository, duplicate_change_doc)
    with pytest.raises(ContractError) as raised:
        change_service.apply(
            duplicate_change,
            target_type=ContractType.TASK,
            active_ownership={},
            evidence_passed=True,
            rollback_available=True,
        )
    assert raised.value.code is ErrorCode.REFERENCE_REJECTED

    original_v1 = repository.load(ContractType.TASK, "PROJ-001", "TASK-001", 1)
    assert original_v1.document["objective"] == "Implement contract ingestion."
