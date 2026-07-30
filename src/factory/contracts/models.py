from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

JsonScalar = None | bool | int | float | str
JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]


class ContractType(StrEnum):
    PROJECT = "project"
    REQUIREMENT = "requirement"
    TASK = "task"
    OWNERSHIP = "ownership"
    PERMISSION = "permission"
    EVIDENCE = "evidence"
    CHANGE = "change"


class ContractStatus(StrEnum):
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    APPROVED = "APPROVED"
    SUPERSEDED = "SUPERSEDED"
    REJECTED = "REJECTED"
    RETIRED = "RETIRED"


class ErrorCode(StrEnum):
    PARSE_REJECTED = "PARSE_REJECTED"
    SCHEMA_REJECTED = "SCHEMA_REJECTED"
    REFERENCE_REJECTED = "REFERENCE_REJECTED"
    SEMANTIC_REJECTED = "SEMANTIC_REJECTED"
    AUTHORITY_CONFLICT = "AUTHORITY_CONFLICT"
    IMPACT_UNPROVEN = "IMPACT_UNPROVEN"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    CACHE_QUARANTINED = "CACHE_QUARANTINED"
    SECURITY_DENIED = "SECURITY_DENIED"
    ACTIVATION_ROLLED_BACK = "ACTIVATION_ROLLED_BACK"


class PolicyOutcome(StrEnum):
    ALLOW = "ALLOW"
    ALLOW_WITH_CHECKPOINT = "ALLOW_WITH_CHECKPOINT"
    SERIALIZE_AND_TEST = "SERIALIZE_AND_TEST"
    HUMAN_APPROVAL_REQUIRED = "HUMAN_APPROVAL_REQUIRED"
    DENY_SECURITY_VIOLATION = "DENY_SECURITY_VIOLATION"


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: ErrorCode
    path: str
    message: str


@dataclass(frozen=True, slots=True)
class ValidationReport:
    valid: bool
    issues: tuple[ValidationIssue, ...]


@dataclass(frozen=True, slots=True)
class CanonicalContract:
    source_path: Path
    contract_type: ContractType
    contract_id: str
    version: int
    schema_version: str
    project_id: str
    canonical_bytes: bytes
    content_hash: str
    document: Mapping[str, JsonValue]
    validation: ValidationReport


@dataclass(frozen=True, slots=True)
class ImpactResult:
    compatible: bool
    ownership_conflicts: tuple[str, ...]
    affected_components: tuple[str, ...]
    required_tests: tuple[str, ...]
    authority_expanded: bool
    evidence_weakened: bool
    protected_boundary_crossed: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    outcome: PolicyOutcome
    reasons: tuple[str, ...]
    required_approvals: tuple[str, ...]
    required_tests: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ActivationRecord:
    project_id: str
    contract_id: str
    contract_version: int
    schema_version: str
    generation: int
    content_hash: str
    runtime_status: str


@dataclass(frozen=True, slots=True)
class CacheEntry:
    record: ActivationRecord
    canonical_bytes: bytes
    document: Mapping[str, JsonValue]
