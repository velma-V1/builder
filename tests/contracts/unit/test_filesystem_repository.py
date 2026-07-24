import json
from pathlib import Path

import pytest
import yaml

from factory.contracts.errors import ContractError
from factory.contracts.models import ContractType, ErrorCode
from factory.contracts.repository.filesystem import ContractFileRepository
from factory.contracts.service import ContractService
from factory.contracts.validation.schema_registry import SchemaRegistry

SCHEMA_ROOT = Path("schemas")
FIXTURES_ROOT = Path("tests/contracts/fixtures/valid")


def _yaml_text(name: str) -> str:
    document = json.loads((FIXTURES_ROOT / name).read_text(encoding="utf-8"))
    return yaml.safe_dump(document, sort_keys=False)


@pytest.fixture
def repository(tmp_path: Path) -> ContractFileRepository:
    service = ContractService(SchemaRegistry.load(SCHEMA_ROOT))
    return ContractFileRepository(root=tmp_path, service=service)


def test_path_for_matches_the_locked_naming_convention(repository: ContractFileRepository) -> None:
    path = repository.path_for(ContractType.TASK, "PROJ-001", "TASK-042", 3)
    assert path == repository.root / "tasks" / "PROJ-001" / "TASK-042" / "v3.yaml"


def test_create_version_then_load_round_trips(repository: ContractFileRepository) -> None:
    text = _yaml_text("project.json")
    written = repository.create_version(ContractType.PROJECT, "PROJ-001", "PROJ-001", 1, text)
    assert written == repository.path_for(ContractType.PROJECT, "PROJ-001", "PROJ-001", 1)

    contract = repository.load(ContractType.PROJECT, "PROJ-001", "PROJ-001", 1)
    assert contract.contract_id == "PROJ-001"
    assert contract.version == 1


def test_create_version_never_overwrites_existing_version(
    repository: ContractFileRepository,
) -> None:
    text = _yaml_text("project.json")
    repository.create_version(ContractType.PROJECT, "PROJ-001", "PROJ-001", 1, text)
    with pytest.raises(ContractError) as raised:
        repository.create_version(ContractType.PROJECT, "PROJ-001", "PROJ-001", 1, text)
    assert raised.value.code is ErrorCode.REFERENCE_REJECTED


def test_create_version_rejects_identity_mismatch(repository: ContractFileRepository) -> None:
    text = _yaml_text("project.json")
    with pytest.raises(ContractError) as raised:
        repository.create_version(ContractType.PROJECT, "PROJ-001", "WRONG-ID", 1, text)
    assert raised.value.code is ErrorCode.REFERENCE_REJECTED


def test_create_version_rejects_invalid_document(repository: ContractFileRepository) -> None:
    document = json.loads((FIXTURES_ROOT / "project.json").read_text(encoding="utf-8"))
    del document["resource_ceilings"]
    text = yaml.safe_dump(document, sort_keys=False)
    with pytest.raises(ContractError) as raised:
        repository.create_version(ContractType.PROJECT, "PROJ-001", "PROJ-001", 1, text)
    assert raised.value.code is ErrorCode.SCHEMA_REJECTED


def test_list_versions_returns_sorted_versions(repository: ContractFileRepository) -> None:
    document = json.loads((FIXTURES_ROOT / "task.json").read_text(encoding="utf-8"))
    for version in (1, 2, 3):
        document["version"] = version
        text = yaml.safe_dump(document, sort_keys=False)
        repository.create_version(ContractType.TASK, "PROJ-001", "TASK-001", version, text)

    versions = repository.list_versions(ContractType.TASK, "PROJ-001", "TASK-001")
    assert versions == (1, 2, 3)


def test_list_versions_empty_when_no_versions_exist(repository: ContractFileRepository) -> None:
    assert repository.list_versions(ContractType.TASK, "PROJ-001", "TASK-999") == ()


def test_load_raises_when_version_missing(repository: ContractFileRepository) -> None:
    with pytest.raises(ContractError) as raised:
        repository.load(ContractType.PROJECT, "PROJ-001", "PROJ-001", 1)
    assert raised.value.code is ErrorCode.REFERENCE_REJECTED


def test_load_raises_when_file_identity_was_tampered(repository: ContractFileRepository) -> None:
    path = repository.path_for(ContractType.PROJECT, "PROJ-001", "PROJ-001", 1)
    path.parent.mkdir(parents=True)
    document = json.loads((FIXTURES_ROOT / "project.json").read_text(encoding="utf-8"))
    document["id"] = "PROJ-999"
    document["project_id"] = "PROJ-999"
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

    with pytest.raises(ContractError) as raised:
        repository.load(ContractType.PROJECT, "PROJ-001", "PROJ-001", 1)
    assert raised.value.code is ErrorCode.REFERENCE_REJECTED
