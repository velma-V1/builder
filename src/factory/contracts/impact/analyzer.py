from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TypeGuard

from factory.contracts.models import CanonicalContract, ContractType, ImpactResult

# List-valued fields where a *larger* set of values grants *more* authority.
_PERMISSIVE_LIST_FIELDS = (
    "allowed_paths",
    "tools",
    "command_classes",
    "permitted_routes",
    "devices",
    "processes",
    "mounts",
    "interfaces_provided",
    "interfaces_consumed",
)

# List-valued fields where a *smaller* set of values grants *more* authority
# (they are restrictions: removing an entry loosens the contract).
_RESTRICTIVE_LIST_FIELDS = (
    "forbidden_paths",
    "read_only_paths",
    "denied",
    "approval_required",
)

_ORDINAL_FIELDS: dict[str, tuple[str, ...]] = {
    "network": ("NONE", "LOCAL_ONLY", "APPROVED_ROUTES_ONLY"),
    "secrets": ("NONE", "READ_ONLY", "READ_WRITE"),
}

_BOOLEAN_EXPANSION_FIELDS = ("cloud", "dependency_installation")

_NUMERIC_CEILING_FIELDS = (
    "max_tokens_per_task",
    "max_requests_per_task",
    "max_retries",
    "max_seconds_per_task",
    "max_files_per_task",
    "autonomy_level",
)

_NUMERIC_CONTAINER_FIELDS = ("resource_limits", "resource_ceilings")

_EVIDENCE_LIST_FIELDS = (
    "test_commands",
    "evidence_categories",
    "scope_checks",
    "required_evidence",
    "completion_conditions",
    "acceptance_criteria",
)

_RETENTION_ORDER = ("STANDARD", "EXTENDED", "PERMANENT")

_PROTECTED_LIST_FIELDS = ("protected_classes", "protected_path_classes", "protected_branches")


def _as_str_set(value: object) -> set[str]:
    if isinstance(value, Sequence) and not isinstance(value, str):
        return {item for item in value if isinstance(item, str)}
    return set()


def _ordinal_index(order: tuple[str, ...], value: object) -> int | None:
    if isinstance(value, str) and value in order:
        return order.index(value)
    return None


@dataclass(slots=True)
class ImpactAnalyzer:
    def compare(
        self,
        previous: CanonicalContract,
        proposed: CanonicalContract,
        linked: Mapping[str, CanonicalContract],
    ) -> ImpactResult:
        reasons: list[str] = []
        authority_expanded = False
        evidence_weakened = False
        protected_boundary_crossed = False

        prev_doc = previous.document
        new_doc = proposed.document

        for field in _PERMISSIVE_LIST_FIELDS:
            added = _as_str_set(new_doc.get(field)) - _as_str_set(prev_doc.get(field))
            if added:
                authority_expanded = True
                reasons.append(f"authority expanded: {field} gained {sorted(added)}")

        for field in _RESTRICTIVE_LIST_FIELDS:
            removed = _as_str_set(prev_doc.get(field)) - _as_str_set(new_doc.get(field))
            if removed:
                authority_expanded = True
                reasons.append(f"authority expanded: {field} lost restriction {sorted(removed)}")

        for field, order in _ORDINAL_FIELDS.items():
            prev_index = _ordinal_index(order, prev_doc.get(field))
            new_index = _ordinal_index(order, new_doc.get(field))
            if prev_index is not None and new_index is not None and new_index > prev_index:
                authority_expanded = True
                reasons.append(
                    f"authority expanded: {field} raised from "
                    f"{order[prev_index]} to {order[new_index]}"
                )

        for field in _BOOLEAN_EXPANSION_FIELDS:
            if prev_doc.get(field) is False and new_doc.get(field) is True:
                authority_expanded = True
                reasons.append(f"authority expanded: {field} became true")

        for field in _NUMERIC_CEILING_FIELDS:
            prev_value = prev_doc.get(field)
            new_value = new_doc.get(field)
            if _is_plain_int(prev_value) and _is_plain_int(new_value) and new_value > prev_value:
                authority_expanded = True
                reasons.append(
                    f"authority expanded: {field} raised from {prev_value} to {new_value}"
                )

        for container in _NUMERIC_CONTAINER_FIELDS:
            prev_container = prev_doc.get(container)
            new_container = new_doc.get(container)
            if isinstance(prev_container, Mapping) and isinstance(new_container, Mapping):
                for field in _NUMERIC_CEILING_FIELDS:
                    prev_value = prev_container.get(field)
                    new_value = new_container.get(field)
                    is_raised = (
                        _is_plain_int(prev_value)
                        and _is_plain_int(new_value)
                        and new_value > prev_value
                    )
                    if is_raised:
                        authority_expanded = True
                        reasons.append(
                            f"authority expanded: {container}.{field} raised from "
                            f"{prev_value} to {new_value}"
                        )

        for field in _EVIDENCE_LIST_FIELDS:
            lost = _as_str_set(prev_doc.get(field)) - _as_str_set(new_doc.get(field))
            if lost:
                evidence_weakened = True
                reasons.append(f"evidence weakened: {field} lost {sorted(lost)}")

        prev_retention = prev_doc.get("retention")
        new_retention = new_doc.get("retention")
        if isinstance(prev_retention, Mapping) and isinstance(new_retention, Mapping):
            prev_index = _ordinal_index(_RETENTION_ORDER, prev_retention.get("policy"))
            new_index = _ordinal_index(_RETENTION_ORDER, new_retention.get("policy"))
            if prev_index is not None and new_index is not None and new_index < prev_index:
                evidence_weakened = True
                reasons.append("evidence weakened: retention policy downgraded")

        prev_reviewer = prev_doc.get("reviewer_record")
        new_reviewer = new_doc.get("reviewer_record")
        if isinstance(prev_reviewer, Mapping) and prev_reviewer.get("verdict") == "PASS":
            new_verdict = new_reviewer.get("verdict") if isinstance(new_reviewer, Mapping) else None
            if new_verdict != "PASS":
                evidence_weakened = True
                reasons.append("evidence weakened: reviewer PASS verdict was removed or downgraded")

        for field in _PROTECTED_LIST_FIELDS:
            removed = _as_str_set(prev_doc.get(field)) - _as_str_set(new_doc.get(field))
            if removed:
                protected_boundary_crossed = True
                reasons.append(f"protected boundary crossed: {field} lost {sorted(removed)}")

        compatible, compatibility_reason = self._assess_compatibility(previous, proposed)
        if compatibility_reason:
            reasons.append(compatibility_reason)

        ownership_conflicts = tuple(
            contract_id
            for contract_id, linked_contract in linked.items()
            if linked_contract.contract_type is ContractType.OWNERSHIP
            and self._conflicts_with(proposed, linked_contract)
        )

        affected_components = tuple(sorted(linked.keys()))
        required_tests = ("integration", "regression") if affected_components else ()

        return ImpactResult(
            compatible=compatible,
            ownership_conflicts=ownership_conflicts,
            affected_components=affected_components,
            required_tests=required_tests,
            authority_expanded=authority_expanded,
            evidence_weakened=evidence_weakened,
            protected_boundary_crossed=protected_boundary_crossed,
            reasons=tuple(reasons),
        )

    def _assess_compatibility(
        self, previous: CanonicalContract, proposed: CanonicalContract
    ) -> tuple[bool, str | None]:
        prev_provided = _as_str_set(previous.document.get("interfaces_provided"))
        new_provided = _as_str_set(proposed.document.get("interfaces_provided"))
        prev_frozen = _as_str_set(previous.document.get("frozen_interfaces"))
        new_frozen = _as_str_set(proposed.document.get("frozen_interfaces"))

        if not prev_provided and not prev_frozen:
            return True, None

        removed_provided = prev_provided - new_provided
        removed_frozen = prev_frozen - new_frozen
        if removed_provided or removed_frozen:
            return False, "IMPACT_UNPROVEN: previously declared interfaces were removed"
        return True, None

    def _conflicts_with(self, proposed: CanonicalContract, ownership: CanonicalContract) -> bool:
        proposed_paths = _as_str_set(proposed.document.get("allowed_paths"))
        other_paths = _as_str_set(ownership.document.get("allowed_paths"))
        return bool(proposed_paths & other_paths)


def _is_plain_int(value: object) -> TypeGuard[int]:
    return isinstance(value, int) and not isinstance(value, bool)
