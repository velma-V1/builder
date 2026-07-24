import json
from pathlib import Path

from factory.contracts.models import ErrorCode
from factory.contracts.validation.schema_registry import SchemaRegistry
from factory.contracts.validation.structural import StructuralValidator

SCHEMA_ROOT = Path("schemas")
FIXTURES_ROOT = Path("tests/contracts/fixtures")


def _load(name: str, kind: str) -> dict[str, object]:
    return json.loads((FIXTURES_ROOT / kind / name).read_text(encoding="utf-8"))


def test_valid_document_produces_no_issues() -> None:
    validator = StructuralValidator(SchemaRegistry.load(SCHEMA_ROOT))
    report = validator.validate(_load("project.json", "valid"))
    assert report.valid
    assert report.issues == ()


def test_invalid_document_produces_sorted_deterministic_issues() -> None:
    validator = StructuralValidator(SchemaRegistry.load(SCHEMA_ROOT))
    report = validator.validate(_load("project_missing_resource_ceilings.json", "invalid"))
    assert not report.valid
    assert all(issue.code is ErrorCode.SCHEMA_REJECTED for issue in report.issues)
    paths = [issue.path for issue in report.issues]
    assert paths == sorted(paths)


def test_missing_contract_type_is_rejected() -> None:
    validator = StructuralValidator(SchemaRegistry.load(SCHEMA_ROOT))
    document = _load("project.json", "valid")
    del document["contract_type"]
    report = validator.validate(document)
    assert not report.valid
    assert report.issues[0].code is ErrorCode.SCHEMA_REJECTED


def test_unrecognized_contract_type_is_rejected() -> None:
    validator = StructuralValidator(SchemaRegistry.load(SCHEMA_ROOT))
    document = _load("project.json", "valid")
    document["contract_type"] = "not-a-real-type"
    report = validator.validate(document)
    assert not report.valid


def test_unsupported_schema_version_is_rejected() -> None:
    validator = StructuralValidator(SchemaRegistry.load(SCHEMA_ROOT))
    document = _load("project.json", "valid")
    document["schema_version"] = "999.0"
    report = validator.validate(document)
    assert not report.valid


def test_validation_does_not_mutate_input() -> None:
    validator = StructuralValidator(SchemaRegistry.load(SCHEMA_ROOT))
    document = _load("project.json", "valid")
    original = json.loads(json.dumps(document))
    validator.validate(document)
    assert document == original
