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
def resolver(repository: ContractFileRepository) -> ReferenceResolver:
    return ReferenceResolver(repository=repository)


def _write(
    repository: ContractFileRepository, contract_type: ContractType, document: dict[str, Any]
) -> None:
    text = yaml.safe_dump(document, sort_keys=False)
    repository.create_version(
        contract_type, document["project_id"], document["id"], document["version"], text
    )


def test_reference_cannot_cross_into_another_projects_directory(
    repository: ContractFileRepository, resolver: ReferenceResolver
) -> None:
    victim_requirement = _load_fixture("requirement.json")
    victim_requirement["project_id"] = "PROJ-VICTIM"
    _write(repository, ContractType.REQUIREMENT, victim_requirement)

    # An attacker-controlled task claims project PROJ-ATTACKER but tries to reference the
    # victim project's requirement by ID. Since the repository path is keyed by project_id,
    # this must resolve as "not found" under the attacker's own project, not leak the victim's
    # contract.
    with pytest.raises(ContractError) as raised:
        resolver.resolve({"id": "REQ-001", "version": 1}, ContractType.REQUIREMENT, "PROJ-ATTACKER")
    assert raised.value.code is ErrorCode.REFERENCE_REJECTED


def test_repository_load_rejects_a_file_whose_envelope_claims_a_different_project(
    repository: ContractFileRepository,
) -> None:
    # Simulate a filesystem-level tamper/injection: a file physically placed under
    # PROJ-A's directory tree, but whose YAML envelope claims to belong to PROJ-B.
    tampered = _load_fixture("requirement.json")
    tampered["project_id"] = "PROJ-999"
    path = repository.path_for(ContractType.REQUIREMENT, "PROJ-001", "REQ-001", 1)
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(tampered, sort_keys=False), encoding="utf-8")

    with pytest.raises(ContractError) as raised:
        repository.load(ContractType.REQUIREMENT, "PROJ-001", "REQ-001", 1)
    assert raised.value.code is ErrorCode.REFERENCE_REJECTED


def test_semantic_validation_rejects_task_referencing_across_projects(
    repository: ContractFileRepository, resolver: ReferenceResolver
) -> None:
    other_project_requirement = _load_fixture("requirement.json")
    other_project_requirement["project_id"] = "PROJ-OTHER"
    _write(repository, ContractType.REQUIREMENT, other_project_requirement)

    task_doc = _load_fixture("task.json")
    task_doc["parent_requirements"] = [{"id": "REQ-001", "version": 1}]
    _write(repository, ContractType.TASK, task_doc)  # task itself lives under PROJ-001

    validator = SemanticValidator(
        resolver=resolver,
        path_authority_factory=lambda root: PathAuthority(project_root=root),
        approved_routes=APPROVED_ROUTES,
    )
    task = repository.load(ContractType.TASK, "PROJ-001", "TASK-001", 1)
    report = validator.validate(task, active_ownership={})

    # The referenced requirement only exists under PROJ-OTHER, not PROJ-001, so this must fail.
    assert not report.valid
    assert any(issue.code is ErrorCode.REFERENCE_REJECTED for issue in report.issues)
