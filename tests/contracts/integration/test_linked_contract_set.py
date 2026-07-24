import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from factory.contracts.impact.analyzer import ImpactAnalyzer
from factory.contracts.models import ContractType
from factory.contracts.references.resolver import ReferenceResolver
from factory.contracts.repository.filesystem import ContractFileRepository
from factory.contracts.service import ContractService
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
def validator(resolver: ReferenceResolver) -> SemanticValidator:
    return SemanticValidator(
        resolver=resolver,
        path_authority_factory=lambda root: PathAuthority(project_root=root),
        approved_routes=APPROVED_ROUTES,
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


def test_full_linked_contract_set_resolves_and_validates_cleanly(
    repository: ContractFileRepository,
    resolver: ReferenceResolver,
    validator: SemanticValidator,
) -> None:
    _seed_full_set(repository)

    task = repository.load(ContractType.TASK, "PROJ-001", "TASK-001", 1)

    resolved = resolver.resolve_all(task)
    assert {contract.contract_id for contract in resolved.values()} == {
        "REQ-001",
        "OWN-001",
        "PERM-001",
        "EVID-001",
    }

    report = validator.validate(task, active_ownership={})
    assert report.valid, report.issues


def test_task_dependency_graph_across_the_linked_set_is_acyclic(
    repository: ContractFileRepository, resolver: ReferenceResolver
) -> None:
    _seed_full_set(repository)

    downstream_doc = _load_fixture("task.json")
    downstream_doc["id"] = "TASK-002"
    downstream_doc["dependencies"] = [{"id": "TASK-001", "version": 1}]
    _write(repository, ContractType.TASK, downstream_doc)

    downstream = repository.load(ContractType.TASK, "PROJ-001", "TASK-002", 1)
    graph = resolver.resolve_dependency_graph(downstream)
    assert {contract.contract_id for contract in graph.values()} == {"TASK-001"}


def test_change_style_revision_reports_impact_against_linked_contracts(
    repository: ContractFileRepository,
) -> None:
    _seed_full_set(repository)
    previous = repository.load(ContractType.TASK, "PROJ-001", "TASK-001", 1)

    revised_doc = _load_fixture("task.json")
    revised_doc["version"] = 2
    revised_doc["objective"] = "Implement contract ingestion, safely and observably."
    revised_doc["autonomy_level"] = 90
    _write(repository, ContractType.TASK, revised_doc)
    proposed = repository.load(ContractType.TASK, "PROJ-001", "TASK-001", 2)

    ownership = repository.load(ContractType.OWNERSHIP, "PROJ-001", "OWN-001", 1)
    analyzer = ImpactAnalyzer()
    result = analyzer.compare(previous, proposed, linked={"OWN-001": ownership})

    assert result.authority_expanded
    assert any("autonomy_level" in reason for reason in result.reasons)
    assert result.affected_components == ("OWN-001",)
