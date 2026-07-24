from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from jsonschema import Draft202012Validator

from factory.contracts.models import (
    ContractType,
    ErrorCode,
    JsonValue,
    ValidationIssue,
    ValidationReport,
)
from factory.contracts.validation.schema_registry import SchemaRegistry

_KNOWN_CONTRACT_TYPES = frozenset(member.value for member in ContractType)


def _pointer_for(path: Sequence[object]) -> str:
    if not path:
        return ""
    return "/" + "/".join(str(segment) for segment in path)


@dataclass(frozen=True, slots=True)
class StructuralValidator:
    registry: SchemaRegistry

    def validate(self, document: Mapping[str, JsonValue]) -> ValidationReport:
        contract_type_value = document.get("contract_type")
        if not isinstance(contract_type_value, str):
            return ValidationReport(
                valid=False,
                issues=(
                    ValidationIssue(
                        ErrorCode.SCHEMA_REJECTED,
                        "/contract_type",
                        "contract_type is missing or not a string",
                    ),
                ),
            )
        if contract_type_value not in _KNOWN_CONTRACT_TYPES:
            return ValidationReport(
                valid=False,
                issues=(
                    ValidationIssue(
                        ErrorCode.SCHEMA_REJECTED,
                        "/contract_type",
                        f"contract_type is not a recognized contract type: {contract_type_value!r}",
                    ),
                ),
            )

        schema_version_value = document.get("schema_version")
        if not isinstance(schema_version_value, str):
            return ValidationReport(
                valid=False,
                issues=(
                    ValidationIssue(
                        ErrorCode.SCHEMA_REJECTED,
                        "/schema_version",
                        "schema_version is missing or not a string",
                    ),
                ),
            )

        contract_type = ContractType(contract_type_value)
        try:
            schema = self.registry.get(contract_type, schema_version_value)
        except KeyError as exc:
            return ValidationReport(
                valid=False,
                issues=(ValidationIssue(ErrorCode.SCHEMA_REJECTED, "/schema_version", str(exc)),),
            )

        validator = Draft202012Validator(schema, registry=self.registry.resource_registry)
        issues = [
            ValidationIssue(
                ErrorCode.SCHEMA_REJECTED, _pointer_for(error.absolute_path), error.message
            )
            for error in validator.iter_errors(document)
        ]
        issues.sort(key=lambda issue: (issue.path, issue.message))
        return ValidationReport(valid=not issues, issues=tuple(issues))
