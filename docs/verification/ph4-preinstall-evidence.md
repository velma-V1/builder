# PH-4 (Section 4) — Model & Coding-Tool Routing & Quotas — Preinstallation Evidence

**Scope:** PH-4 preinstallation routing core built against deterministic fake provider adapters.
**Status:** `PH4_PREINSTALLATION_CORE_COMPLETE — LIVE_RUNTIME_PENDING`.
**Not:** a phase promotion, a merge, or any live-runtime claim. `main` and PR #10 are unchanged.
**Base:** roadmap PH-3 promoted baseline `3c979d72abee28776fc361bceb1b1edd55cde0ae`.
**Governing:** `docs/plans/section-4-model-and-worker-routing.md`, `01J`, `03`, `01R`;
CTR-ROUTE-REGISTRY / CTR-MODEL-FINGERPRINT / CTR-MODEL-EXEC-RECORD (`docs/planning/CONTRACT-REGISTRY.md`).

## Verdict

**PASS (preinstallation).** The deterministic routing core is implemented, tested to 100% branch
coverage, and gated. Live Ollama and live Aider execution, live resource sensing, and IP-2 remain
pending installation (see `ph4-pending-live-gate-register.md`).

## What was built (owner paths per the section-4 plan)

| Task | Owner path | Delivered (preinstallation) |
|---|---|---|
| 4.1 Ollama adapter | `src/factory/models/ollama_adapter/` | `FakeOllamaAdapter` — health/version, exact-model discovery, bounded call, every failure mode; live daemon PENDING |
| 4.2 Aider adapter | `src/factory/workers/aider_adapter/` | `FakeAiderWorker` — owned-path-enforced edits, no self-certification, no scope expansion; live Aider PENDING |
| 4.3 router + registry + fingerprint + records | `src/factory/routing/` | deterministic `ModelRouter`, `ApprovedRoster` (CTR-ROUTE-REGISTRY), `require_full_fingerprint` (CTR-MODEL-FINGERPRINT), append-only `ExecutionLedger` (CTR-MODEL-EXEC-RECORD), `ProviderAdapter` interface |
| 4.4 scheduler + quota | `src/factory/scheduler/` | `ResourceScheduler` (single-active GPU-heavy, ceilings, cooldown, pressure order, reconcile), `QuotaLedger` |
| 4.5 health / fallback / privacy | `src/factory/routing/` | `health_check_required` (`01J §3.4`), disclosed + reverified fallback and privacy gate in `ModelRouter` |

## Gate results (CPython 3.12.11, this environment)

| Gate | Result |
|---|---|
| `scripts/verify_ph4_preinstall.py` | **10/10 PASS** |
| PH-4 focused tests (`tests/routing`) | **93 passed** (unit 78, security 5, failure-path 7, integration 3) |
| Branch coverage (routing + scheduler + ollama_adapter + aider_adapter) | **100.00%** (obligation ≥95%) |
| Ruff (`src` + `tests`) | clean |
| mypy `--strict` | clean (31 source files) |
| Full repository (`pytest`) | **904 passed, 1 skipped** (Windows-only); +93 vs the 811 RPH-3 baseline, no regression |

## Governing-invariant coverage (`01J §5`, `03`)

| `01J` acceptance criterion | Where enforced | Test |
|---|---|---|
| §5.1 deterministic routing exposes model + reason | `router.route` | `test_route_is_deterministic_and_visible` |
| §5.2 operator override within limits | `router.route` override branch | `test_operator_override_*` |
| §5.3 complete fingerprint per execution | `fingerprint.require_full_fingerprint`, adapter fingerprints | `test_routing_fingerprint`, adapter tests |
| §5.4 no silent identity/config change | `router.execute` (never substitutes) | `test_runtime_unavailable_never_silently_reroutes` |
| §5.5 fallback closes failed attempt + new record | `router.fallback` | `test_fallback_opens_new_record_and_discloses_substitution` |
| §5.6 fallback reruns verification | `reverification_required` + `FallbackRecord.reverification_gates` | `test_fallback_records_a_disclosed_fallback_entry` |
| §5.7 switching preserves model-neutral state | `ExecutionLedger` append-only, `RoutingSnapshot` | `test_restart_reconciliation_*` |
| §5.9 no delegation outside gateway | adapters injected; router owns routing | `test_execute_missing_adapter_raises` |
| §5.10 reservations prevent overcommit before load | `ResourceScheduler.admit` | `test_resource_scheduler` (vram/ram/cpu/storage) |
| §5.11 CPU/RAM/VRAM/storage/timeout enforced | `ResourceScheduler.admit` | `test_resource_scheduler` |
| §5.12 cooldown/residency prevent thrash | `admit` cooldown branch | `test_cooldown_blocks_immediate_readmission` |
| §5.13 important-task health checks triggered | `health.health_check_required` | `test_routing_health` |
| §5.15 malformed output cannot become a transition | adapter `FAILED`/malformed result; not `ok` | `test_malformed_output_never_succeeds` |
| §5.17 cloud not required locally | local-first roster + privacy gate | `test_hosted_only_route_needs_cloud_permission` |
| §3.3 single-active GPU-heavy | `admit` GPU-heavy branch | `test_only_one_gpu_heavy_active` |
| §3.4 reduced monitoring on missing sensor | `admit` sensor branch | `test_missing_sensor_triggers_reduced_monitoring_but_still_admits` |
| `03 §6` no GLM anywhere approved | `roster.activate` exclusion | `test_glm_models_are_rejected_from_the_roster` |
| `03 §9` privacy before hosted | `router._privacy_ok` gate | `test_local_only_privacy_excludes_hosted_route` |

## Boundaries held

- No installation, no live Ollama/Aider execution, no network, no secrets.
- `main` (`9bce1ca`) unchanged; PR #10 (`7b1922e`) draft/open/unmodified.
- No merge, no phase promotion, no Stage-2 cutover, no PH-5/PH-6 code in this commit.
- The Worker Execution Substrate and RPH-3 security spine are unmodified; full repo regression green.

See the accompanying requirement-to-test matrix, failure-path matrix, and pending-live-gate register.
