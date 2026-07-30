# PH-4 Requirement-to-Test Matrix (preinstallation)

Maps each PH-4 preinstallation-core requirement (from the SYSTEM directive's `PH4_PREINSTALLATION_CORE`
list and the section-4 plan) to the implementing module and its deterministic test(s). All tests are
offline and use deterministic fakes.

| # | Requirement | Module | Test(s) |
|---|---|---|---|
| R1 | provider adapter interfaces | `routing/adapters/base.py` | `test_fake_ollama_satisfies_provider_adapter_protocol` |
| R2 | fake Ollama adapter | `models/ollama_adapter/fake_ollama.py` | `test_ollama_*` (probe/supports/call/cancel/behaviors) |
| R3 | fake Aider adapter | `workers/aider_adapter/fake_aider.py` | `test_aider_*` |
| R4 | deterministic router | `routing/router.py` | `test_route_is_deterministic_and_visible` |
| R5 | approved-model roster validation | `routing/roster.py` | `test_activate_*`, `test_descriptor_lookup_unknown_raises` |
| R6 | model fingerprints | `routing/models.py`, `routing/fingerprint.py` | `test_fingerprint_digest_*`, `test_routing_fingerprint` |
| R7 | model execution records (append-only) | `routing/records.py` | `test_store_is_append_only_and_rejects_duplicate_ids`, `test_ledger_record_and_queries` |
| R8 | quota ledger | `scheduler/quota.py` | `test_routing_quota` (charge/would_exceed/remaining/snapshot) |
| R9 | resource scheduler | `scheduler/scheduler.py` | `test_resource_scheduler` |
| R10 | reservation and release | `scheduler/scheduler.py` | `test_admit_returns_reservation_and_tracks_active`, `test_release_is_idempotent` |
| R11 | GPU-heavy single-active policy | `scheduler/scheduler.py` | `test_only_one_gpu_heavy_active` |
| R12 | no silent substitution | `routing/router.py` | `test_runtime_unavailable_never_silently_reroutes` |
| R13 | explicit fallback records | `routing/router.py`, `routing/records.py` | `test_fallback_records_a_disclosed_fallback_entry` |
| R14 | fallback reverification | `routing/router.py` | `test_fallback_opens_new_record_and_discloses_substitution` |
| R15 | local-only policy (privacy) | `routing/router.py` | `test_local_only_privacy_excludes_hosted_route`, `test_hosted_only_route_needs_cloud_permission` |
| R16 | capability detection | adapters `probe()` | `test_ollama_probe_reports_installed_models`, `test_aider_probe_and_call` |
| R17 | explicit runtime-unavailable results | adapters + router | `test_ollama_call_runtime_down_is_explicit_result`, `test_execute_denied_admission_makes_no_call` |
| R18 | restart reconciliation | `routing/router.py`, `scheduler/scheduler.py` | `test_restart_reconciliation_restores_usage_and_reports_in_flight`, `test_reconcile_releases_orphans_and_adopts_live` |
| R19 | approved-model roster excludes GLM-4.7 | `routing/roster.py` | `test_glm_models_are_rejected_from_the_roster` |
| R20 | operator override within limits | `routing/router.py` | `test_operator_override_*` |
| R21 | health-check triggers (`01J §3.4`) | `routing/health.py` | `test_routing_health` |

All 21 requirements are covered by passing deterministic tests at 100% branch coverage.
