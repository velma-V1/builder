import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from factory.contracts.impact.analyzer import ImpactAnalyzer
from factory.contracts.models import CanonicalContract
from factory.contracts.service import ContractService
from factory.contracts.validation.schema_registry import SchemaRegistry

SCHEMA_ROOT = Path("schemas")
FIXTURES_ROOT = Path("tests/contracts/fixtures/valid")


def _load_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES_ROOT / name).read_text(encoding="utf-8"))


@pytest.fixture
def service() -> ContractService:
    return ContractService(SchemaRegistry.load(SCHEMA_ROOT))


@pytest.fixture
def analyzer() -> ImpactAnalyzer:
    return ImpactAnalyzer()


def _ingest(
    service: ContractService, tmp_path: Path, name: str, document: dict[str, Any]
) -> CanonicalContract:
    path = tmp_path / name
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return service.ingest(path)


def test_no_changes_produce_a_clean_impact_result(
    service: ContractService, analyzer: ImpactAnalyzer, tmp_path: Path
) -> None:
    document = _load_fixture("ownership.json")
    previous = _ingest(service, tmp_path, "prev.yaml", document)
    proposed = _ingest(service, tmp_path, "next.yaml", document)

    result = analyzer.compare(previous, proposed, linked={})
    assert result.compatible
    assert not result.authority_expanded
    assert not result.evidence_weakened
    assert not result.protected_boundary_crossed
    assert result.ownership_conflicts == ()
    assert result.affected_components == ()


def test_new_allowed_path_expands_authority(
    service: ContractService, analyzer: ImpactAnalyzer, tmp_path: Path
) -> None:
    previous_doc = _load_fixture("ownership.json")
    previous = _ingest(service, tmp_path, "prev.yaml", previous_doc)

    proposed_doc = dict(previous_doc)
    proposed_doc["allowed_paths"] = [*previous_doc["allowed_paths"], "docs/**"]
    proposed = _ingest(service, tmp_path, "next.yaml", proposed_doc)

    result = analyzer.compare(previous, proposed, linked={})
    assert result.authority_expanded
    assert any("allowed_paths" in reason for reason in result.reasons)


def test_removed_approval_requirement_expands_authority(
    service: ContractService, analyzer: ImpactAnalyzer, tmp_path: Path
) -> None:
    previous_doc = _load_fixture("permission.json")
    previous = _ingest(service, tmp_path, "prev.yaml", previous_doc)

    proposed_doc = dict(previous_doc)
    proposed_doc["approval_required"] = []
    proposed = _ingest(service, tmp_path, "next.yaml", proposed_doc)

    result = analyzer.compare(previous, proposed, linked={})
    assert result.authority_expanded
    assert any("approval_required" in reason for reason in result.reasons)


def test_network_privilege_escalation_expands_authority(
    service: ContractService, analyzer: ImpactAnalyzer, tmp_path: Path
) -> None:
    previous_doc = _load_fixture("permission.json")
    previous = _ingest(service, tmp_path, "prev.yaml", previous_doc)

    proposed_doc = dict(previous_doc)
    proposed_doc["network"] = "APPROVED_ROUTES_ONLY"
    proposed = _ingest(service, tmp_path, "next.yaml", proposed_doc)

    result = analyzer.compare(previous, proposed, linked={})
    assert result.authority_expanded
    assert any("network" in reason for reason in result.reasons)


def test_removed_test_command_weakens_evidence(
    service: ContractService, analyzer: ImpactAnalyzer, tmp_path: Path
) -> None:
    previous_doc = _load_fixture("evidence.json")
    previous_doc["test_commands"] = ["uv run pytest tests/contracts/unit", "uv run mypy src"]
    previous = _ingest(service, tmp_path, "prev.yaml", previous_doc)

    proposed_doc = dict(previous_doc)
    proposed_doc["test_commands"] = ["uv run pytest tests/contracts/unit"]
    proposed = _ingest(service, tmp_path, "next.yaml", proposed_doc)

    result = analyzer.compare(previous, proposed, linked={})
    assert result.evidence_weakened
    assert any("test_commands" in reason for reason in result.reasons)


def test_retention_downgrade_weakens_evidence(
    service: ContractService, analyzer: ImpactAnalyzer, tmp_path: Path
) -> None:
    previous_doc = _load_fixture("evidence.json")
    previous_doc["retention"] = {"policy": "PERMANENT"}
    previous = _ingest(service, tmp_path, "prev.yaml", previous_doc)

    proposed_doc = dict(previous_doc)
    proposed_doc["retention"] = {"policy": "STANDARD"}
    proposed = _ingest(service, tmp_path, "next.yaml", proposed_doc)

    result = analyzer.compare(previous, proposed, linked={})
    assert result.evidence_weakened
    assert any("retention" in reason for reason in result.reasons)


def test_removing_protected_branch_crosses_protected_boundary(
    service: ContractService, analyzer: ImpactAnalyzer, tmp_path: Path
) -> None:
    previous_doc = _load_fixture("project.json")
    previous_doc["protected_branches"] = ["main", "release"]
    previous = _ingest(service, tmp_path, "prev.yaml", previous_doc)

    proposed_doc = dict(previous_doc)
    proposed_doc["protected_branches"] = ["main"]
    proposed = _ingest(service, tmp_path, "next.yaml", proposed_doc)

    result = analyzer.compare(previous, proposed, linked={})
    assert result.protected_boundary_crossed


def test_removing_provided_interface_is_impact_unproven(
    service: ContractService, analyzer: ImpactAnalyzer, tmp_path: Path
) -> None:
    previous_doc = _load_fixture("ownership.json")
    previous_doc["interfaces_provided"] = ["ContractService.ingest", "SchemaRegistry.get"]
    previous = _ingest(service, tmp_path, "prev.yaml", previous_doc)

    proposed_doc = dict(previous_doc)
    proposed_doc["interfaces_provided"] = ["ContractService.ingest"]
    proposed = _ingest(service, tmp_path, "next.yaml", proposed_doc)

    result = analyzer.compare(previous, proposed, linked={})
    assert not result.compatible
    assert any("IMPACT_UNPROVEN" in reason for reason in result.reasons)


def test_ownership_conflict_detected_via_linked_contracts(
    service: ContractService, analyzer: ImpactAnalyzer, tmp_path: Path
) -> None:
    previous_doc = _load_fixture("ownership.json")
    previous = _ingest(service, tmp_path, "prev.yaml", previous_doc)
    proposed = _ingest(service, tmp_path, "next.yaml", previous_doc)

    other_ownership_doc = dict(previous_doc)
    other_ownership_doc["id"] = "OWN-002"
    other_ownership = _ingest(service, tmp_path, "other.yaml", other_ownership_doc)

    result = analyzer.compare(previous, proposed, linked={"OWN-002": other_ownership})
    assert "OWN-002" in result.ownership_conflicts
    assert result.affected_components == ("OWN-002",)
    assert result.required_tests == ("integration", "regression")
