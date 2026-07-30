# PH-4 Failure-Path Matrix (preinstallation)

Every failure mode the directive enumerates, the deterministic injection used, and the required
fail-closed / explicit-result behavior. No failure silently succeeds or silently reroutes.

| # | Failure mode | Injection | Required behavior | Test |
|---|---|---|---|---|
| F1 | provider runtime down | `FakeOllamaAdapter(status=UNAVAILABLE)` | explicit `RUNTIME_UNAVAILABLE` result; record on the same route; no auto-fallback | `test_runtime_unavailable_never_silently_reroutes` |
| F2 | missing / uninstalled model | adapter with model absent | explicit `RUNTIME_UNAVAILABLE` + `MODEL_MISSING` | `test_ollama_call_missing_model_is_explicit_result` |
| F3 | fingerprint insufficient (bare tag) | `require_full_fingerprint(bare)` | raise `FINGERPRINT_INSUFFICIENT` | `test_bare_declared_name_is_insufficient` |
| F4 | timeout | `behaviors={model: TIMED_OUT}` | terminal `TIMED_OUT` record; not `ok` | `test_timeout_is_recorded_as_terminal` |
| F5 | malformed output | `behaviors={model: FAILED}` | `FAILED` + `MALFORMED_OUTPUT`; never a success/transition | `test_malformed_output_never_succeeds` |
| F6 | cancellation | `adapter.cancel(task_id)` | `CANCELLED` result | `test_ollama_cancellation` |
| F7 | quota exhausted | `QuotaLimits(0,0,0)` | `QUOTA_EXCEEDED`, no partial charge | `test_quota_exhaustion_blocks_charge`, `test_charge_over_limit_is_refused_without_mutation` |
| F8 | reservation overcommit | ceilings breached (vram/ram/cpu/storage/free-ram) | `DENIED_OVERCOMMIT`, no record/call | `test_*_ceiling_*`, `test_admission_denied_produces_no_record` |
| F9 | GPU-heavy contention | two GPU-heavy admits | second `DENIED_GPU_HEAVY_BUSY` | `test_only_one_gpu_heavy_active` |
| F10 | thrash (rapid reload) | release then re-admit within cooldown | `DENIED_COOLDOWN` | `test_cooldown_blocks_immediate_readmission` |
| F11 | missing resource sensor | `SensorReading()` with `None` fields | `REDUCED_MONITORING`, still fail-closed on ceilings | `test_missing_sensor_triggers_reduced_monitoring_but_still_admits` |
| F12 | fallback to unapproved model | substitute not rostered | `FALLBACK_UNAPPROVED` | `test_fallback_requires_an_approved_substitute` |
| F13 | fallback violating privacy | hosted substitute under LOCAL_ONLY | `FALLBACK_PRIVACY` | `test_fallback_rejects_privacy_violating_substitute` |
| F14 | fallback on a non-failed record | substitute a succeeded attempt | `FALLBACK_NOT_FAILED` | `test_fallback_on_a_healthy_record_is_refused` |
| F15 | fallback from unknown record | bogus record id | `FALLBACK_UNKNOWN` | `test_fallback_from_unknown_record_is_rejected` |
| F16 | fallback admission denied | oversized substitute profile | denied outcome, no new record, reverify flagged | `test_fallback_denied_admission_yields_no_new_record` |
| F17 | fallback substitute also fails | substitute times out | new failed record supersedes, reverify flagged | `test_fallback_substitute_that_also_fails_is_recorded` |
| F18 | duplicate execution record | append same id twice | `RECORD_DUPLICATE` | `test_store_is_append_only_and_rejects_duplicate_ids` |
| F19 | orphaned reservation after crash | reconcile with a live set excluding it | orphan released | `test_reconcile_releases_orphans_and_adopts_live` |
| F20 | operator override unapproved / private | bad override id / hosted under LOCAL_ONLY | `OVERRIDE_UNAPPROVED` / `OVERRIDE_PRIVACY` | `test_operator_override_unapproved_is_rejected`, `test_operator_override_violating_privacy_is_rejected` |
| F21 | worker scope expansion | edit outside owned paths / traversal | rejected, never applied | `test_aider_edits_within_owned_paths_only`, `test_aider_rejects_path_traversal`, `test_worker_cannot_expand_scope` |
