import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from factory.contracts.errors import ContractError
from factory.contracts.models import ContractType, ErrorCode
from factory.contracts.references.resolver import ReferenceResolver
from factory.contracts.repository.filesystem import ContractFileRepository
from factory.contracts.service import ContractService
from factory.contracts.validation.schema_registry import SchemaRegistry

SCHEMA_ROOT = Path("schemas")
FIXTURES_ROOT = Path("tests/contracts/fixtures/valid")


def _load_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES_ROOT / name).read_text(encoding="utf-8"))


@pytest.fixture
def repository(tmp_path: Path) -> ContractFileRepository:
    service = ContractService(SchemaRegistry.load(SCHEMA_ROOT))
    return ContractFileRepository(root=tmp_path, service=service)


@pytest.fixture
def resolver(repository: ContractFileRepository) -> ReferenceResolver:
    return ReferenceResolver(repository=repository)


def _write_task(
    repository: ContractFileRepository,
    task_id: str,
    *,
    dependencies: list[dict[str, Any]] | None = None,
    status: str = "APPROVED",
) -> None:
    document = _load_fixture("task.json")
    document["id"] = task_id
    document["status"] = status
    document["dependencies"] = dependencies or []
    text = yaml.safe_dump(document, sort_keys=False)
    repository.create_version(ContractType.TASK, "PROJ-001", task_id, 1, text)


def _write_requirement(repository: ContractFileRepository) -> None:
    document = _load_fixture("requirement.json")
    text = yaml.safe_dump(document, sort_keys=False)
    repository.create_version(ContractType.REQUIREMENT, "PROJ-001", "REQ-001", 1, text)


def _write_ownership(repository: ContractFileRepository) -> None:
    document = _load_fixture("ownership.json")
    text = yaml.safe_dump(document, sort_keys=False)
    repository.create_version(ContractType.OWNERSHIP, "PROJ-001", "OWN-001", 1, text)


def _write_permission(repository: ContractFileRepository) -> None:
    document = _load_fixture("permission.json")
    text = yaml.safe_dump(document, sort_keys=False)
    repository.create_version(ContractType.PERMISSION, "PROJ-001", "PERM-001", 1, text)


def _write_evidence(repository: ContractFileRepository) -> None:
    document = _load_fixture("evidence.json")
    text = yaml.safe_dump(document, sort_keys=False)
    repository.create_version(ContractType.EVIDENCE, "PROJ-001", "EVID-001", 1, text)


def test_resolve_returns_matching_contract(
    repository: ContractFileRepository, resolver: ReferenceResolver
) -> None:
    _write_requirement(repository)
    reference = {"id": "REQ-001", "version": 1}
    contract = resolver.resolve(reference, ContractType.REQUIREMENT, "PROJ-001")
    assert contract.contract_id == "REQ-001"


def test_resolve_rejects_missing_reference(resolver: ReferenceResolver) -> None:
    with pytest.raises(ContractError) as raised:
        resolver.resolve({"id": "REQ-404", "version": 1}, ContractType.REQUIREMENT, "PROJ-001")
    assert raised.value.code is ErrorCode.REFERENCE_REJECTED


def test_resolve_rejects_reference_to_rejected_contract(
    repository: ContractFileRepository, resolver: ReferenceResolver
) -> None:
    _write_task(repository, "TASK-001", status="REJECTED")
    with pytest.raises(ContractError) as raised:
        resolver.resolve({"id": "TASK-001", "version": 1}, ContractType.TASK, "PROJ-001")
    assert raised.value.code is ErrorCode.REFERENCE_REJECTED


def test_resolve_all_resolves_direct_task_references(
    repository: ContractFileRepository, resolver: ReferenceResolver
) -> None:
    _write_requirement(repository)
    _write_ownership(repository)
    _write_permission(repository)
    _write_evidence(repository)
    _write_task(repository, "TASK-001")

    task = repository.load(ContractType.TASK, "PROJ-001", "TASK-001", 1)
    resolved = resolver.resolve_all(task)

    resolved_ids = {contract.contract_id for contract in resolved.values()}
    assert resolved_ids == {"REQ-001", "OWN-001", "PERM-001", "EVID-001"}


def test_resolve_dependency_graph_resolves_transitive_chain(
    repository: ContractFileRepository, resolver: ReferenceResolver
) -> None:
    _write_task(repository, "TASK-C")
    _write_task(repository, "TASK-B", dependencies=[{"id": "TASK-C", "version": 1}])
    _write_task(repository, "TASK-A", dependencies=[{"id": "TASK-B", "version": 1}])

    task_a = repository.load(ContractType.TASK, "PROJ-001", "TASK-A", 1)
    graph = resolver.resolve_dependency_graph(task_a)

    resolved_ids = {contract.contract_id for contract in graph.values()}
    assert resolved_ids == {"TASK-B", "TASK-C"}


def test_resolve_dependency_graph_rejects_cycles(
    repository: ContractFileRepository, resolver: ReferenceResolver
) -> None:
    _write_task(repository, "TASK-A", dependencies=[{"id": "TASK-B", "version": 1}])
    _write_task(repository, "TASK-B", dependencies=[{"id": "TASK-A", "version": 1}])

    task_a = repository.load(ContractType.TASK, "PROJ-001", "TASK-A", 1)
    with pytest.raises(ContractError) as raised:
        resolver.resolve_dependency_graph(task_a)
    assert raised.value.code is ErrorCode.REFERENCE_REJECTED
    assert "cycle" in raised.value.message.lower()
