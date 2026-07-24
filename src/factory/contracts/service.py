from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from factory.contracts.canonicalization.jcs import canonicalize
from factory.contracts.errors import ContractError
from factory.contracts.models import (
    CanonicalContract,
    ContractType,
    ErrorCode,
    ImpactResult,
    JsonValue,
    PolicyDecision,
    PolicyOutcome,
    ValidationIssue,
    ValidationReport,
)
from factory.contracts.parsing.yaml_parser import YamlLimits, parse_yaml_contract
from factory.contracts.validation.schema_registry import SchemaRegistry
from factory.contracts.validation.structural import StructuralValidator

if TYPE_CHECKING:
    from factory.contracts.impact.analyzer import ImpactAnalyzer
    from factory.contracts.policy.engine import PolicyEngine
    from factory.contracts.repository.filesystem import ContractFileRepository
    from factory.contracts.validation.semantic import SemanticValidator

_PROTECTED_ENVELOPE_POINTERS = frozenset(
    {"/id", "/contract_type", "/project_id", "/schema_version", "/created_at", "/created_by"}
)


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


def _thaw(value: object) -> JsonValue:
    """Convert a frozen (MappingProxyType/tuple) document back into plain dict/list."""
    if value is None or isinstance(value, bool | int | float | str):
        return value
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_thaw(item) for item in value]
    message = f"unsupported value type while thawing: {type(value)!r}"
    raise ContractError(ErrorCode.SEMANTIC_REJECTED, message)


def _unescape_token(token: str) -> str:
    return token.replace("~1", "/").replace("~0", "~")


def _parse_pointer(pointer: str) -> list[str]:
    if pointer == "":
        return []
    if not pointer.startswith("/"):
        raise ContractError(ErrorCode.SEMANTIC_REJECTED, f"invalid JSON pointer: {pointer!r}")
    return [_unescape_token(token) for token in pointer[1:].split("/")]


def _list_index(index_token: str, length: int, *, for_insert: bool) -> int:
    if index_token == "-" and for_insert:  # noqa: S105 -- JSON Pointer "-" append marker, not a secret
        return length
    if not index_token.isdigit():
        message = f"invalid JSON pointer array index: {index_token!r}"
        raise ContractError(ErrorCode.SEMANTIC_REJECTED, message)
    index = int(index_token)
    limit = length if for_insert else length - 1
    if index < 0 or index > limit:
        message = f"JSON pointer array index out of range: {index_token!r}"
        raise ContractError(ErrorCode.SEMANTIC_REJECTED, message)
    return index


def _navigate_parent(document: JsonValue, tokens: Sequence[str]) -> JsonValue:
    current = document
    for token in tokens[:-1]:
        if isinstance(current, dict):
            if token not in current:
                message = f"JSON pointer segment not found: {token!r}"
                raise ContractError(ErrorCode.SEMANTIC_REJECTED, message)
            current = current[token]
        elif isinstance(current, list):
            current = current[_list_index(token, len(current), for_insert=False)]
        else:
            message = "JSON pointer traverses a scalar value"
            raise ContractError(ErrorCode.SEMANTIC_REJECTED, message)
    return current


def _apply_add(document: JsonValue, tokens: Sequence[str], value: JsonValue) -> None:
    if not tokens:
        raise ContractError(ErrorCode.SEMANTIC_REJECTED, "cannot replace the document root")
    parent = _navigate_parent(document, tokens)
    last = tokens[-1]
    if isinstance(parent, dict):
        parent[last] = copy.deepcopy(value)
    elif isinstance(parent, list):
        parent.insert(_list_index(last, len(parent), for_insert=True), copy.deepcopy(value))
    else:
        raise ContractError(ErrorCode.SEMANTIC_REJECTED, "cannot add beneath a scalar value")


def _apply_replace(document: JsonValue, tokens: Sequence[str], value: JsonValue) -> None:
    if not tokens:
        raise ContractError(ErrorCode.SEMANTIC_REJECTED, "cannot replace the document root")
    parent = _navigate_parent(document, tokens)
    last = tokens[-1]
    if isinstance(parent, dict):
        if last not in parent:
            message = f"cannot replace missing field: {last!r}"
            raise ContractError(ErrorCode.SEMANTIC_REJECTED, message)
        parent[last] = copy.deepcopy(value)
    elif isinstance(parent, list):
        parent[_list_index(last, len(parent), for_insert=False)] = copy.deepcopy(value)
    else:
        raise ContractError(ErrorCode.SEMANTIC_REJECTED, "cannot replace beneath a scalar value")


def _apply_remove(document: JsonValue, tokens: Sequence[str]) -> None:
    if not tokens:
        raise ContractError(ErrorCode.SEMANTIC_REJECTED, "cannot remove the document root")
    parent = _navigate_parent(document, tokens)
    last = tokens[-1]
    if isinstance(parent, dict):
        if last not in parent:
            message = f"cannot remove missing field: {last!r}"
            raise ContractError(ErrorCode.SEMANTIC_REJECTED, message)
        del parent[last]
    elif isinstance(parent, list):
        del parent[_list_index(last, len(parent), for_insert=False)]
    else:
        raise ContractError(ErrorCode.SEMANTIC_REJECTED, "cannot remove beneath a scalar value")


def _apply_change_operations(
    target_document: Mapping[str, JsonValue], operations: Sequence[Mapping[str, JsonValue]]
) -> dict[str, JsonValue]:
    thawed = _thaw(target_document)
    if not isinstance(thawed, dict):
        raise ContractError(ErrorCode.SEMANTIC_REJECTED, "target document must be a JSON object")
    result: dict[str, JsonValue] = thawed

    for operation in operations:
        path = operation.get("path")
        if not isinstance(path, str):
            raise ContractError(ErrorCode.SEMANTIC_REJECTED, "change operation is missing a path")
        if path in _PROTECTED_ENVELOPE_POINTERS:
            raise ContractError(
                ErrorCode.SEMANTIC_REJECTED,
                f"change operations may not modify a protected envelope field: {path}",
            )
        tokens = _parse_pointer(path)
        op = operation.get("op")
        if op == "remove":
            _apply_remove(result, tokens)
        elif op == "add":
            _apply_add(result, tokens, operation["value"])
        elif op == "replace":
            _apply_replace(result, tokens, operation["value"])
        else:
            message = f"unsupported change operation: {op!r}"
            raise ContractError(ErrorCode.SEMANTIC_REJECTED, message)

    return result


@dataclass(frozen=True, slots=True)
class ChangeApplicationResult:
    proposed: CanonicalContract
    impact: ImpactResult
    policy: PolicyDecision
    written_path: Path


@dataclass(slots=True)
class ChangeApplicationService:
    repository: ContractFileRepository
    semantic_validator: SemanticValidator
    impact_analyzer: ImpactAnalyzer
    policy_engine: PolicyEngine

    def apply(
        self,
        change: CanonicalContract,
        *,
        target_type: ContractType,
        active_ownership: Mapping[str, Sequence[str]],
        evidence_passed: bool,
        rollback_available: bool,
    ) -> ChangeApplicationResult:
        document = change.document
        target_ref = document.get("target")
        operations = document.get("operations")
        resulting_version = document.get("resulting_version")
        if not isinstance(target_ref, Mapping) or not isinstance(operations, Sequence):
            message = "change is missing target or operations"
            raise ContractError(ErrorCode.SEMANTIC_REJECTED, message)

        target_id = target_ref.get("id")
        target_version = target_ref.get("version")
        if not isinstance(target_id, str) or not isinstance(target_version, int):
            raise ContractError(ErrorCode.SEMANTIC_REJECTED, "change target reference is malformed")

        target = self.repository.load(target_type, change.project_id, target_id, target_version)

        new_version = target.version + 1
        if resulting_version != new_version:
            raise ContractError(
                ErrorCode.SEMANTIC_REJECTED,
                f"resulting_version must equal target version plus one: "
                f"expected {new_version}, got {resulting_version!r}",
            )

        patched = _apply_change_operations(
            target.document, [op for op in operations if isinstance(op, Mapping)]
        )
        patched["version"] = new_version
        patched["status"] = "VALIDATED"
        patched["created_at"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

        related = patched.get("related_contracts")
        change_ref: dict[str, JsonValue] = {"id": change.contract_id, "version": change.version}
        if isinstance(related, list):
            if change_ref not in related:
                related.append(change_ref)
        else:
            patched["related_contracts"] = [change_ref]

        structural_validator = StructuralValidator(self.repository.service.schemas)
        structural_report = structural_validator.validate(patched)
        if not structural_report.valid:
            raise ContractError(
                ErrorCode.SCHEMA_REJECTED,
                "the resulting contract version failed structural validation",
                issues=structural_report.issues,
            )

        canonical = canonicalize(patched)
        source_path = self.repository.path_for(
            target_type, change.project_id, target_id, new_version
        )
        proposed = CanonicalContract(
            source_path=source_path,
            contract_type=target_type,
            contract_id=target_id,
            version=new_version,
            schema_version=target.schema_version,
            project_id=change.project_id,
            canonical_bytes=canonical.canonical_bytes,
            content_hash=canonical.content_hash,
            document=canonical.document,
            validation=structural_report,
        )

        semantic_report = self.semantic_validator.validate(
            proposed, active_ownership=active_ownership
        )
        combined_issues = tuple(structural_report.issues) + tuple(semantic_report.issues)
        combined_validation = ValidationReport(
            valid=structural_report.valid and semantic_report.valid, issues=combined_issues
        )

        # `linked` represents *other* components genuinely impacted by this change (e.g. shared
        # interface consumers), not this contract's own forward references (ownership/permission/
        # evidence scaffolding, which every task has and which `resolve_all` would always return).
        # Section 1 / PH-1 has no reverse-dependency index across workstreams (R2 defers that), so
        # there is nothing honest to put here yet; a future section can populate it from such an
        # index once one exists.
        linked: Mapping[str, CanonicalContract] = {}

        impact = self.impact_analyzer.compare(target, proposed, linked)
        policy = self.policy_engine.decide(
            candidate=proposed,
            impact=impact,
            validation=combined_validation,
            evidence_passed=evidence_passed,
            rollback_available=rollback_available,
            deletion_classification=None,
        )

        if policy.outcome is PolicyOutcome.DENY_SECURITY_VIOLATION:
            deny_issues = tuple(
                ValidationIssue(ErrorCode.SECURITY_DENIED, "/", reason) for reason in policy.reasons
            )
            raise ContractError(
                ErrorCode.SECURITY_DENIED, "change application denied by policy", issues=deny_issues
            )

        yaml_text = yaml.safe_dump(patched, sort_keys=False)
        written_path = self.repository.create_version(
            target_type, change.project_id, target_id, new_version, yaml_text
        )
        proposed = self.repository.load(target_type, change.project_id, target_id, new_version)

        return ChangeApplicationResult(
            proposed=proposed, impact=impact, policy=policy, written_path=written_path
        )
