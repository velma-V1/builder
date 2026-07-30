import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from factory.contracts.impact.analyzer import ImpactAnalyzer
from factory.contracts.models import ContractType, PolicyOutcome
from factory.contracts.policy.engine import PolicyEngine
from factory.contracts.references.resolver import ReferenceResolver
from factory.contracts.repository.filesystem import ContractFileRepository
from factory.contracts.service import ChangeApplicationService, ContractService
from factory.contracts.validation.paths import PathAuthority
from factory.contracts.validation.schema_registry import SchemaRegistry
from factory.contracts.validation.semantic import SemanticValidator

pytestmark = pytest.mark.security

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
def change_service(repository: ContractFileRepository) -> ChangeApplicationService:
    resolver = ReferenceResolver(repository=repository)
    validator = SemanticValidator(
        resolver=resolver,
        path_authority_factory=lambda root: PathAuthority(project_root=root),
        approved_routes=APPROVED_ROUTES,
    )
    return ChangeApplicationService(
        repository=repository,
        semantic_validator=validator,
        impact_analyzer=ImpactAnalyzer(),
        policy_engine=PolicyEngine(),
    )


def _write(
    repository: ContractFileRepository, contract_type: ContractType, document: dict[str, Any]
) -> None:
    text = yaml.safe_dump(document, sort_keys=False)
    repository.create_version(
        contract_type, document["project_id"], document["id"], document["version"], text
    )


def _seed_evidence(repository: ContractFileRepository, **overrides: Any) -> None:
    _write(repository, ContractType.PROJECT, _load_fixture("project.json"))
    _write(repository, ContractType.REQUIREMENT, _load_fixture("requirement.json"))
    document = _load_fixture("evidence.json")
    document.update(overrides)
    _write(repository, ContractType.EVIDENCE, document)


def _ingest_change(repository: ContractFileRepository, operations: list[dict[str, Any]]):
    document = _load_fixture("change.json")
    document["target"] = {"id": "EVID-001", "version": 1}
    document["operations"] = operations
    document["resulting_version"] = 2
    path = repository.root.parent / "change.yaml"
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return repository.service.ingest(path)


def test_removing_a_required_test_command_requires_human_approval(
    repository: ContractFileRepository, change_service: ChangeApplicationService
) -> None:
    _seed_evidence(
        repository,
        test_commands=["uv run pytest tests/contracts/unit", "uv run mypy src"],
    )
    change = _ingest_change(
        repository,
        [
            {
                "op": "replace",
                "path": "/test_commands",
                "value": ["uv run pytest tests/contracts/unit"],
            }
        ],
    )

    result = change_service.apply(
        change,
        target_type=ContractType.EVIDENCE,
        active_ownership={},
        evidence_passed=True,
        rollback_available=True,
    )
    assert result.policy.outcome is PolicyOutcome.HUMAN_APPROVAL_REQUIRED
    assert result.impact.evidence_weakened


def test_downgrading_retention_policy_requires_human_approval(
    repository: ContractFileRepository, change_service: ChangeApplicationService
) -> None:
    _seed_evidence(repository, retention={"policy": "PERMANENT"})
    change = _ingest_change(
        repository, [{"op": "replace", "path": "/retention", "value": {"policy": "STANDARD"}}]
    )

    result = change_service.apply(
        change,
        target_type=ContractType.EVIDENCE,
        active_ownership={},
        evidence_passed=True,
        rollback_available=True,
    )
    assert result.policy.outcome is PolicyOutcome.HUMAN_APPROVAL_REQUIRED
    assert result.impact.evidence_weakened


def test_downgrading_a_passing_reviewer_verdict_requires_human_approval(
    repository: ContractFileRepository, change_service: ChangeApplicationService
) -> None:
    _seed_evidence(repository, reviewer_record={"verdict": "PASS"})
    change = _ingest_change(
        repository,
        [{"op": "replace", "path": "/reviewer_record", "value": {"verdict": "INCONCLUSIVE"}}],
    )

    result = change_service.apply(
        change,
        target_type=ContractType.EVIDENCE,
        active_ownership={},
        evidence_passed=True,
        rollback_available=True,
    )
    assert result.policy.outcome is PolicyOutcome.HUMAN_APPROVAL_REQUIRED
    assert result.impact.evidence_weakened


def test_widening_test_coverage_is_not_flagged_as_weakening(
    repository: ContractFileRepository, change_service: ChangeApplicationService
) -> None:
    _seed_evidence(repository, test_commands=["uv run pytest tests/contracts/unit"])
    change = _ingest_change(
        repository,
        [
            {
                "op": "replace",
                "path": "/test_commands",
                "value": [
                    "uv run pytest tests/contracts/unit",
                    "uv run pytest tests/contracts/security",
                ],
            }
        ],
    )

    result = change_service.apply(
        change,
        target_type=ContractType.EVIDENCE,
        active_ownership={},
        evidence_passed=True,
        rollback_available=True,
    )
    assert not result.impact.evidence_weakened
    assert result.policy.outcome is PolicyOutcome.ALLOW_WITH_CHECKPOINT
