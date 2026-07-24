import subprocess
import sys
from pathlib import Path

import pytest

from factory.contracts.errors import ContractError
from factory.contracts.models import ContractType, ErrorCode
from factory.contracts.service import ContractService
from factory.contracts.validation.schema_registry import SchemaRegistry

SCHEMA_ROOT = Path("schemas")
FIXTURES_ROOT = Path("tests/contracts/fixtures")


def _write_yaml_fixture(tmp_path: Path, json_fixture: Path, filename: str) -> Path:
    import json

    import yaml

    document = json.loads(json_fixture.read_text(encoding="utf-8"))
    target = tmp_path / filename
    target.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return target


@pytest.fixture
def service() -> ContractService:
    return ContractService(SchemaRegistry.load(SCHEMA_ROOT))


def test_ingest_valid_contract_returns_canonical_contract(
    service: ContractService, tmp_path: Path
) -> None:
    path = _write_yaml_fixture(tmp_path, FIXTURES_ROOT / "valid" / "project.json", "project.yaml")
    contract = service.ingest(path)

    assert contract.contract_type is ContractType.PROJECT
    assert contract.contract_id == "PROJ-001"
    assert contract.version == 1
    assert contract.project_id == "PROJ-001"
    assert contract.validation.valid
    assert len(contract.content_hash) == 64


def test_ingest_is_deterministic_regardless_of_key_order(
    service: ContractService, tmp_path: Path
) -> None:
    path_a = _write_yaml_fixture(tmp_path, FIXTURES_ROOT / "valid" / "task.json", "task_a.yaml")
    reordered = tmp_path / "task_b.yaml"
    text = path_a.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    reordered.write_text("".join(reversed(lines[:2])) + "".join(lines[2:]), encoding="utf-8")

    contract_a = service.ingest(path_a)
    contract_b = service.ingest(reordered)
    assert contract_a.content_hash == contract_b.content_hash


def test_ingest_invalid_contract_raises_with_issues(
    service: ContractService, tmp_path: Path
) -> None:
    path = _write_yaml_fixture(
        tmp_path,
        FIXTURES_ROOT / "invalid" / "project_missing_resource_ceilings.json",
        "invalid.yaml",
    )
    with pytest.raises(ContractError) as raised:
        service.ingest(path)
    assert raised.value.code is ErrorCode.SCHEMA_REJECTED
    assert raised.value.issues


def test_ingest_malicious_yaml_fails_closed(service: ContractService, tmp_path: Path) -> None:
    path = tmp_path / "malicious.yaml"
    path.write_text("value: !!python/object:os.system ['echo pwned']\n", encoding="utf-8")
    with pytest.raises(ContractError) as raised:
        service.ingest(path)
    assert raised.value.code is ErrorCode.PARSE_REJECTED


def test_ingest_oversized_file_is_rejected(service: ContractService, tmp_path: Path) -> None:
    path = tmp_path / "oversized.yaml"
    with path.open("w", encoding="utf-8") as handle:
        handle.write("value: |\n")
        handle.write("  " + ("a" * (1_048_576 + 100)) + "\n")
    with pytest.raises(ContractError) as raised:
        service.ingest(path)
    assert raised.value.code is ErrorCode.PARSE_REJECTED


def test_ingest_non_utf8_file_is_rejected(service: ContractService, tmp_path: Path) -> None:
    path = tmp_path / "binary.yaml"
    path.write_bytes(b"\xff\xfe\x00value")
    with pytest.raises(ContractError) as raised:
        service.ingest(path)
    assert raised.value.code is ErrorCode.PARSE_REJECTED


def test_validate_contracts_script_reports_pass_and_fail(tmp_path: Path) -> None:
    script = Path("scripts/validate_contracts.py").resolve()

    valid_dir = tmp_path / "contracts"
    valid_dir.mkdir()
    _write_yaml_fixture(valid_dir, FIXTURES_ROOT / "valid" / "project.json", "project.yaml")

    result = subprocess.run(  # noqa: S603
        [sys.executable, str(script), str(valid_dir)],
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    invalid_dir = tmp_path / "invalid"
    invalid_dir.mkdir()
    _write_yaml_fixture(
        invalid_dir, FIXTURES_ROOT / "invalid" / "requirement_bad_priority.json", "requirement.yaml"
    )
    result = subprocess.run(  # noqa: S603
        [sys.executable, str(script), str(invalid_dir)],
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
