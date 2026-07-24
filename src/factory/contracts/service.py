from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from factory.contracts.canonicalization.jcs import canonicalize
from factory.contracts.errors import ContractError
from factory.contracts.models import CanonicalContract, ContractType, ErrorCode, JsonValue
from factory.contracts.parsing.yaml_parser import YamlLimits, parse_yaml_contract
from factory.contracts.validation.schema_registry import SchemaRegistry
from factory.contracts.validation.structural import StructuralValidator


def _require_str(document: Mapping[str, JsonValue], key: str) -> str:
    value = document[key]
    if not isinstance(value, str):
        raise ContractError(ErrorCode.SCHEMA_REJECTED, f"{key} must be a string after validation")
    return value


def _require_int(document: Mapping[str, JsonValue], key: str) -> int:
    value = document[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContractError(ErrorCode.SCHEMA_REJECTED, f"{key} must be an integer after validation")
    return value


@dataclass(slots=True)
class ContractService:
    schemas: SchemaRegistry

    def ingest(self, source_path: Path) -> CanonicalContract:
        limits = YamlLimits()
        with source_path.open("rb") as handle:
            raw = handle.read(limits.max_bytes + 1)
        if len(raw) > limits.max_bytes:
            raise ContractError(
                ErrorCode.PARSE_REJECTED, f"{source_path}: input exceeds maximum allowed size"
            )

        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            message = f"{source_path}: not valid UTF-8"
            raise ContractError(ErrorCode.PARSE_REJECTED, message) from exc

        document = parse_yaml_contract(text, limits)

        validator = StructuralValidator(self.schemas)
        validation = validator.validate(document)
        if not validation.valid:
            raise ContractError(
                ErrorCode.SCHEMA_REJECTED,
                f"{source_path}: contract failed structural validation",
                issues=validation.issues,
            )

        canonical = canonicalize(document)

        return CanonicalContract(
            source_path=source_path,
            contract_type=ContractType(_require_str(document, "contract_type")),
            contract_id=_require_str(document, "id"),
            version=_require_int(document, "version"),
            schema_version=_require_str(document, "schema_version"),
            project_id=_require_str(document, "project_id"),
            canonical_bytes=canonical.canonical_bytes,
            content_hash=canonical.content_hash,
            document=canonical.document,
            validation=validation,
        )
