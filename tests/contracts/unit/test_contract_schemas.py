import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from factory.contracts.models import ContractType
from factory.contracts.validation.schema_registry import SchemaRegistry

SCHEMA_ROOT = Path("schemas")
FIXTURES_ROOT = Path("tests/contracts/fixtures")

VALID_FIXTURES = sorted((FIXTURES_ROOT / "valid").glob("*.json"))
INVALID_FIXTURES = sorted((FIXTURES_ROOT / "invalid").glob("*.json"))


def _contract_type_for(document: dict[str, object]) -> ContractType:
    return ContractType(document["contract_type"])


def _validator_for(registry: SchemaRegistry, contract_type: ContractType) -> Draft202012Validator:
    schema = registry.get(contract_type, "1.0")
    return Draft202012Validator(dict(schema), registry=registry.resource_registry)


@pytest.mark.parametrize("fixture_path", VALID_FIXTURES, ids=lambda p: p.stem)
def test_valid_fixtures_pass_schema_validation(fixture_path: Path) -> None:
    registry = SchemaRegistry.load(SCHEMA_ROOT)
    document = json.loads(fixture_path.read_text(encoding="utf-8"))
    validator = _validator_for(registry, _contract_type_for(document))
    errors = list(validator.iter_errors(document))
    assert errors == []


@pytest.mark.parametrize("fixture_path", INVALID_FIXTURES, ids=lambda p: p.stem)
def test_invalid_fixtures_fail_schema_validation(fixture_path: Path) -> None:
    registry = SchemaRegistry.load(SCHEMA_ROOT)
    document = json.loads(fixture_path.read_text(encoding="utf-8"))
    validator = _validator_for(registry, _contract_type_for(document))
    errors = list(validator.iter_errors(document))
    assert errors != []


def test_all_seven_contract_types_have_valid_fixtures() -> None:
    stems = {path.stem for path in VALID_FIXTURES}
    assert stems == {contract_type.value for contract_type in ContractType}
