# Section 1 Requirements and Contracts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the complete Section 1 contract subsystem: seven linked YAML contract families, deterministic validation and canonicalization, semantic and impact checks, protected-boundary policy decisions, immutable revision flow, transactional activation metadata, and an immutable runtime cache.

**Architecture:** Git-tracked YAML files remain the editable source of approved intent. A Python contract service safely parses them, validates them against JSON Schema Draft 2020-12, performs semantic and impact checks, serializes them with RFC 8785, and submits eligible versions to a Watchdog-owned SQLite activation writer. Runtime consumers receive only immutable canonical JSON through a read-only cache and cannot directly mutate authoritative activation state.

**Tech Stack:** Python 3.12; uv; PyYAML 6.0.3; jsonschema 4.26.0; rfc8785 0.1.4; standard-library `sqlite3`; pytest 9.1.1; pytest-cov 7.1.0; Hypothesis 6.161.0; mypy 2.3.0; Ruff 0.15.22.

## Global Constraints

- Target Windows 11 Home, including the current unactivated development environment; no Pro-only Windows component may be required.
- Development commands must run in PowerShell and remain compatible with WSL2.
- Internet and cloud access are not required by Section 1 runtime or tests.
- YAML is the only human-edited contract representation; generated canonical JSON is never a competing source of truth.
- Activated YAML files are immutable. A revision creates a new version through a Change Contract.
- YAML `status` is immutable after activation. Supersession, disablement, rollback, and active generation are authoritative SQLite activation metadata.
- The Watchdog-owned activation service is the only writer to activation tables. Lanes and later dashboard processes receive read-only interfaces.
- Normal runtime reads do not parse YAML or run JSON Schema validation.
- Flexible intent fields may contain bounded natural language. Identity, authority, paths, permissions, resources, references, status, and completion fields remain strongly typed.
- Automatic work is allowed only when ownership, compatibility, reversibility, rollback, and required evidence are proven.
- Security violations are denied and audited, not converted into ordinary permission prompts.
- Existing source, test, schema, contract, decision, shared, protected, and user-authored files cannot be automatically deleted.
- Every task follows test-driven development and ends with an independently reviewable checkpoint commit.
- Full Section 1 verification requires `ruff`, strict `mypy`, all test categories, and at least 95% line coverage for `src/factory/contracts`.

## Locked File Map

```text
pyproject.toml
uv.lock
config/contracts/route-identities.yaml
contracts/.gitkeep
schemas/common/envelope-v1.schema.json
schemas/common/definitions-v1.schema.json
schemas/contracts/project/v1.schema.json
schemas/contracts/requirement/v1.schema.json
schemas/contracts/task/v1.schema.json
schemas/contracts/ownership/v1.schema.json
schemas/contracts/permission/v1.schema.json
schemas/contracts/evidence/v1.schema.json
schemas/contracts/change/v1.schema.json
migrations/contracts/0001_activation_store.sql
src/factory/__init__.py
src/factory/contracts/__init__.py
src/factory/contracts/errors.py
src/factory/contracts/models.py
src/factory/contracts/parsing/__init__.py
src/factory/contracts/parsing/yaml_parser.py
src/factory/contracts/validation/__init__.py
src/factory/contracts/validation/schema_registry.py
src/factory/contracts/validation/structural.py
src/factory/contracts/validation/semantic.py
src/factory/contracts/validation/paths.py
src/factory/contracts/canonicalization/__init__.py
src/factory/contracts/canonicalization/jcs.py
src/factory/contracts/repository/__init__.py
src/factory/contracts/repository/filesystem.py
src/factory/contracts/references/__init__.py
src/factory/contracts/references/resolver.py
src/factory/contracts/impact/__init__.py
src/factory/contracts/impact/analyzer.py
src/factory/contracts/policy/__init__.py
src/factory/contracts/policy/engine.py
src/factory/contracts/activation/__init__.py
src/factory/contracts/activation/store.py
src/factory/contracts/activation/service.py
src/factory/contracts/cache/__init__.py
src/factory/contracts/cache/runtime_cache.py
src/factory/contracts/service.py
scripts/validate_contracts.py
scripts/verify_section1.py
tests/contracts/conftest.py
tests/contracts/unit/
tests/contracts/integration/
tests/contracts/security/
tests/contracts/failure_paths/
tests/contracts/fixtures/valid/
tests/contracts/fixtures/invalid/
docs/verification/section-1-requirements-contracts.md
```

## Public Interfaces

```python
# src/factory/contracts/models.py
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, Sequence

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
```

---

### Task 1: Package Foundation, Common Envelope, and Seven Schemas

**Files:**
- Create: `pyproject.toml`
- Create: `uv.lock`
- Create: `src/factory/__init__.py`
- Create: `src/factory/contracts/__init__.py`
- Create: `src/factory/contracts/errors.py`
- Create: `src/factory/contracts/models.py`
- Create: `schemas/common/envelope-v1.schema.json`
- Create: `schemas/common/definitions-v1.schema.json`
- Create: seven files under `schemas/contracts/*/v1.schema.json`
- Create: `config/contracts/route-identities.yaml`
- Create: valid and invalid schema fixtures under `tests/contracts/fixtures/`
- Test: `tests/contracts/unit/test_schema_registry.py`
- Test: `tests/contracts/unit/test_contract_schemas.py`

**Interfaces:**
- Consumes: Approved Section 1 design.
- Produces: enums and frozen result types from `models.py`; Draft 2020-12 schemas identified by `(contract_type, schema_version)`; abstract route registry.

- [ ] **Step 1: Create the pinned Python project and development configuration**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["hatchling==1.27.0"]
build-backend = "hatchling.build"

[project]
name = "factory-builder"
version = "0.1.0"
description = "Deterministic local-first AI software factory"
requires-python = ">=3.12,<3.15"
dependencies = [
  "PyYAML==6.0.3",
  "jsonschema==4.26.0",
  "rfc8785==0.1.4",
]

[dependency-groups]
dev = [
  "hypothesis==6.161.0",
  "mypy==2.3.0",
  "pytest==9.1.1",
  "pytest-cov==7.1.0",
  "ruff==0.15.22",
]

[tool.hatch.build.targets.wheel]
packages = ["src/factory"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra --strict-markers --strict-config"
markers = [
  "security: adversarial security behavior",
  "failure_path: controlled failure and rollback behavior",
  "windows: Windows-specific path behavior",
]

[tool.coverage.run]
branch = true
source = ["src/factory/contracts"]

[tool.coverage.report]
fail_under = 95
show_missing = true
skip_covered = true

[tool.mypy]
python_version = "3.12"
strict = true
packages = ["factory.contracts"]
warn_unreachable = true

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "SIM", "S", "RUF"]
ignore = ["S101"]
```

Run:

```powershell
uv lock
uv sync --frozen
```

Expected: `uv.lock` is created; the environment resolves without dependency conflicts.

- [ ] **Step 2: Write failing tests for common identifiers and schema registration**

Create `tests/contracts/unit/test_schema_registry.py`:

```python
from pathlib import Path

import pytest

from factory.contracts.models import ContractType
from factory.contracts.validation.schema_registry import SchemaRegistry

SCHEMA_ROOT = Path("schemas")


def test_registry_loads_every_contract_schema() -> None:
    registry = SchemaRegistry.load(SCHEMA_ROOT)
    for contract_type in ContractType:
        schema = registry.get(contract_type, "1.0")
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_registry_rejects_unsupported_schema_version() -> None:
    registry = SchemaRegistry.load(SCHEMA_ROOT)
    with pytest.raises(KeyError, match="unsupported schema"):
        registry.get(ContractType.TASK, "999.0")
```

Run:

```powershell
uv run pytest tests/contracts/unit/test_schema_registry.py -v
```

Expected: collection fails because `SchemaRegistry` does not exist.

- [ ] **Step 3: Implement immutable common models and typed errors**

Create `src/factory/contracts/models.py` using the complete public-interface block above.

Create `src/factory/contracts/errors.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from factory.contracts.models import ErrorCode, ValidationIssue


@dataclass(frozen=True, slots=True)
class ContractError(Exception):
    code: ErrorCode
    message: str
    issues: tuple[ValidationIssue, ...] = ()

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"
```

Export only read-safe types from `src/factory/contracts/__init__.py`:

```python
from factory.contracts.models import (
    ActivationRecord,
    CacheEntry,
    CanonicalContract,
    ContractStatus,
    ContractType,
    ErrorCode,
    ImpactResult,
    PolicyDecision,
    PolicyOutcome,
    ValidationIssue,
    ValidationReport,
)

__all__ = [
    "ActivationRecord",
    "CacheEntry",
    "CanonicalContract",
    "ContractStatus",
    "ContractType",
    "ErrorCode",
    "ImpactResult",
    "PolicyDecision",
    "PolicyOutcome",
    "ValidationIssue",
    "ValidationReport",
]
```

- [ ] **Step 4: Create strict common JSON Schema definitions**

`schemas/common/definitions-v1.schema.json` must define:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://factory.local/schemas/common/definitions-v1.schema.json",
  "$defs": {
    "schemaVersion": {"const": "1.0"},
    "contractVersion": {"type": "integer", "minimum": 1, "maximum": 2147483647},
    "projectId": {"type": "string", "pattern": "^PROJ-[A-Z0-9][A-Z0-9-]{1,62}$"},
    "requirementId": {"type": "string", "pattern": "^REQ-[A-Z0-9][A-Z0-9-]{1,62}$"},
    "taskId": {"type": "string", "pattern": "^TASK-[A-Z0-9][A-Z0-9-]{1,62}$"},
    "ownershipId": {"type": "string", "pattern": "^OWN-[A-Z0-9][A-Z0-9-]{1,62}$"},
    "permissionId": {"type": "string", "pattern": "^PERM-[A-Z0-9][A-Z0-9-]{1,62}$"},
    "evidenceId": {"type": "string", "pattern": "^EVID-[A-Z0-9][A-Z0-9-]{1,62}$"},
    "changeId": {"type": "string", "pattern": "^CHG-[A-Z0-9][A-Z0-9-]{1,62}$"},
    "status": {
      "enum": ["DRAFT", "VALIDATED", "APPROVAL_REQUIRED", "APPROVED", "SUPERSEDED", "REJECTED", "RETIRED"]
    },
    "routeIdentity": {
      "enum": [
        "LANE_1_WORKER", "LANE_1_REVIEWER",
        "LANE_2_WORKER", "LANE_2_REVIEWER",
        "LANE_3_WORKER", "LANE_3_REVIEWER",
        "LOCAL_FAST", "LOCAL_SUPERVISOR"
      ]
    },
    "repoPath": {
      "type": "string",
      "minLength": 1,
      "maxLength": 512,
      "pattern": "^(?![A-Za-z]:)(?!/)(?!.*(?:^|/)\\.\\.(?:/|$))[^\\u0000]+$"
    },
    "contractRef": {
      "type": "object",
      "additionalProperties": false,
      "required": ["id", "version"],
      "properties": {
        "id": {"type": "string", "minLength": 3, "maxLength": 67},
        "version": {"$ref": "#/$defs/contractVersion"}
      }
    }
  }
}
```

`schemas/common/envelope-v1.schema.json` must require `contract_type`, `id`, `version`, `schema_version`, `project_id`, `status`, `source`, `created_at`, `created_by`, and `related_contracts`; reject unknown envelope keys; and expose the envelope through `$defs.envelope` for each contract schema.

- [ ] **Step 5: Create all seven schemas with strict authority and flexible bounded intent**

Each schema must:

1. use Draft 2020-12;
2. set a stable `$id` under `https://factory.local/schemas/contracts/<type>/v1.schema.json`;
3. set `additionalProperties: false` at every authority-bearing object;
4. require the common envelope;
5. permit `intent`, `notes`, `rationale`, and human-readable acceptance text as strings capped at 64 KiB each;
6. use integer ceilings for tokens, requests, retries, time, and file counts;
7. use abstract route identities only;
8. prohibit runtime `generation`, `content_hash`, `lane_id`, and `current_model` fields.

Create schema-specific required fields exactly as follows:

| Schema | Required body fields |
|---|---|
| Project | `name`, `project_root`, `repository`, `project_type`, `deliverables`, `goals`, `exclusions`, `operating_environments`, `protected_branches`, `protected_path_classes`, `privacy`, `resource_ceilings` |
| Requirement | `statement`, `rationale`, `acceptance_criteria`, `dependencies`, `priority`, `criticality`, `evidence_categories`, `permitted_limitations`, `supersession` |
| Task | `parent_requirements`, `objective`, `deliverables`, `ownership_contract`, `permission_contract`, `evidence_contract`, `frozen_interfaces`, `dependencies`, `permitted_routes`, `resource_limits`, `environment_class`, `checkpoint_policy`, `recovery_policy`, `completion_conditions` |
| Ownership | `task_id`, `allowed_paths`, `forbidden_paths`, `protected_classes`, `read_only_paths`, `interfaces_consumed`, `interfaces_provided`, `generated_artifacts`, `disposable_artifacts`, `overlap_policy`, `lease_required`, `path_policy` |
| Permission | `task_id`, `tools`, `command_classes`, `network`, `cloud`, `secrets`, `devices`, `processes`, `mounts`, `environment`, `file_operations`, `dependency_installation`, `approval_required`, `denied`, `expires_at`, `revocation` |
| Evidence | `task_id`, `requirement_ids`, `deliverables`, `test_commands`, `environment_identity`, `scope_checks`, `evidence_categories`, `worker_record`, `reviewer_record`, `artifacts`, `retention`, `completion_formula`, `permitted_limitations` |
| Change | `target`, `reason`, `operations`, `affected_requirements`, `affected_tasks`, `affected_paths`, `affected_interfaces`, `affected_permissions`, `affected_tests`, `affected_components`, `compatibility`, `protected_boundary`, `impact_result`, `required_evidence`, `rollback_target`, `approval`, `resulting_version` |

The Change schema supports only these deterministic patch operations:

```json
{
  "type": "array",
  "minItems": 1,
  "maxItems": 256,
  "items": {
    "type": "object",
    "additionalProperties": false,
    "required": ["op", "path"],
    "properties": {
      "op": {"enum": ["add", "replace", "remove"]},
      "path": {"type": "string", "pattern": "^/(?:[^~/]|~0|~1)+(?:/(?:[^~/]|~0|~1)+)*$"},
      "value": {}
    },
    "allOf": [
      {
        "if": {"properties": {"op": {"enum": ["add", "replace"]}}},
        "then": {"required": ["value"]}
      },
      {
        "if": {"properties": {"op": {"const": "remove"}}},
        "then": {"not": {"required": ["value"]}}
      }
    ]
  }
}
```

- [ ] **Step 6: Add abstract route registry**

Create `config/contracts/route-identities.yaml`:

```yaml
schema_version: "1.0"
routes:
  LANE_1_WORKER: {provider_lane: LANE_1, role: WORKER, cloud: true}
  LANE_1_REVIEWER: {provider_lane: LANE_1, role: REVIEWER, cloud: true}
  LANE_2_WORKER: {provider_lane: LANE_2, role: WORKER, cloud: true}
  LANE_2_REVIEWER: {provider_lane: LANE_2, role: REVIEWER, cloud: true}
  LANE_3_WORKER: {provider_lane: LANE_3, role: WORKER, cloud: true}
  LANE_3_REVIEWER: {provider_lane: LANE_3, role: REVIEWER, cloud: true}
  LOCAL_FAST: {provider_lane: LOCAL, role: WORKER, cloud: false}
  LOCAL_SUPERVISOR: {provider_lane: LOCAL, role: REVIEWER, cloud: false}
```

- [ ] **Step 7: Implement the schema registry and run schema tests**

Create `src/factory/contracts/validation/schema_registry.py` with:

```python
@dataclass(frozen=True, slots=True)
class SchemaRegistry:
    _schemas: Mapping[tuple[ContractType, str], Mapping[str, object]]

    @classmethod
    def load(cls, schema_root: Path) -> "SchemaRegistry": ...

    def get(self, contract_type: ContractType, schema_version: str) -> Mapping[str, object]: ...
```

Implementation requirements:

- load only `schemas/contracts/*/v1.schema.json` and common resources;
- call `Draft202012Validator.check_schema` for every schema;
- build one `referencing.Registry` containing every stable `$id` resource;
- return read-only mappings;
- fail startup on duplicate `$id`, unsupported draft, malformed schema, or missing contract family.

Run:

```powershell
uv run pytest tests/contracts/unit/test_schema_registry.py tests/contracts/unit/test_contract_schemas.py -v
uv run ruff check src tests
uv run mypy src/factory/contracts
```

Expected: all Task 1 tests pass; Ruff and mypy report no errors.

- [ ] **Step 8: Commit Task 1**

```powershell
git add pyproject.toml uv.lock config schemas src/factory tests/contracts/fixtures tests/contracts/unit
git commit -m "feat: define Factory contract schemas"
```

---

### Task 2: Safe YAML Ingestion, Structural Validation, Canonical JSON, and Hashing

**Files:**
- Create: `src/factory/contracts/parsing/yaml_parser.py`
- Create: `src/factory/contracts/validation/structural.py`
- Create: `src/factory/contracts/canonicalization/jcs.py`
- Create: `src/factory/contracts/service.py`
- Create: `scripts/validate_contracts.py`
- Test: `tests/contracts/unit/test_yaml_parser.py`
- Test: `tests/contracts/unit/test_structural_validation.py`
- Test: `tests/contracts/unit/test_canonicalization.py`
- Test: `tests/contracts/security/test_yaml_attacks.py`
- Test: `tests/contracts/integration/test_ingestion.py`

**Interfaces:**
- Consumes: `SchemaRegistry`, common models, seven schemas.
- Produces: `parse_yaml_contract(text, limits)`, `StructuralValidator.validate(document)`, `canonicalize(document)`, `ContractService.ingest(path)`.

- [ ] **Step 1: Write adversarial parser tests first**

Tests must cover:

- duplicate keys;
- `!!python/object` and every non-standard tag;
- more than 32 aliases;
- more than 10,000 parsed nodes;
- nesting deeper than 64 levels;
- input larger than 1 MiB;
- non-string mapping keys;
- YAML 1.1 surprise booleans (`yes`, `no`, `on`, `off`) remaining strings;
- only lowercase or uppercase `true` and `false` becoming booleans;
- `.nan`, `.inf`, and `-.inf` rejection;
- timestamps remaining strings;
- null bytes rejection.

Example failing test:

```python
import pytest

from factory.contracts.errors import ContractError
from factory.contracts.models import ErrorCode
from factory.contracts.parsing.yaml_parser import YamlLimits, parse_yaml_contract


def test_duplicate_keys_fail_closed() -> None:
    with pytest.raises(ContractError) as raised:
        parse_yaml_contract("id: TASK-1\nid: TASK-2\n", YamlLimits())
    assert raised.value.code is ErrorCode.PARSE_REJECTED
    assert "duplicate key" in raised.value.message.lower()
```

Run:

```powershell
uv run pytest tests/contracts/unit/test_yaml_parser.py tests/contracts/security/test_yaml_attacks.py -v
```

Expected: import or assertion failures because the parser is not implemented.

- [ ] **Step 2: Implement bounded safe YAML parsing**

Create:

```python
@dataclass(frozen=True, slots=True)
class YamlLimits:
    max_bytes: int = 1_048_576
    max_aliases: int = 32
    max_depth: int = 64
    max_nodes: int = 10_000
    max_scalar_length: int = 65_536


def parse_yaml_contract(text: str, limits: YamlLimits = YamlLimits()) -> dict[str, JsonValue]: ...
```

Implementation requirements:

- UTF-8 text only; reject NUL;
- pre-scan `yaml.parse` events to count aliases, nesting, nodes, and scalar lengths before construction;
- subclass `SafeLoader`;
- reject duplicate keys in a custom mapping constructor;
- remove Python object constructors and timestamp implicit resolver;
- replace the YAML 1.1 boolean resolver with `^(?:true|false|True|False|TRUE|FALSE)$`;
- permit only standard null, bool, int, float, string, sequence, and mapping tags;
- reject non-finite floats and non-string mapping keys;
- return plain dict/list/scalar values only.

- [ ] **Step 3: Write and implement structural validation**

Create:

```python
@dataclass(frozen=True, slots=True)
class StructuralValidator:
    registry: SchemaRegistry

    def validate(self, document: Mapping[str, JsonValue]) -> ValidationReport: ...
```

Required behavior:

- identify schema by `contract_type` and `schema_version` only after minimal envelope type checks;
- use `Draft202012Validator.iter_errors` with the loaded resource registry;
- sort issues deterministically by JSON Pointer then message;
- convert all failures into `ValidationIssue(ErrorCode.SCHEMA_REJECTED, pointer, message)`;
- reject unknown authority fields through schemas;
- never mutate input.

- [ ] **Step 4: Write deterministic canonicalization tests**

Tests must prove:

- key order, YAML comments, and whitespace do not change bytes or hash;
- Unicode and escaped strings produce stable RFC 8785 output;
- non-string dictionary keys are rejected before canonicalization;
- non-finite floats are rejected;
- SHA-256 is lowercase 64-character hexadecimal;
- canonicalization is deterministic across 1,000 Hypothesis-generated JSON-compatible documents within approved limits.

Example:

```python
from factory.contracts.canonicalization.jcs import canonicalize


def test_key_order_does_not_change_identity() -> None:
    left = canonicalize({"b": 2, "a": 1})
    right = canonicalize({"a": 1, "b": 2})
    assert left.canonical_bytes == right.canonical_bytes
    assert left.content_hash == right.content_hash
```

- [ ] **Step 5: Implement RFC 8785 serialization and hashing**

Create:

```python
@dataclass(frozen=True, slots=True)
class Canonicalized:
    canonical_bytes: bytes
    content_hash: str
    document: Mapping[str, JsonValue]


def canonicalize(document: Mapping[str, JsonValue]) -> Canonicalized: ...
```

Use `rfc8785.dumps`, `hashlib.sha256`, and recursive `MappingProxyType`/tuple freezing for runtime data. Preserve canonical bytes separately because tuples are not JSON values.

- [ ] **Step 6: Implement the ingestion façade**

Create `ContractService.ingest`:

```python
@dataclass(slots=True)
class ContractService:
    schemas: SchemaRegistry

    def ingest(self, source_path: Path) -> CanonicalContract: ...
```

Flow:

1. read at most 1 MiB plus one byte and reject oversize input;
2. parse safely;
3. structurally validate;
4. canonicalize;
5. return `CanonicalContract` only when valid;
6. otherwise raise `ContractError` with deterministic issues.

Create `scripts/validate_contracts.py` accepting one or more file or directory paths and returning exit code `0` only when every discovered `.yaml` contract passes ingestion.

- [ ] **Step 7: Run Task 2 verification**

```powershell
uv run pytest tests/contracts/unit/test_yaml_parser.py tests/contracts/unit/test_structural_validation.py tests/contracts/unit/test_canonicalization.py tests/contracts/security/test_yaml_attacks.py tests/contracts/integration/test_ingestion.py -v
uv run ruff check src tests scripts
uv run mypy src/factory/contracts
```

Expected: every Task 2 test passes; invalid and malicious YAML fail closed; static checks pass.

- [ ] **Step 8: Commit Task 2**

```powershell
git add src/factory/contracts/parsing src/factory/contracts/validation/structural.py src/factory/contracts/canonicalization src/factory/contracts/service.py scripts/validate_contracts.py tests/contracts
git commit -m "feat: add safe contract ingestion"
```

---

### Task 3: Filesystem Repository, References, Semantic Validation, Paths, and Impact

**Files:**
- Create: `src/factory/contracts/repository/filesystem.py`
- Create: `src/factory/contracts/references/resolver.py`
- Create: `src/factory/contracts/validation/semantic.py`
- Create: `src/factory/contracts/validation/paths.py`
- Create: `src/factory/contracts/impact/analyzer.py`
- Create: `contracts/.gitkeep`
- Test: `tests/contracts/unit/test_filesystem_repository.py`
- Test: `tests/contracts/unit/test_reference_resolver.py`
- Test: `tests/contracts/unit/test_semantic_validation.py`
- Test: `tests/contracts/unit/test_path_authority.py`
- Test: `tests/contracts/unit/test_impact_analyzer.py`
- Test: `tests/contracts/security/test_path_attacks.py`
- Test: `tests/contracts/integration/test_linked_contract_set.py`

**Interfaces:**
- Consumes: `CanonicalContract`, abstract route registry, project contracts, active ownership snapshot supplied as data.
- Produces: `ContractFileRepository`, `ReferenceResolver`, `SemanticValidator`, `PathAuthority`, `ImpactAnalyzer`.

- [ ] **Step 1: Lock the immutable repository naming convention**

Contract path:

```text
contracts/<family>/<project_id>/<contract_id>/v<version>.yaml
```

Examples:

```text
contracts/projects/PROJ-001/PROJ-001/v1.yaml
contracts/tasks/PROJ-001/TASK-042/v3.yaml
contracts/changes/PROJ-001/CHG-009/v1.yaml
```

Create:

```python
@dataclass(slots=True)
class ContractFileRepository:
    root: Path
    service: ContractService

    def path_for(self, contract_type: ContractType, project_id: str, contract_id: str, version: int) -> Path: ...
    def load(self, contract_type: ContractType, project_id: str, contract_id: str, version: int) -> CanonicalContract: ...
    def list_versions(self, contract_type: ContractType, project_id: str, contract_id: str) -> tuple[int, ...]: ...
    def create_version(self, contract_type: ContractType, project_id: str, contract_id: str, version: int, yaml_text: str) -> Path: ...
```

`create_version` uses exclusive file creation (`"x"` mode), validates before writing, verifies envelope/path identity, creates parent directories, fsyncs the file, and never overwrites an existing version.

- [ ] **Step 2: Write Windows path-security tests**

Tests must cover:

- `..` traversal;
- absolute POSIX and Windows paths;
- sibling-prefix bypass (`C:\Factory-Evil` versus `C:\Factory`);
- mixed separators;
- case differences;
- trailing spaces and dots;
- NTFS alternate data stream syntax (`file.txt:stream`);
- reserved device names (`CON`, `PRN`, `AUX`, `NUL`, `COM1` through `COM9`, `LPT1` through `LPT9`);
- symlink escape on platforms where supported;
- junction/reparse-point escape on Windows when test privileges permit, otherwise a separately classified skip with a deterministic pure resolver test;
- nonexistent child under a symlinked or junction parent;
- allowed path not overriding forbidden or protected path;
- read-only path denying write;
- active exclusive ownership denying concurrent write.

- [ ] **Step 3: Implement path normalization and authority decisions**

Create:

```python
@dataclass(frozen=True, slots=True)
class PathAuthorityResult:
    allowed: bool
    normalized_relative: str
    resolved_path: Path
    reason: str
    requires_serialization: bool


@dataclass(slots=True)
class PathAuthority:
    project_root: Path

    def evaluate(
        self,
        candidate: str,
        *,
        operation: str,
        allowed: Sequence[str],
        forbidden: Sequence[str],
        read_only: Sequence[str],
        active_exclusive_paths: Sequence[str],
    ) -> PathAuthorityResult: ...

    def revalidate_before_use(self, previous: PathAuthorityResult) -> None: ...
```

Implementation requirements:

- compare containment with `os.path.commonpath`, never `startswith`;
- resolve the nearest existing ancestor before appending nonexistent children;
- apply `os.path.normcase` on Windows;
- reject ADS and reserved device components;
- convert accepted relative paths to forward-slash form;
- compile contract globs with explicit semantics: `*` matches one segment portion; `**` matches zero or more segments;
- forbidden/protected/read-only rules take precedence;
- preserve enough resolved-parent identity for immediate pre-use revalidation to reduce TOCTOU gaps.

- [ ] **Step 4: Implement cross-contract reference resolution**

Create:

```python
@dataclass(slots=True)
class ReferenceResolver:
    repository: ContractFileRepository

    def resolve(self, reference: Mapping[str, JsonValue], expected_type: ContractType, project_id: str) -> CanonicalContract: ...
    def resolve_all(self, contract: CanonicalContract) -> Mapping[str, CanonicalContract]: ...
```

Verify exact ID, version, type, same-project requirement, supersession legality, and missing references. Build dependency graphs and reject requirement/task cycles using deterministic depth-first search with the cycle path included in the issue.

- [ ] **Step 5: Implement semantic validation**

Create:

```python
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
    ) -> ValidationReport: ...
```

It must validate:

- all references;
- same-project ownership;
- legal version and supersession relationships;
- route identities;
- cloud route permission against project and task privacy;
- resource limits against project ceilings;
- path authority and ownership conflicts;
- frozen interface references;
- evidence command and category reachability;
- legal authored status transitions;
- no runtime-only fields.

- [ ] **Step 6: Implement deterministic impact analysis**

Create:

```python
@dataclass(slots=True)
class ImpactAnalyzer:
    def compare(
        self,
        previous: CanonicalContract,
        proposed: CanonicalContract,
        linked: Mapping[str, CanonicalContract],
    ) -> ImpactResult: ...
```

Rules:

- authority expansion is true when allowed paths, commands, tools, routes, network, cloud, secrets, mounts, processes, resources, retries, time, or file limits become broader;
- evidence weakening is true when required tests, evidence categories, retention, reviewer records, failure-path checks, security checks, or completion clauses are removed or reduced;
- compatible interface changes require identical or additive signatures declared by contract; unknown compatibility becomes `IMPACT_UNPROVEN`;
- cross-component impact produces affected component IDs and required integration/regression evidence rather than immediately requiring human approval;
- removal operations against protected or pre-existing categories set `protected_boundary_crossed`.

- [ ] **Step 7: Run Task 3 verification**

```powershell
uv run pytest tests/contracts/unit/test_filesystem_repository.py tests/contracts/unit/test_reference_resolver.py tests/contracts/unit/test_semantic_validation.py tests/contracts/unit/test_path_authority.py tests/contracts/unit/test_impact_analyzer.py tests/contracts/security/test_path_attacks.py tests/contracts/integration/test_linked_contract_set.py -v
uv run ruff check src tests
uv run mypy src/factory/contracts
```

Expected: all tests pass; every path and reference attack fails closed or enters deterministic serialization handling.

- [ ] **Step 8: Commit Task 3**

```powershell
git add contracts src/factory/contracts/repository src/factory/contracts/references src/factory/contracts/validation src/factory/contracts/impact tests/contracts
git commit -m "feat: validate linked contract authority"
```

---

### Task 4: Change Application, Policy Decisions, SQLite Activation, Rollback, and Immutable Cache

**Files:**
- Create: `src/factory/contracts/policy/engine.py`
- Create: `src/factory/contracts/activation/store.py`
- Create: `src/factory/contracts/activation/service.py`
- Create: `src/factory/contracts/cache/runtime_cache.py`
- Create: `migrations/contracts/0001_activation_store.sql`
- Modify: `src/factory/contracts/service.py`
- Test: `tests/contracts/unit/test_policy_engine.py`
- Test: `tests/contracts/unit/test_change_application.py`
- Test: `tests/contracts/unit/test_runtime_cache.py`
- Test: `tests/contracts/integration/test_activation_store.py`
- Test: `tests/contracts/integration/test_activation_flow.py`
- Test: `tests/contracts/failure_paths/test_activation_rollback.py`
- Test: `tests/contracts/security/test_read_only_activation_access.py`
- Test: `tests/contracts/security/test_deletion_policy.py`

**Interfaces:**
- Consumes: validated contract set, `ImpactResult`, evidence result, optional approval record.
- Produces: `PolicyEngine.decide`, `ChangeApplicationService.apply`, Watchdog-only `ActivationService`, public `ActivationReader`, `RuntimeContractCache`.

- [ ] **Step 1: Write policy matrix tests before implementation**

Required outcomes:

| Condition | Outcome |
|---|---|
| bounded owned edit, tests pass, rollback exists | `ALLOW_WITH_CHECKPOINT` |
| compatible shared interface with required integration tests | `SERIALIZE_AND_TEST` |
| ambiguous product behavior | `HUMAN_APPROVAL_REQUIRED` |
| architecture/security/privacy/authority expansion | `HUMAN_APPROVAL_REQUIRED` |
| path traversal, unapproved route, cross-project injection | `DENY_SECURITY_VIOLATION` |
| deletion of task-created disposable artifact with recreation proof | `ALLOW_WITH_CHECKPOINT` |
| deletion of pre-existing source/test/schema/contract/decision/shared/user file | `HUMAN_APPROVAL_REQUIRED` |
| delete outside ownership | `DENY_SECURITY_VIOLATION` |

Create:

```python
@dataclass(slots=True)
class PolicyEngine:
    def decide(
        self,
        *,
        candidate: CanonicalContract,
        impact: ImpactResult,
        validation: ValidationReport,
        evidence_passed: bool,
        rollback_available: bool,
        deletion_classification: str | None,
    ) -> PolicyDecision: ...
```

- [ ] **Step 2: Implement restricted Change Contract application**

Create a private JSON Pointer parser supporting `~0` and `~1`, and only `add`, `replace`, and `remove` operations. Requirements:

- apply to a deep copy of the canonical target document;
- require new version to equal target version plus one;
- prohibit modifying `id`, `contract_type`, `project_id`, `schema_version`, `created_at`, or `created_by` through patch operations;
- require new provenance and related Change Contract reference in the resulting YAML;
- reject removing required schema fields;
- structurally and semantically validate the resulting document;
- run impact and policy analysis before repository creation;
- never overwrite the prior version.

- [ ] **Step 3: Create the minimal Section 1 activation schema**

`migrations/contracts/0001_activation_store.sql`:

```sql
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE project_generations (
    project_id TEXT PRIMARY KEY,
    last_generation INTEGER NOT NULL CHECK (last_generation >= 0)
);

CREATE TABLE contract_activations (
    project_id TEXT NOT NULL,
    contract_id TEXT NOT NULL,
    contract_version INTEGER NOT NULL CHECK (contract_version > 0),
    schema_version TEXT NOT NULL,
    generation INTEGER NOT NULL CHECK (generation > 0),
    content_hash TEXT NOT NULL CHECK (length(content_hash) = 64),
    runtime_status TEXT NOT NULL CHECK (runtime_status IN ('ACTIVE', 'SUPERSEDED', 'DISABLED', 'ROLLED_BACK')),
    canonical_json BLOB NOT NULL,
    validation_report_json TEXT NOT NULL,
    impact_report_json TEXT NOT NULL,
    policy_decision_json TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    rollback_contract_version INTEGER,
    activated_at TEXT NOT NULL,
    PRIMARY KEY (project_id, contract_id, contract_version),
    UNIQUE (project_id, generation)
);

CREATE TABLE active_contracts (
    project_id TEXT NOT NULL,
    contract_id TEXT NOT NULL,
    contract_version INTEGER NOT NULL,
    generation INTEGER NOT NULL,
    schema_version TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    enabled INTEGER NOT NULL CHECK (enabled IN (0, 1)),
    PRIMARY KEY (project_id, contract_id),
    FOREIGN KEY (project_id, contract_id, contract_version)
      REFERENCES contract_activations(project_id, contract_id, contract_version)
);

CREATE TABLE activation_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    contract_id TEXT NOT NULL,
    generation INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TRIGGER activation_events_no_update
BEFORE UPDATE ON activation_events
BEGIN SELECT RAISE(ABORT, 'activation_events are append-only'); END;

CREATE TRIGGER activation_events_no_delete
BEFORE DELETE ON activation_events
BEGIN SELECT RAISE(ABORT, 'activation_events are append-only'); END;
```

The migration runner must verify the migration SHA-256 before applying it, execute in one transaction, and record version `1` only after success.

- [ ] **Step 4: Implement writer and read-only store boundaries**

Create:

```python
class ActivationReader(Protocol):
    def get_active(self, project_id: str, contract_id: str) -> ActivationRecord | None: ...
    def get_generation(self, project_id: str) -> int: ...


@dataclass(slots=True)
class SQLiteActivationReader:
    database_path: Path

    def get_active(self, project_id: str, contract_id: str) -> ActivationRecord | None: ...
    def get_generation(self, project_id: str) -> int: ...


@dataclass(slots=True)
class _SQLiteActivationWriter:
    database_path: Path

    def activate_transactionally(...) -> ActivationRecord: ...
    def rollback_transactionally(...) -> ActivationRecord: ...
```

Reader connections must use `file:<path>?mode=ro` with `uri=True` and an SQLite authorizer callback denying `INSERT`, `UPDATE`, `DELETE`, `CREATE`, `DROP`, `ALTER`, `ATTACH`, `DETACH`, and writable pragmas. Do not export `_SQLiteActivationWriter` from package `__init__.py`.

- [ ] **Step 5: Implement Watchdog-owned activation transactions**

Create:

```python
@dataclass(slots=True)
class ActivationService:
    writer: _SQLiteActivationWriter
    cache: "RuntimeContractCache"

    def activate(
        self,
        candidate: CanonicalContract,
        *,
        impact: ImpactResult,
        policy: PolicyDecision,
        evidence: Mapping[str, JsonValue],
        expected_generation: int,
        approval_record: Mapping[str, JsonValue] | None = None,
        rollback_contract_version: int | None = None,
    ) -> ActivationRecord: ...

    def rollback(
        self,
        *,
        project_id: str,
        contract_id: str,
        target_version: int,
        expected_generation: int,
        reason: str,
    ) -> ActivationRecord: ...
```

Activation transaction order:

1. `BEGIN IMMEDIATE`;
2. verify current project generation equals `expected_generation`;
3. verify the candidate remains validated and hash-stable;
4. reject human-required policy without approval;
5. atomically increment `project_generations` and obtain next generation;
6. mark previous runtime activation `SUPERSEDED` when present;
7. insert immutable activation row and replace active pointer;
8. append audit event;
9. commit;
10. atomically replace the in-memory cache entry.

If any database step fails, rollback leaves prior activation and cache unchanged. If cache publication fails after commit, quarantine the cache entry and rebuild from the committed canonical bytes; do not increment generation again.

- [ ] **Step 6: Implement replace-only immutable runtime cache**

Create:

```python
@dataclass(slots=True)
class RuntimeContractCache:
    _entries: dict[tuple[str, str], CacheEntry]
    _lock: threading.RLock

    def publish(self, entry: CacheEntry) -> None: ...
    def get(self, project_id: str, contract_id: str, reader: ActivationReader) -> CacheEntry: ...
    def quarantine(self, project_id: str, contract_id: str, reason: str) -> None: ...
```

`get` verifies enabled status, ID, project, version, schema version, generation, and hash against SQLite. A mismatch removes only that entry and raises `ContractError(ErrorCode.CACHE_QUARANTINED, ...)`. Consumers receive frozen mappings and cannot mutate cache state.

- [ ] **Step 7: Run Task 4 verification**

```powershell
uv run pytest tests/contracts/unit/test_policy_engine.py tests/contracts/unit/test_change_application.py tests/contracts/unit/test_runtime_cache.py tests/contracts/integration/test_activation_store.py tests/contracts/integration/test_activation_flow.py tests/contracts/failure_paths/test_activation_rollback.py tests/contracts/security/test_read_only_activation_access.py tests/contracts/security/test_deletion_policy.py -v
uv run ruff check src tests
uv run mypy src/factory/contracts
```

Expected: all tests pass; generation is unchanged by parsing, startup, cache rebuild, and re-ingestion; failed transactions preserve the previous active contract.

- [ ] **Step 8: Commit Task 4**

```powershell
git add migrations src/factory/contracts/policy src/factory/contracts/activation src/factory/contracts/cache src/factory/contracts/service.py tests/contracts
git commit -m "feat: activate immutable contract versions"
```

---

### Task 5: Full Verification, Traceability, Windows Evidence, and Section 2 Handoff

**Files:**
- Create: `scripts/verify_section1.py`
- Create: `tests/contracts/integration/test_end_to_end_contract_lifecycle.py`
- Create: `tests/contracts/failure_paths/test_cache_recovery.py`
- Create: `tests/contracts/failure_paths/test_failed_change_preserves_active.py`
- Create: `tests/contracts/security/test_authority_expansion.py`
- Create: `tests/contracts/security/test_evidence_weakening.py`
- Create: `tests/contracts/security/test_cross_project_injection.py`
- Create: `tests/contracts/security/test_toc_tou_revalidation.py`
- Create: `docs/verification/section-1-requirements-contracts.md`
- Modify: `README.md`
- Modify: `docs/00-DOCUMENTATION-INDEX.md`

**Interfaces:**
- Consumes: every Section 1 public interface.
- Produces: one reproducible verification command, requirement-to-test matrix, evidence report, and stable interfaces for Section 2.

- [ ] **Step 1: Add an end-to-end lifecycle test**

The test must:

1. create a Project, Requirement, Task, Ownership, Permission, and Evidence contract set;
2. ingest and validate all contracts;
3. activate the initial versions automatically;
4. read the task through the immutable cache;
5. create a safe Change Contract editing only flexible intent;
6. create and activate task version 2 without human approval;
7. prove generation increments once;
8. prove version 1 remains immutable and loadable;
9. attempt authority expansion and receive `HUMAN_APPROVAL_REQUIRED`;
10. attempt cross-project injection and receive `DENY_SECURITY_VIOLATION`;
11. force activation failure and prove version 2 remains active;
12. rollback to version 1 and prove a new generation is assigned.

- [ ] **Step 2: Add the complete threat test matrix**

Create deterministic tests for every Section 1 security requirement:

| Threat | Required test |
|---|---|
| malformed YAML | parser rejection |
| duplicate keys | duplicate constructor rejection |
| unsafe tags | custom tag rejection |
| alias expansion | alias/node/depth limit rejection |
| path traversal/prefix | containment tests |
| symlink/junction/reparse escape | resolver tests |
| case/separator inconsistency | Windows normalization tests |
| stale cache | generation/hash mismatch quarantine |
| schema downgrade | unsupported version rejection |
| cross-project reference injection | resolver rejection |
| unapproved route | semantic rejection |
| authority expansion | impact/policy human gate |
| evidence weakening | impact/policy human gate |
| direct lane write | read-only SQLite denial |
| TOCTOU | pre-use revalidation rejection |
| protected deletion | approval or denial result |

- [ ] **Step 3: Build one verification command**

Create `scripts/verify_section1.py` to execute, in order:

```powershell
uv sync --frozen
uv run ruff format --check src tests scripts
uv run ruff check src tests scripts
uv run mypy src/factory/contracts
uv run pytest tests/contracts/unit -v
uv run pytest tests/contracts/integration -v
uv run pytest tests/contracts/security -m security -v
uv run pytest tests/contracts/failure_paths -m failure_path -v
uv run pytest tests/contracts --cov=src/factory/contracts --cov-branch --cov-report=term-missing --cov-fail-under=95
```

The script records command, start/end time, exit code, stdout/stderr SHA-256, environment identity, Python version, OS version, Git commit, and dependency lock hash into `artifacts/verification/section-1/manifest.json`. Runtime artifacts remain ignored; the final summarized evidence is copied into the committed verification document.

- [ ] **Step 4: Run Windows 11 Home verification**

Run from PowerShell in a clean uv environment:

```powershell
uv run python scripts/verify_section1.py
```

Expected:

- exit code `0`;
- Ruff format/check pass;
- strict mypy pass;
- all unit, integration, security, and failure-path tests pass;
- no unexpected skips;
- an allowed Windows privilege-dependent junction test may be classified `NOT TESTABLE` only when its deterministic resolver equivalent passes and the limitation is recorded;
- coverage is at least 95%;
- evidence manifest hashes match retained logs.

- [ ] **Step 5: Write the evidence-backed completion report**

`docs/verification/section-1-requirements-contracts.md` must include:

- exact commit tested;
- exact environment;
- commands and exit codes;
- test counts by category;
- coverage result;
- requirement-to-test matrix for all 13 acceptance criteria;
- security threat matrix;
- every claim classified `VERIFIED`, `FAILED`, `UNVERIFIED`, or `NOT TESTABLE`;
- retained artifact paths and hashes;
- known limitations;
- rollback instructions;
- Section 2 interfaces:
  - `ContractService.ingest`;
  - `SemanticValidator.validate`;
  - `ImpactAnalyzer.compare`;
  - `PolicyEngine.decide`;
  - `ActivationService.activate` and `.rollback`;
  - `ActivationReader.get_active` and `.get_generation`;
  - `RuntimeContractCache.get`.

Do not write “complete,” “safe,” or “passed” unless the corresponding evidence exists.

- [ ] **Step 6: Update repository navigation**

Update `README.md` status to identify Section 1 as implemented only after Task 5 verification passes. Add links to the design, implementation plan, and verification report. Update `docs/00-DOCUMENTATION-INDEX.md` with the same source order.

- [ ] **Step 7: Run the final regression command again after documentation changes**

```powershell
uv run python scripts/verify_section1.py
```

Expected: identical pass classification; documentation-only changes do not alter canonical contract behavior.

- [ ] **Step 8: Commit Task 5**

```powershell
git add scripts tests/contracts README.md docs/00-DOCUMENTATION-INDEX.md docs/verification
git commit -m "test: verify Section 1 contract system"
```

## Plan Self-Review Results

### Spec coverage

- Seven contract types and fixtures: Task 1.
- Safe YAML and structural validation: Task 2.
- Canonical JSON and stable SHA-256: Task 2.
- Cross-contract, route, resource, path, ownership, dependency, and interface validation: Task 3.
- Authority expansion and evidence weakening detection: Task 3.
- Immutable version creation and restricted Change Contracts: Task 4.
- Automatic safe activation and protected-boundary decisions: Task 4.
- SQLite activation generation and Watchdog-only writes: Task 4.
- Immutable cache, mismatch quarantine, and isolated recovery: Task 4.
- Transaction rollback preserving prior activation: Task 4.
- Deletion policy: Tasks 3 and 4.
- Complete Windows, security, failure-path, traceability, and evidence package: Task 5.
- Later queue, continuous Watchdog, providers, worktrees, containers, lanes, dashboard, and installer remain excluded.

### Placeholder scan

No `TBD`, `TODO`, “implement later,” unspecified error handling, or undefined interface remains in this plan.

### Type consistency

All later tasks use the exact public types and method names declared in the Public Interfaces section. Runtime generation and content hash remain SQLite metadata and are not editable YAML fields.

### Clarification locked by this plan

An activated YAML file remains byte-for-byte immutable with authored status `APPROVED`. Runtime `ACTIVE`, `SUPERSEDED`, `DISABLED`, and `ROLLED_BACK` states are stored in SQLite. This resolves the apparent conflict between immutable contract files and supersession tracking without rewriting history.
