from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from factory.contracts.models import ContractType

_SUPPORTED_SCHEMA_VERSION = "1.0"
_DRAFT_2020_12_URI = "https://json-schema.org/draft/2020-12/schema"


def _load_json(path: Path) -> Mapping[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        loaded = json.load(handle)
    if not isinstance(loaded, dict):
        raise ValueError(f"schema document is not a JSON object: {path}")
    return loaded


@dataclass(frozen=True, slots=True)
class SchemaRegistry:
    _schemas: Mapping[tuple[ContractType, str], Mapping[str, object]]
    resource_registry: Registry

    @classmethod
    def load(cls, schema_root: Path) -> SchemaRegistry:
        common_dir = schema_root / "common"
        contracts_dir = schema_root / "contracts"
        if not common_dir.is_dir():
            raise ValueError(f"missing required schema directory: {common_dir}")
        if not contracts_dir.is_dir():
            raise ValueError(f"missing required schema directory: {contracts_dir}")

        seen_ids: set[str] = set()
        resources: list[tuple[str, Resource[object]]] = []

        def register(document: Mapping[str, object], source: Path) -> None:
            schema_id = document.get("$id")
            if not isinstance(schema_id, str) or not schema_id:
                raise ValueError(f"schema missing stable $id: {source}")
            if schema_id in seen_ids:
                raise ValueError(f"duplicate schema $id {schema_id!r} found in {source}")
            if document.get("$schema") != _DRAFT_2020_12_URI:
                raise ValueError(f"unsupported draft in {source}: expected {_DRAFT_2020_12_URI}")
            Draft202012Validator.check_schema(dict(document))
            seen_ids.add(schema_id)
            resource = Resource.from_contents(dict(document), default_specification=DRAFT202012)
            resources.append((schema_id, resource))

        common_files = sorted(common_dir.glob("*.schema.json"))
        if not common_files:
            raise ValueError(f"no common schema resources found under {common_dir}")
        for path in common_files:
            register(_load_json(path), path)

        schemas: dict[tuple[ContractType, str], Mapping[str, object]] = {}
        for contract_type in ContractType:
            schema_path = contracts_dir / contract_type.value / "v1.schema.json"
            if not schema_path.is_file():
                raise ValueError(f"missing contract family schema: {schema_path}")
            document = _load_json(schema_path)
            register(document, schema_path)
            schemas[(contract_type, _SUPPORTED_SCHEMA_VERSION)] = MappingProxyType(dict(document))

        registry: Registry[object] = Registry().with_resources(resources)
        return cls(MappingProxyType(schemas), registry)

    def get(self, contract_type: ContractType, schema_version: str) -> Mapping[str, object]:
        key = (contract_type, schema_version)
        if key not in self._schemas:
            raise KeyError(
                f"unsupported schema version {schema_version!r} for contract type {contract_type!r}"
            )
        return self._schemas[key]
