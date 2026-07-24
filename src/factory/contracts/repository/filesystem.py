from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from factory.contracts.canonicalization.jcs import canonicalize
from factory.contracts.errors import ContractError
from factory.contracts.models import CanonicalContract, ContractType, ErrorCode
from factory.contracts.parsing.yaml_parser import YamlLimits, parse_yaml_contract
from factory.contracts.service import ContractService
from factory.contracts.validation.structural import StructuralValidator

_FAMILY_DIRS: dict[ContractType, str] = {
    ContractType.PROJECT: "projects",
    ContractType.REQUIREMENT: "requirements",
    ContractType.TASK: "tasks",
    ContractType.OWNERSHIP: "ownerships",
    ContractType.PERMISSION: "permissions",
    ContractType.EVIDENCE: "evidence",
    ContractType.CHANGE: "changes",
}

_VERSION_FILENAME = re.compile(r"^v(\d+)\.yaml$")


@dataclass(slots=True)
class ContractFileRepository:
    root: Path
    service: ContractService

    def path_for(
        self, contract_type: ContractType, project_id: str, contract_id: str, version: int
    ) -> Path:
        family = _FAMILY_DIRS[contract_type]
        return self.root / family / project_id / contract_id / f"v{version}.yaml"

    def load(
        self, contract_type: ContractType, project_id: str, contract_id: str, version: int
    ) -> CanonicalContract:
        path = self.path_for(contract_type, project_id, contract_id, version)
        if not path.is_file():
            raise ContractError(ErrorCode.REFERENCE_REJECTED, f"contract version not found: {path}")

        contract = self.service.ingest(path)
        identity_matches = (
            contract.contract_type is contract_type
            and contract.project_id == project_id
            and contract.contract_id == contract_id
            and contract.version == version
        )
        if not identity_matches:
            raise ContractError(
                ErrorCode.REFERENCE_REJECTED, f"contract identity mismatch at {path}"
            )
        return contract

    def list_versions(
        self, contract_type: ContractType, project_id: str, contract_id: str
    ) -> tuple[int, ...]:
        directory = self.path_for(contract_type, project_id, contract_id, 1).parent
        if not directory.is_dir():
            return ()
        versions = []
        for entry in directory.iterdir():
            match = _VERSION_FILENAME.match(entry.name)
            if match and entry.is_file():
                versions.append(int(match.group(1)))
        return tuple(sorted(versions))

    def create_version(
        self,
        contract_type: ContractType,
        project_id: str,
        contract_id: str,
        version: int,
        yaml_text: str,
    ) -> Path:
        limits = YamlLimits()
        if len(yaml_text.encode("utf-8")) > limits.max_bytes:
            raise ContractError(ErrorCode.PARSE_REJECTED, "contract text exceeds maximum size")

        document = parse_yaml_contract(yaml_text, limits)

        validator = StructuralValidator(self.service.schemas)
        validation = validator.validate(document)
        if not validation.valid:
            raise ContractError(
                ErrorCode.SCHEMA_REJECTED,
                "contract failed structural validation before write",
                issues=validation.issues,
            )

        identity_matches = (
            document.get("contract_type") == contract_type.value
            and document.get("project_id") == project_id
            and document.get("id") == contract_id
            and document.get("version") == version
        )
        if not identity_matches:
            raise ContractError(
                ErrorCode.REFERENCE_REJECTED,
                "contract envelope does not match the requested repository path identity",
            )

        canonicalize(document)  # validated for canonicalization compatibility before writing

        target = self.path_for(contract_type, project_id, contract_id, version)
        target.parent.mkdir(parents=True, exist_ok=True)

        try:
            with target.open("x", encoding="utf-8") as handle:
                handle.write(yaml_text)
                handle.flush()
                os.fsync(handle.fileno())
        except FileExistsError as exc:
            raise ContractError(
                ErrorCode.REFERENCE_REJECTED, f"contract version already exists: {target}"
            ) from exc

        return target
