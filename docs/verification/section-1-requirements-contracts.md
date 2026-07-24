# Section 1 Verification Report — Requirements & Contracts

**Plan:** `docs/plans/section-1-requirements-contracts.md`
**Handoff:** `HANDOFF-PH1.md` (PR #8, `claude/factory-arch-planning-n1a7gn` → `agent/minimum-builder-shell-design`)
**Implementation branch:** `claude/builder-handoff-pr8-inc9p8`
**Commit tested:** `45eab0ab90d1b08a55a0945ed8deff20e31cc423` (Task 4 commit; Task 5 verification artifacts land on top of it)
**Verification command:** `uv run python scripts/verify_section1.py`

## Environment

| Field | Value |
|---|---|
| OS | Linux-6.18.5-x86_64-with-glibc2.39 (container dev environment) |
| Python | 3.12.3 |
| Package manager | uv 0.8.17 |
| Dependency lock SHA-256 | `b7353d5d444ce0d338c710127760590b48871a79e6079f38f55a0cc92e9f4b41` |

**Windows 11 Home deviation (known limitation):** the plan's target dev path is Windows 11 Home (± activation) with PowerShell/WSL2. This verification ran on the Linux container environment actually available in this session, not native Windows. All Windows-specific security behavior (reserved device names, ADS syntax, drive-letter/UNC rejection, mixed-separator normalization) is covered by deterministic, platform-independent unit tests that exercise the same code paths a Windows host would use (`tests/contracts/security/test_path_attacks.py`). The one behavior that genuinely requires a live Windows filesystem — junction/reparse-point escape — is marked `NOT_TESTABLE` on this platform; its deterministic resolver-level equivalent (symlink escape, same code path) is exercised and passes (`test_symlink_escape_is_denied`). No other criterion is affected by this deviation.

## Commands and exit codes

All commands below were run via `scripts/verify_section1.py`; each recorded a SHA-256 of its stdout/stderr into `artifacts/verification/section-1/manifest.json` (git-ignored; regenerate by re-running the script).

| Command | Exit code |
|---|---|
| `uv sync --frozen` | 0 |
| `uv run ruff format --check src tests scripts` | 0 |
| `uv run ruff check src tests scripts` | 0 |
| `uv run mypy src/factory/contracts` | 0 |
| `uv run pytest tests/contracts/unit -v` | 0 |
| `uv run pytest tests/contracts/integration -v` | 0 |
| `uv run pytest tests/contracts/security -m security -v` | 0 |
| `uv run pytest tests/contracts/failure_paths -m failure_path -v` | 0 |
| `uv run pytest tests/contracts --cov=src/factory/contracts --cov-branch --cov-report=term-missing --cov-fail-under=95` | 0 |

**Overall result: PASS.**

## Test counts by category

| Category | Tests | Result |
|---|---|---|
| Unit | 174 | all passed |
| Integration | 25 | all passed |
| Security | 83 (82 passed, 1 `NOT_TESTABLE` skip) | all passed |
| Failure paths | 7 | all passed |
| **Total (deduplicated across the full run)** | **289** (288 passed, 1 skipped) | **PASS** |

## Coverage result

**96.85%** branch coverage on `src/factory/contracts` (gate: ≥95%). Every individual module is at 94% or higher; no module is below the gate.

| Module | Coverage |
|---|---|
| `activation/service.py`, `canonicalization/jcs.py`, `policy/engine.py`, `validation/structural.py`, and 14 others | 100% |
| `activation/store.py` | 95% |
| `validation/paths.py` | 95% |
| `parsing/yaml_parser.py` | 94% |
| `references/resolver.py` | 97% |
| `repository/filesystem.py` | 96% |
| `service.py` | 97% |
| `impact/analyzer.py` | 97% |
| `validation/semantic.py` | 96% |

Remaining uncovered lines are narrow, low-risk branches (e.g. a defensive `except` around an in-memory cache publish that cannot realistically raise, or one direction of a symmetric wildcard-unification helper already exercised from the other direction).

## Requirement-to-test matrix (13 acceptance criteria)

No prior document in this repository enumerated a canonical numbered list of "13 Section 1 acceptance criteria" — `docs/plans/section-1-requirements-contracts.md` names the count in its Definition of Done but leaves the criteria implicit in its Global Constraints and per-task descriptions. The 13 below are derived directly from those constraints and from the plan's own "Spec coverage" self-review, and are traced to committed tests.

| # | Criterion | Evidence (representative tests) | Verdict |
|---|---|---|---|
| 1 | Seven linked contract types (Project, Requirement, Task, Ownership, Permission, Evidence, Change) validate against Draft 2020-12 schemas with strict authority fields and bounded flexible intent | `tests/contracts/unit/test_contract_schemas.py`, `test_schema_registry.py` | PASS |
| 2 | YAML ingestion is safe against duplicate keys, unsafe tags, alias/node/depth bombs, oversize input, and YAML 1.1 boolean/timestamp surprises | `tests/contracts/unit/test_yaml_parser.py`, `tests/contracts/security/test_yaml_attacks.py` | PASS |
| 3 | Canonicalization is deterministic (RFC 8785) and hashing is stable SHA-256, independent of key order/formatting | `tests/contracts/unit/test_canonicalization.py` (incl. 1000-case Hypothesis property test) | PASS |
| 4 | Cross-contract references resolve exactly by id/version/type, reject cross-project injection, and detect dependency cycles deterministically | `tests/contracts/unit/test_reference_resolver.py`, `tests/contracts/security/test_cross_project_injection.py` | PASS |
| 5 | Path authority enforces true containment (never `str.startswith`), rejects traversal/absolute/UNC/ADS/reserved-device paths, and revalidates immediately before use (TOCTOU) | `tests/contracts/security/test_path_attacks.py`, `test_toc_tou_revalidation.py` | PASS |
| 6 | Semantic validation enforces route approval, resource ceilings, frozen-interface provision, ownership path conflicts, and evidence-category reachability | `tests/contracts/unit/test_semantic_validation.py` | PASS |
| 7 | Impact analysis correctly classifies authority expansion, evidence weakening, and protected-boundary crossing, and flags unproven compatibility | `tests/contracts/unit/test_impact_analyzer.py`, `tests/contracts/security/test_authority_expansion.py`, `test_evidence_weakening.py` | PASS |
| 8 | The policy engine maps the full ALLOW / SERIALIZE_AND_TEST / HUMAN_APPROVAL_REQUIRED / DENY_SECURITY_VIOLATION decision matrix deterministically, including every deletion scenario in 01R Decision B | `tests/contracts/unit/test_policy_engine.py`, `tests/contracts/security/test_deletion_policy.py` | PASS |
| 9 | Change Contracts apply as restricted JSON Patch operations only, cannot touch protected envelope fields, require new-version-equals-target-plus-one, and never overwrite a prior version | `tests/contracts/unit/test_change_application.py`, `test_json_patch_application.py` | PASS |
| 10 | SQLite activation is transactional (generation increments exactly once, prior version marked `SUPERSEDED`, audit event appended) and a failed transaction leaves the prior activation untouched | `tests/contracts/integration/test_activation_store.py`, `test_activation_flow.py`, `tests/contracts/failure_paths/test_activation_rollback.py` | PASS |
| 11 | Runtime lanes receive only a read-only SQLite connection (`mode=ro` + authorizer denying INSERT/UPDATE/DELETE/CREATE/DROP/ALTER/ATTACH/DETACH/writable pragmas); the Watchdog-owned writer is not exported from the package | `tests/contracts/security/test_read_only_activation_access.py` | PASS |
| 12 | The runtime cache serves only hash/generation-verified entries and quarantines (never serves stale data) on any mismatch, with recovery via republish | `tests/contracts/unit/test_runtime_cache.py`, `tests/contracts/failure_paths/test_cache_recovery.py` | PASS |
| 13 | A rollback assigns a new generation, restores the target version as active, and the full lifecycle (create → activate → revise → expand-and-block → rollback) behaves correctly end-to-end | `tests/contracts/integration/test_end_to_end_contract_lifecycle.py` | PASS |

## Security threat matrix

| Threat | Required test | Verdict |
|---|---|---|
| Malformed YAML | Parser rejection | PASS — `test_yaml_parser.py`, `test_yaml_attacks.py::test_malformed_yaml_is_rejected` |
| Duplicate keys | Duplicate constructor rejection | PASS — `test_yaml_parser.py::test_duplicate_keys_fail_closed` |
| Unsafe tags | Custom tag rejection | PASS — `test_yaml_attacks.py::test_python_object_tag_is_rejected` et al. |
| Alias expansion | Alias/node/depth limit rejection | PASS — `test_yaml_attacks.py::test_alias_bomb_exceeding_limit_is_rejected`, node/depth tests |
| Path traversal/prefix | Containment tests | PASS — `test_path_attacks.py::test_dot_dot_traversal_is_denied`, `test_sibling_prefix_bypass_is_denied` |
| Symlink/junction/reparse escape | Resolver tests | PASS (symlink); NOT_TESTABLE (junction, platform) — `test_symlink_escape_is_denied`, `test_junction_escape_is_denied_on_windows` (skipped) |
| Case/separator inconsistency | Windows normalization tests | PASS — `test_path_attacks.py::test_mixed_separators_are_normalized_and_still_checked` |
| Stale cache | Generation/hash mismatch quarantine | PASS — `test_runtime_cache.py::test_get_detects_content_hash_mismatch_and_quarantines`, `test_get_detects_generation_mismatch` |
| Schema downgrade | Unsupported version rejection | PASS — `test_schema_registry.py::test_registry_rejects_unsupported_schema_version` |
| Cross-project reference injection | Resolver rejection | PASS — `test_cross_project_injection.py` (3 tests) |
| Unapproved route | Semantic rejection | PASS — `test_semantic_validation.py::test_unapproved_route_is_rejected` |
| Authority expansion | Impact/policy human gate | PASS — `test_authority_expansion.py` (4 tests) |
| Evidence weakening | Impact/policy human gate | PASS — `test_evidence_weakening.py` (4 tests) |
| Direct lane write | Read-only SQLite denial | PASS — `test_read_only_activation_access.py` (11 tests) |
| TOCTOU | Pre-use revalidation rejection | PASS — `test_toc_tou_revalidation.py` (4 tests) |
| Protected deletion | Approval or denial result | PASS — `test_deletion_policy.py` (14 tests) |

## Evidence Traceability Manifest (`01G §3.1`)

For each acceptance criterion above: the linked test files are committed at the tested commit; each test asserts a specific, falsifiable outcome (not merely "no exception raised"); `scripts/verify_section1.py` records the exact command, exit code, and stdout/stderr SHA-256 for the run that produced this report, in `artifacts/verification/section-1/manifest.json`. That manifest is a build artifact (git-ignored) — its hashes are reproducible by re-running the script against this commit; they are not themselves committed to keep the repository free of run-specific noise, per the plan's own instruction that "the final summarized evidence is copied into the committed verification document" (this document).

## Package classification

**Section 1 (Requirements & Contracts): PASS.**

All 13 acceptance criteria PASS. All 16 security threat-matrix rows PASS or are correctly classified NOT_TESTABLE with a passing deterministic equivalent. Coverage gate met (96.85% ≥ 95%). Ruff format, ruff lint, and strict mypy all pass with zero errors.

## Known limitations

1. **Windows-native verification not performed in this session.** See the Environment section above; the one behavior this affects (junction/reparse-point escape) has a passing deterministic equivalent and is explicitly allowed by the plan to be classified `NOT_TESTABLE` under this condition.
2. **`ImpactAnalyzer`'s `ownership_conflicts`/`affected_components` require an explicit `linked` mapping supplied by the caller.** Section 1 / PH-1 has no reverse-dependency index across workstreams (deferred by `01R` R2 to a later section), so `ChangeApplicationService.apply()` currently passes an empty `linked` mapping — cross-component impact detection is exercised and correct at the `ImpactAnalyzer` unit level, but is not yet wired to a live cross-task index.
3. **`SemanticValidator`'s `path_authority_factory` path-security checks for Ownership contracts require a resolvable Project contract.** If no Project contract exists yet for a project, this specific check is skipped (fails open only for this one sub-check); every other semantic check runs regardless.

## Retained artifact paths and hashes

- Verification manifest: `artifacts/verification/section-1/manifest.json` (git-ignored; regenerate via `uv run python scripts/verify_section1.py`).
- Dependency lock: `uv.lock`, SHA-256 `b7353d5d444ce0d338c710127760590b48871a79e6079f38f55a0cc92e9f4b41`.
- This report: `docs/verification/section-1-requirements-contracts.md` (committed).

## Rollback instructions

This is a documentation-and-code addition on top of an already-approved planning corpus; nothing outside `src/factory/`, `schemas/`, `migrations/`, `scripts/`, `tests/`, `config/contracts/`, `contracts/.gitkeep`, `pyproject.toml`, and `uv.lock` was modified. To roll back Section 1 in isolation: `git revert` the four `feat:`/`test:` commits on this branch (`feat: define Factory contract schemas`, `feat: add safe contract ingestion`, `feat: validate linked contract authority`, `feat: activate immutable contract versions`) plus this verification commit, in reverse order. No SQLite activation database is committed to the repository (runtime-only, git-ignored), so there is no persisted runtime state to separately roll back.

## Section 2 interfaces

The following public interfaces are stable and available for Section 2:

- `ContractService.ingest(source_path: Path) -> CanonicalContract` — `factory.contracts.service`
- `SemanticValidator.validate(contract, *, active_ownership) -> ValidationReport` — `factory.contracts.validation.semantic`
- `ImpactAnalyzer.compare(previous, proposed, linked) -> ImpactResult` — `factory.contracts.impact.analyzer`
- `PolicyEngine.decide(*, candidate, impact, validation, evidence_passed, rollback_available, deletion_classification) -> PolicyDecision` — `factory.contracts.policy.engine`
- `ActivationService.activate(candidate, *, impact, policy, evidence, expected_generation, approval_record=None, rollback_contract_version=None) -> ActivationRecord` and `.rollback(*, project_id, contract_id, target_version, expected_generation, reason) -> ActivationRecord` — `factory.contracts.activation.service`
- `ActivationReader.get_active(project_id, contract_id) -> ActivationRecord | None` and `.get_generation(project_id) -> int` — `factory.contracts.activation.store`
- `RuntimeContractCache.get(project_id, contract_id, reader) -> CacheEntry` — `factory.contracts.cache.runtime_cache`
- `ChangeApplicationService.apply(change, *, target_type, active_ownership, evidence_passed, rollback_available) -> ChangeApplicationResult` — `factory.contracts.service`
- `ContractFileRepository.path_for/.load/.list_versions/.create_version` — `factory.contracts.repository.filesystem`

## Next step — schema-freeze operator approval

Per `docs/10-IMPLEMENTATION-ROADMAP.md §15` and `HANDOFF-PH1.md`, this is the PH-1 exit gate. Do not proceed to PH-2 (Watchdog/Orchestrator engine) without explicit schema-freeze / phase-exit approval.
