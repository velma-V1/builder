from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from factory.contracts.errors import ContractError
from factory.contracts.models import CanonicalContract, ContractType, ErrorCode, JsonValue
from factory.contracts.repository.filesystem import ContractFileRepository

_TERMINAL_STATUSES = frozenset({"REJECTED", "RETIRED"})

# (expected referenced contract type, is the field a list of references)
_REFERENCE_FIELDS: dict[ContractType, dict[str, tuple[ContractType, bool]]] = {
    ContractType.TASK: {
        "parent_requirements": (ContractType.REQUIREMENT, True),
        "ownership_contract": (ContractType.OWNERSHIP, False),
        "permission_contract": (ContractType.PERMISSION, False),
        "evidence_contract": (ContractType.EVIDENCE, False),
        "dependencies": (ContractType.TASK, True),
    },
    ContractType.REQUIREMENT: {
        "dependencies": (ContractType.REQUIREMENT, True),
    },
}

_DEPENDENCY_FIELD = "dependencies"


def _contract_key(contract: CanonicalContract) -> str:
    return f"{contract.contract_type.value}:{contract.contract_id}:{contract.version}"


@dataclass(slots=True)
class ReferenceResolver:
    repository: ContractFileRepository

    def resolve(
        self,
        reference: Mapping[str, JsonValue],
        expected_type: ContractType,
        project_id: str,
    ) -> CanonicalContract:
        if not isinstance(reference, Mapping):
            raise ContractError(
                ErrorCode.REFERENCE_REJECTED, "reference must be a contract reference object"
            )
        contract_id = reference.get("id")
        version = reference.get("version")
        if not isinstance(contract_id, str) or not isinstance(version, int):
            raise ContractError(
                ErrorCode.REFERENCE_REJECTED,
                "reference must include a string id and an integer version",
            )

        contract = self.repository.load(expected_type, project_id, contract_id, version)

        status = contract.document.get("status")
        if status in _TERMINAL_STATUSES:
            raise ContractError(
                ErrorCode.REFERENCE_REJECTED,
                f"cannot reference a {status} contract version: {contract_id} v{version}",
            )
        return contract

    def resolve_all(self, contract: CanonicalContract) -> Mapping[str, CanonicalContract]:
        field_table = _REFERENCE_FIELDS.get(contract.contract_type, {})
        resolved: dict[str, CanonicalContract] = {}
        for field_name, (expected_type, is_list) in field_table.items():
            value = contract.document.get(field_name)
            if value is None:
                continue
            if is_list:
                if not isinstance(value, Sequence):
                    continue
                for index, item in enumerate(value):
                    if not isinstance(item, Mapping):
                        continue
                    resolved_contract = self.resolve(item, expected_type, contract.project_id)
                    key = f"{field_name}[{index}]:{resolved_contract.contract_id}"
                    resolved[key] = resolved_contract
            else:
                if not isinstance(value, Mapping):
                    continue
                resolved_contract = self.resolve(value, expected_type, contract.project_id)
                resolved[f"{field_name}:{resolved_contract.contract_id}"] = resolved_contract
        return resolved

    def resolve_dependency_graph(
        self, contract: CanonicalContract
    ) -> Mapping[str, CanonicalContract]:
        field_table = _REFERENCE_FIELDS.get(contract.contract_type, {})
        if _DEPENDENCY_FIELD not in field_table:
            return {}
        expected_type, _ = field_table[_DEPENDENCY_FIELD]

        resolved: dict[str, CanonicalContract] = {}
        visited: set[str] = set()
        visiting: list[str] = []

        def visit(current: CanonicalContract) -> None:
            current_key = _contract_key(current)
            if current_key in visiting:
                cycle_start = visiting.index(current_key)
                cycle_path = [*visiting[cycle_start:], current_key]
                raise ContractError(
                    ErrorCode.REFERENCE_REJECTED,
                    f"dependency cycle detected: {' -> '.join(cycle_path)}",
                )
            if current_key in visited:
                return

            visiting.append(current_key)
            dependencies = current.document.get(_DEPENDENCY_FIELD, [])
            if isinstance(dependencies, Sequence):
                for reference in dependencies:
                    if not isinstance(reference, Mapping):
                        continue
                    dependency = self.resolve(reference, expected_type, current.project_id)
                    resolved[_contract_key(dependency)] = dependency
                    visit(dependency)
            visiting.pop()
            visited.add(current_key)

        visit(contract)
        return resolved
