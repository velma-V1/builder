import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from factory.contracts.models import CanonicalContract, ContractType, ErrorCode, ValidationReport
from factory.contracts.references.resolver import ReferenceResolver
from factory.contracts.repository.filesystem import ContractFileRepository
from factory.contracts.service import ContractService
from factory.contracts.validation.paths import PathAuthority
from factory.contracts.validation.schema_registry import SchemaRegistry
from factory.contracts.validation.semantic import SemanticValidator

SCHEMA_ROOT = Path("schemas")
FIXTURES_ROOT = Path("tests/contracts/fixtures/valid")

APPROVED_ROUTES = frozenset({"LOCAL_FAST", "LOCAL_SUPERVISOR"})


def _load_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES_ROOT / name).read_text(encoding="utf-8"))


@pytest.fixture
def repository(tmp_path: Path) -> ContractFileRepository:
    service = ContractService(SchemaRegistry.load(SCHEMA_ROOT))
    return ContractFileRepository(root=tmp_path, service=service)


@pytest.fixture
def resolver(repository: ContractFileRepository) -> ReferenceResolver:
    return ReferenceResolver(repository=repository)


@pytest.fixture
def validator(resolver: ReferenceResolver) -> SemanticValidator:
    return SemanticValidator(
        resolver=resolver,
        path_authority_factory=lambda root: PathAuthority(project_root=root),
        approved_routes=APPROVED_ROUTES,
    )


def _write(
    repository: ContractFileRepository, contract_type: ContractType, document: dict[str, Any]
) -> None:
    text = yaml.safe_dump(document, sort_keys=False)
    repository.create_version(
        contract_type, document["project_id"], document["id"], document["version"], text
    )


def _seed_full_task_set(repository: ContractFileRepository) -> None:
    _write(repository, ContractType.PROJECT, _load_fixture("project.json"))
    _write(repository, ContractType.REQUIREMENT, _load_fixture("requirement.json"))
    _write(repository, ContractType.OWNERSHIP, _load_fixture("ownership.json"))
    _write(repository, ContractType.PERMISSION, _load_fixture("permission.json"))
    _write(repository, ContractType.EVIDENCE, _load_fixture("evidence.json"))
    _write(repository, ContractType.TASK, _load_fixture("task.json"))


def test_valid_task_produces_no_semantic_issues(
    repository: ContractFileRepository, validator: SemanticValidator
) -> None:
    _seed_full_task_set(repository)
    task = repository.load(ContractType.TASK, "PROJ-001", "TASK-001", 1)
    report = validator.validate(task, active_ownership={})
    assert report.valid, report.issues


def test_unapproved_route_is_rejected(
    repository: ContractFileRepository, validator: SemanticValidator
) -> None:
    _write(repository, ContractType.PROJECT, _load_fixture("project.json"))
    _write(repository, ContractType.REQUIREMENT, _load_fixture("requirement.json"))
    _write(repository, ContractType.OWNERSHIP, _load_fixture("ownership.json"))
    _write(repository, ContractType.PERMISSION, _load_fixture("permission.json"))
    _write(repository, ContractType.EVIDENCE, _load_fixture("evidence.json"))
    task_doc = _load_fixture("task.json")
    task_doc["permitted_routes"] = ["LANE_1_WORKER"]
    _write(repository, ContractType.TASK, task_doc)

    task = repository.load(ContractType.TASK, "PROJ-001", "TASK-001", 1)
    report = validator.validate(task, active_ownership={})
    assert not report.valid
    assert any(issue.code is ErrorCode.SEMANTIC_REJECTED for issue in report.issues)


def test_resource_limits_exceeding_project_ceilings_are_rejected(
    repository: ContractFileRepository, validator: SemanticValidator
) -> None:
    _write(repository, ContractType.PROJECT, _load_fixture("project.json"))
    _write(repository, ContractType.REQUIREMENT, _load_fixture("requirement.json"))
    _write(repository, ContractType.OWNERSHIP, _load_fixture("ownership.json"))
    _write(repository, ContractType.PERMISSION, _load_fixture("permission.json"))
    _write(repository, ContractType.EVIDENCE, _load_fixture("evidence.json"))
    task_doc = _load_fixture("task.json")
    task_doc["resource_limits"]["max_tokens_per_task"] = 999_999_999
    _write(repository, ContractType.TASK, task_doc)

    task = repository.load(ContractType.TASK, "PROJ-001", "TASK-001", 1)
    report = validator.validate(task, active_ownership={})
    assert not report.valid
    assert any("ceiling" in issue.message for issue in report.issues)


def test_frozen_interface_not_provided_by_ownership_is_rejected(
    repository: ContractFileRepository, validator: SemanticValidator
) -> None:
    _write(repository, ContractType.PROJECT, _load_fixture("project.json"))
    _write(repository, ContractType.REQUIREMENT, _load_fixture("requirement.json"))
    _write(repository, ContractType.OWNERSHIP, _load_fixture("ownership.json"))
    _write(repository, ContractType.PERMISSION, _load_fixture("permission.json"))
    _write(repository, ContractType.EVIDENCE, _load_fixture("evidence.json"))
    task_doc = _load_fixture("task.json")
    task_doc["frozen_interfaces"] = ["NotProvided.method"]
    _write(repository, ContractType.TASK, task_doc)

    task = repository.load(ContractType.TASK, "PROJ-001", "TASK-001", 1)
    report = validator.validate(task, active_ownership={})
    assert not report.valid
    assert any("frozen interface" in issue.message for issue in report.issues)


def test_ownership_allowed_and_forbidden_conflict_is_rejected(
    repository: ContractFileRepository, validator: SemanticValidator
) -> None:
    _write(repository, ContractType.PROJECT, _load_fixture("project.json"))
    ownership_doc = _load_fixture("ownership.json")
    ownership_doc["forbidden_paths"] = list(ownership_doc["allowed_paths"])
    _write(repository, ContractType.OWNERSHIP, ownership_doc)

    ownership = repository.load(ContractType.OWNERSHIP, "PROJ-001", "OWN-001", 1)
    report = validator.validate(ownership, active_ownership={})
    assert not report.valid
    assert any(issue.code is ErrorCode.AUTHORITY_CONFLICT for issue in report.issues)


def test_ownership_conflicts_with_active_ownership(
    repository: ContractFileRepository, validator: SemanticValidator
) -> None:
    _write(repository, ContractType.PROJECT, _load_fixture("project.json"))
    _write(repository, ContractType.OWNERSHIP, _load_fixture("ownership.json"))

    ownership = repository.load(ContractType.OWNERSHIP, "PROJ-001", "OWN-001", 1)
    report = validator.validate(
        ownership, active_ownership={"OWN-999": ["src/factory/contracts/service.py"]}
    )
    assert not report.valid
    assert any(issue.code is ErrorCode.AUTHORITY_CONFLICT for issue in report.issues)


def test_evidence_category_not_reachable_from_requirement_is_rejected(
    repository: ContractFileRepository, validator: SemanticValidator
) -> None:
    _write(repository, ContractType.PROJECT, _load_fixture("project.json"))
    requirement_doc = _load_fixture("requirement.json")
    requirement_doc["evidence_categories"] = ["UNIT_TEST"]
    _write(repository, ContractType.REQUIREMENT, requirement_doc)

    evidence_doc = _load_fixture("evidence.json")
    evidence_doc["evidence_categories"] = ["SECURITY_TEST"]
    _write(repository, ContractType.EVIDENCE, evidence_doc)

    evidence = repository.load(ContractType.EVIDENCE, "PROJ-001", "EVID-001", 1)
    report = validator.validate(evidence, active_ownership={})
    assert not report.valid
    assert any("not reachable" in issue.message for issue in report.issues)


def test_missing_reference_produces_reference_rejected_issue(
    repository: ContractFileRepository, validator: SemanticValidator
) -> None:
    task_doc = _load_fixture("task.json")
    task_doc["parent_requirements"] = [{"id": "REQ-404", "version": 1}]
    _write(repository, ContractType.TASK, task_doc)

    task = repository.load(ContractType.TASK, "PROJ-001", "TASK-001", 1)
    report = validator.validate(task, active_ownership={})
    assert not report.valid
    assert any(issue.code is ErrorCode.REFERENCE_REJECTED for issue in report.issues)


def test_directly_authored_superseded_status_is_rejected(
    repository: ContractFileRepository, validator: SemanticValidator
) -> None:
    _seed_full_task_set(repository)
    task_doc = _load_fixture("task.json")
    task_doc["status"] = "SUPERSEDED"
    task_doc["version"] = 2
    _write(repository, ContractType.TASK, task_doc)

    task = repository.load(ContractType.TASK, "PROJ-001", "TASK-001", 2)
    report = validator.validate(task, active_ownership={})
    assert not report.valid
    assert any("cannot be directly authored" in issue.message for issue in report.issues)


def test_dependency_cycle_is_reported_through_validate(
    repository: ContractFileRepository, validator: SemanticValidator
) -> None:
    _seed_full_task_set(repository)
    task_b = _load_fixture("task.json")
    task_b["id"] = "TASK-002"
    task_b["dependencies"] = [{"id": "TASK-001", "version": 2}]
    _write(repository, ContractType.TASK, task_b)

    task_a = _load_fixture("task.json")
    task_a["version"] = 2
    task_a["dependencies"] = [{"id": "TASK-002", "version": 1}]
    _write(repository, ContractType.TASK, task_a)

    task = repository.load(ContractType.TASK, "PROJ-001", "TASK-001", 2)
    report = validator.validate(task, active_ownership={})
    assert not report.valid
    assert any("cycle" in issue.message.lower() for issue in report.issues)


def test_load_project_exception_is_treated_as_project_not_found(
    repository: ContractFileRepository, validator: SemanticValidator
) -> None:
    project_path = repository.path_for(ContractType.PROJECT, "PROJ-001", "PROJ-001", 1)
    project_path.parent.mkdir(parents=True)
    invalid_yaml = "id: PROJ-001\nid: duplicate-key-makes-this-invalid\n"
    project_path.write_text(invalid_yaml, encoding="utf-8")

    _write(repository, ContractType.REQUIREMENT, _load_fixture("requirement.json"))
    _write(repository, ContractType.OWNERSHIP, _load_fixture("ownership.json"))
    _write(repository, ContractType.PERMISSION, _load_fixture("permission.json"))
    _write(repository, ContractType.EVIDENCE, _load_fixture("evidence.json"))
    _write(repository, ContractType.TASK, _load_fixture("task.json"))

    task = repository.load(ContractType.TASK, "PROJ-001", "TASK-001", 1)
    # The project file exists but fails to ingest (malformed YAML), so project-dependent
    # checks (route/ceiling validation) must degrade gracefully rather than raising.
    report = validator.validate(task, active_ownership={})
    assert isinstance(report, ValidationReport)


def test_patterns_conflict_handles_reversed_wildcard_and_true_non_conflict(
    repository: ContractFileRepository, validator: SemanticValidator
) -> None:
    _write(repository, ContractType.PROJECT, _load_fixture("project.json"))
    _write(repository, ContractType.OWNERSHIP, _load_fixture("ownership.json"))
    ownership = repository.load(ContractType.OWNERSHIP, "PROJ-001", "OWN-001", 1)

    # The *other* ownership's pattern is the wildcard here (reversed from other tests),
    # covering the right-hand "**" branch of the unification matcher.
    conflicting_report = validator.validate(ownership, active_ownership={"OWN-999": ["src/**"]})
    assert not conflicting_report.valid

    non_conflicting_report = validator.validate(
        ownership, active_ownership={"OWN-999": ["docs/completely/unrelated/path.md"]}
    )
    conflict_issues = [
        issue
        for issue in non_conflicting_report.issues
        if issue.code is ErrorCode.AUTHORITY_CONFLICT and "active ownership" in issue.message
    ]
    assert conflict_issues == []


def _raw_task_contract(document: dict[str, Any]) -> CanonicalContract:
    return CanonicalContract(
        source_path=Path("TASK-001.yaml"),
        contract_type=ContractType.TASK,
        contract_id="TASK-001",
        version=1,
        schema_version="1.0",
        project_id="PROJ-001",
        canonical_bytes=b"{}",
        content_hash="0" * 64,
        document=document,
        validation=ValidationReport(valid=True, issues=()),
    )


def test_runtime_only_fields_are_rejected_when_present(
    repository: ContractFileRepository, validator: SemanticValidator
) -> None:
    task = _raw_task_contract({"generation": 1, "content_hash": "a" * 64})
    report = validator.validate(task, active_ownership={})
    assert not report.valid
    assert any("runtime-only field" in issue.message for issue in report.issues)


def test_task_validation_tolerates_malformed_field_types(
    repository: ContractFileRepository, validator: SemanticValidator
) -> None:
    task = _raw_task_contract(
        {
            "permitted_routes": "not-a-list",
            "resource_limits": "not-a-mapping",
            "ownership_contract": "not-a-mapping",
            "frozen_interfaces": "not-a-list",
        }
    )
    # None of these malformed shapes should raise; they should simply be skipped.
    report = validator.validate(task, active_ownership={})
    assert isinstance(report, ValidationReport)


def test_ownership_validation_tolerates_malformed_field_types(
    repository: ContractFileRepository, validator: SemanticValidator
) -> None:
    ownership = CanonicalContract(
        source_path=Path("OWN-001.yaml"),
        contract_type=ContractType.OWNERSHIP,
        contract_id="OWN-001",
        version=1,
        schema_version="1.0",
        project_id="PROJ-001",
        canonical_bytes=b"{}",
        content_hash="0" * 64,
        document={"allowed_paths": "not-a-list", "forbidden_paths": []},
        validation=ValidationReport(valid=True, issues=()),
    )
    report = validator.validate(ownership, active_ownership={})
    assert isinstance(report, ValidationReport)


def test_evidence_validation_tolerates_malformed_field_types_and_missing_requirement(
    repository: ContractFileRepository, validator: SemanticValidator
) -> None:
    evidence_missing_ref = CanonicalContract(
        source_path=Path("EVID-001.yaml"),
        contract_type=ContractType.EVIDENCE,
        contract_id="EVID-001",
        version=1,
        schema_version="1.0",
        project_id="PROJ-001",
        canonical_bytes=b"{}",
        content_hash="0" * 64,
        document={"requirement_ids": ["REQ-404"], "evidence_categories": "not-a-list"},
        validation=ValidationReport(valid=True, issues=()),
    )
    report = validator.validate(evidence_missing_ref, active_ownership={})
    assert not report.valid
    assert any("requirement not found" in issue.message for issue in report.issues)
