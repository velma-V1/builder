from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from factory.contracts.errors import ContractError
from factory.contracts.models import (
    CanonicalContract,
    ContractType,
    ErrorCode,
    ValidationIssue,
    ValidationReport,
)
from factory.contracts.references.resolver import ReferenceResolver
from factory.contracts.validation.paths import PathAuthority

_RUNTIME_ONLY_FIELDS = frozenset({"generation", "content_hash", "lane_id", "current_model"})
_DISALLOWED_AUTHORED_STATUSES = frozenset({"SUPERSEDED"})


def _segments_unify(left: Sequence[str], right: Sequence[str]) -> bool:
    if not left and not right:
        return True
    if not left:
        return right[0] == "**" and _segments_unify(left, right[1:])
    if not right:
        return left[0] == "**" and _segments_unify(left[1:], right)
    if left[0] == "**":
        return _segments_unify(left[1:], right) or _segments_unify(left, right[1:])
    if right[0] == "**":
        return _segments_unify(left, right[1:]) or _segments_unify(left[1:], right)
    if left[0] == "*" or right[0] == "*" or left[0] == right[0]:
        return _segments_unify(left[1:], right[1:])
    return False


def _patterns_conflict(left: str, right: str) -> bool:
    return _segments_unify(
        [segment for segment in left.split("/") if segment],
        [segment for segment in right.split("/") if segment],
    )


@dataclass(slots=True)
class SemanticValidator:
    resolver: ReferenceResolver
    path_authority_factory: Callable[[Path], PathAuthority]
    approved_routes: frozenset[str]

    def validate(
        self,
        contract: CanonicalContract,
        *,
        active_ownership: Mapping[str, Sequence[str]],
    ) -> ValidationReport:
        issues: list[ValidationIssue] = []
        document = contract.document

        status = document.get("status")
        if status in _DISALLOWED_AUTHORED_STATUSES:
            issues.append(
                ValidationIssue(
                    ErrorCode.SEMANTIC_REJECTED,
                    "/status",
                    f"status cannot be directly authored: {status}",
                )
            )
        for field in _RUNTIME_ONLY_FIELDS:
            if field in document:
                issues.append(
                    ValidationIssue(
                        ErrorCode.SEMANTIC_REJECTED,
                        f"/{field}",
                        "runtime-only field must not appear in an authored contract",
                    )
                )

        try:
            self.resolver.resolve_all(contract)
        except ContractError as exc:
            issues.append(ValidationIssue(ErrorCode.REFERENCE_REJECTED, "/", str(exc)))

        try:
            self.resolver.resolve_dependency_graph(contract)
        except ContractError as exc:
            issues.append(ValidationIssue(ErrorCode.REFERENCE_REJECTED, "/dependencies", str(exc)))

        if contract.contract_type is ContractType.TASK:
            issues.extend(self._validate_task(contract))
        elif contract.contract_type is ContractType.OWNERSHIP:
            issues.extend(self._validate_ownership(contract, active_ownership))
        elif contract.contract_type is ContractType.EVIDENCE:
            issues.extend(self._validate_evidence(contract))

        return ValidationReport(valid=not issues, issues=tuple(issues))

    def _load_project(self, project_id: str) -> CanonicalContract | None:
        try:
            versions = self.resolver.repository.list_versions(
                ContractType.PROJECT, project_id, project_id
            )
            if not versions:
                return None
            return self.resolver.repository.load(
                ContractType.PROJECT, project_id, project_id, max(versions)
            )
        except ContractError:
            return None

    def _validate_task(self, contract: CanonicalContract) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        document = contract.document

        permitted_routes = document.get("permitted_routes", [])
        if isinstance(permitted_routes, Sequence):
            for route in permitted_routes:
                if route not in self.approved_routes:
                    issues.append(
                        ValidationIssue(
                            ErrorCode.SEMANTIC_REJECTED,
                            "/permitted_routes",
                            f"route is not approved for this project's privacy setting: {route}",
                        )
                    )

        project = self._load_project(contract.project_id)
        resource_limits = document.get("resource_limits")
        if project is not None and isinstance(resource_limits, Mapping):
            ceilings = project.document.get("resource_ceilings")
            if isinstance(ceilings, Mapping):
                for key, value in resource_limits.items():
                    ceiling = ceilings.get(key)
                    if (
                        isinstance(value, int)
                        and isinstance(ceiling, int)
                        and not isinstance(value, bool)
                        and value > ceiling
                    ):
                        issues.append(
                            ValidationIssue(
                                ErrorCode.SEMANTIC_REJECTED,
                                f"/resource_limits/{key}",
                                f"exceeds project ceiling: {value} > {ceiling}",
                            )
                        )

        ownership_ref = document.get("ownership_contract")
        frozen_interfaces = document.get("frozen_interfaces", [])
        if isinstance(ownership_ref, Mapping) and isinstance(frozen_interfaces, Sequence):
            try:
                ownership = self.resolver.resolve(
                    ownership_ref, ContractType.OWNERSHIP, contract.project_id
                )
            except ContractError:
                ownership = None
            if ownership is not None:
                provided = ownership.document.get("interfaces_provided", [])
                provided_set = set(provided) if isinstance(provided, Sequence) else set()
                for interface in frozen_interfaces:
                    if interface not in provided_set:
                        issues.append(
                            ValidationIssue(
                                ErrorCode.SEMANTIC_REJECTED,
                                "/frozen_interfaces",
                                f"frozen interface not provided by ownership contract: {interface}",
                            )
                        )

        return issues

    def _validate_ownership(
        self, contract: CanonicalContract, active_ownership: Mapping[str, Sequence[str]]
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        document = contract.document
        allowed = document.get("allowed_paths", [])
        forbidden = document.get("forbidden_paths", [])
        read_only = document.get("read_only_paths", [])

        if not (isinstance(allowed, Sequence) and isinstance(forbidden, Sequence)):
            return issues

        for pattern in allowed:
            if pattern in forbidden:
                issues.append(
                    ValidationIssue(
                        ErrorCode.AUTHORITY_CONFLICT,
                        "/allowed_paths",
                        f"path pattern is both allowed and forbidden: {pattern}",
                    )
                )

        project = self._load_project(contract.project_id)
        if project is not None:
            project_root = Path(str(project.document.get("project_root", ".")))
            authority = self.path_authority_factory(project_root)
            for label, patterns in (
                ("/allowed_paths", allowed),
                ("/forbidden_paths", forbidden),
                ("/read_only_paths", read_only if isinstance(read_only, Sequence) else []),
            ):
                for pattern in patterns:
                    if not isinstance(pattern, str):
                        continue
                    result = authority.evaluate(
                        pattern,
                        operation="read",
                        allowed=["**"],
                        forbidden=[],
                        read_only=[],
                        active_exclusive_paths=[],
                    )
                    if not result.allowed:
                        issues.append(
                            ValidationIssue(ErrorCode.SECURITY_DENIED, label, result.reason)
                        )

        for owner_id, other_paths in active_ownership.items():
            for own_pattern in allowed:
                for other_pattern in other_paths:
                    if (
                        isinstance(own_pattern, str)
                        and isinstance(other_pattern, str)
                        and _patterns_conflict(own_pattern, other_pattern)
                    ):
                        issues.append(
                            ValidationIssue(
                                ErrorCode.AUTHORITY_CONFLICT,
                                "/allowed_paths",
                                f"conflicts with active ownership {owner_id!r}: "
                                f"{own_pattern!r} vs {other_pattern!r}",
                            )
                        )

        return issues

    def _validate_evidence(self, contract: CanonicalContract) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        document = contract.document
        requirement_ids = document.get("requirement_ids", [])
        own_categories = document.get("evidence_categories", [])
        reachable: set[str] = set()

        if isinstance(requirement_ids, Sequence):
            for requirement_id in requirement_ids:
                if not isinstance(requirement_id, str):
                    continue
                versions = self.resolver.repository.list_versions(
                    ContractType.REQUIREMENT, contract.project_id, requirement_id
                )
                if not versions:
                    issues.append(
                        ValidationIssue(
                            ErrorCode.REFERENCE_REJECTED,
                            "/requirement_ids",
                            f"requirement not found: {requirement_id}",
                        )
                    )
                    continue
                requirement = self.resolver.repository.load(
                    ContractType.REQUIREMENT, contract.project_id, requirement_id, max(versions)
                )
                categories = requirement.document.get("evidence_categories", [])
                if isinstance(categories, Sequence):
                    string_categories = (c for c in categories if isinstance(c, str))
                    reachable.update(string_categories)

        if reachable and isinstance(own_categories, Sequence):
            for category in own_categories:
                if category not in reachable:
                    issues.append(
                        ValidationIssue(
                            ErrorCode.SEMANTIC_REJECTED,
                            "/evidence_categories",
                            "evidence category not reachable from referenced "
                            f"requirements: {category}",
                        )
                    )

        return issues
