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
