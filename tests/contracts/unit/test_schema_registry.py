import json
import shutil
from pathlib import Path

import pytest

from factory.contracts.models import ContractType
from factory.contracts.validation.schema_registry import SchemaRegistry

SCHEMA_ROOT = Path("schemas")


def test_registry_loads_every_contract_schema() -> None:
    registry = SchemaRegistry.load(SCHEMA_ROOT)
    for contract_type in ContractType:
        schema = registry.get(contract_type, "1.0")
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_registry_rejects_unsupported_schema_version() -> None:
    registry = SchemaRegistry.load(SCHEMA_ROOT)
    with pytest.raises(KeyError, match="unsupported schema"):
        registry.get(ContractType.TASK, "999.0")


@pytest.fixture
def schema_copy(tmp_path: Path) -> Path:
    destination = tmp_path / "schemas"
    shutil.copytree(SCHEMA_ROOT, destination)
    return destination


def test_load_rejects_a_non_json_object_schema_file(schema_copy: Path) -> None:
    path = schema_copy / "contracts" / "task" / "v1.schema.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(ValueError, match="not a JSON object"):
        SchemaRegistry.load(schema_copy)


def test_load_rejects_a_missing_common_directory(schema_copy: Path) -> None:
    shutil.rmtree(schema_copy / "common")
    with pytest.raises(ValueError, match="missing required schema directory"):
        SchemaRegistry.load(schema_copy)


def test_load_rejects_a_missing_contracts_directory(schema_copy: Path) -> None:
    shutil.rmtree(schema_copy / "contracts")
    with pytest.raises(ValueError, match="missing required schema directory"):
        SchemaRegistry.load(schema_copy)


def test_load_rejects_a_schema_missing_a_stable_id(schema_copy: Path) -> None:
    path = schema_copy / "contracts" / "task" / "v1.schema.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    del document["$id"]
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="missing stable \\$id"):
        SchemaRegistry.load(schema_copy)


def test_load_rejects_a_duplicate_schema_id(schema_copy: Path) -> None:
    project_path = schema_copy / "contracts" / "project" / "v1.schema.json"
    task_path = schema_copy / "contracts" / "task" / "v1.schema.json"
    project_document = json.loads(project_path.read_text(encoding="utf-8"))
    task_document = json.loads(task_path.read_text(encoding="utf-8"))
    task_document["$id"] = project_document["$id"]
    task_path.write_text(json.dumps(task_document), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate schema \\$id"):
        SchemaRegistry.load(schema_copy)


def test_load_rejects_an_unsupported_draft(schema_copy: Path) -> None:
    path = schema_copy / "contracts" / "task" / "v1.schema.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["$schema"] = "https://json-schema.org/draft/2019-09/schema"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported draft"):
        SchemaRegistry.load(schema_copy)


def test_load_rejects_no_common_schema_resources(schema_copy: Path) -> None:
    for path in (schema_copy / "common").glob("*.schema.json"):
        path.unlink()
    with pytest.raises(ValueError, match="no common schema resources"):
        SchemaRegistry.load(schema_copy)


def test_load_rejects_a_missing_contract_family_schema(schema_copy: Path) -> None:
    (schema_copy / "contracts" / "task" / "v1.schema.json").unlink()
    with pytest.raises(ValueError, match="missing contract family schema"):
        SchemaRegistry.load(schema_copy)
