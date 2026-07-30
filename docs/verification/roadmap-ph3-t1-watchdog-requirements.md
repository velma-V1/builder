# RPH3-T1 CMP-WATCH Requirement-to-Test Matrix

| Requirement | Test evidence | Verdict |
|---|---|---|
| Independent normally read-only observer; auto-launch off | `test_process_is_not_auto_launched_and_selects_deterministic_interventions`; verifier observer/isolation checks | PASS |
| Exact seven-command immutable interface, default-deny | `test_allowlist_is_exactly_the_seven_governed_commands`; `test_unknown_command_is_default_denied`; `test_caller_cannot_expand_the_immutable_allowlist` | PASS |
| Authenticated monotonic heartbeat; no wall-clock false stall | `test_heartbeat_uses_monotonic_time_and_rejects_replay`; `test_wall_clock_rollback_cannot_fabricate_a_stall` | PASS |
| Staged thresholds, sustained windows, hysteresis | `test_thresholds_stage_and_recover_with_hysteresis`; `test_invalid_threshold_and_monotonic_regression_fail_closed` | PASS |
| Missing sensor is declared, never fabricated | `test_missing_sensor_enters_reduced_monitoring_without_fabrication` | PASS |
| Deterministic failure identity excludes volatile data | `test_failure_identity_excludes_volatile_fields_and_is_deterministic` | PASS |
| Bounded restart/backoff/circuit breaker | `test_service_supervisor_bounds_retries_and_opens_circuit`; invalid-policy cases | PASS |
| Request auth, bounded target, expected-state, authority gate | parameterized invalid-request tests; `test_permission_or_approval_gate_cannot_be_bypassed` | PASS |
| Task writes only through frozen CMP-ORCH | pause/contain/reconcile integration tests; verifier WIR/isolation checks | PASS |
| Class-2/Class-3 audit-before-success ordering | pause/restart integration tests; `test_audit_finalize_outage_never_reports_class2_applied` | PASS |
| Duplicate prevention and concurrent idempotency | `test_pause_is_durable_audited_and_idempotent`; `test_concurrent_duplicate_request_has_one_effect_and_one_audit` | PASS |
| Crash/restart reconciliation; no blind retry | Class-2 pre/post-audit roll-forward/rollback and Class-3 pre-intent/uncertain/completed tests | PASS |
| Watchdog/WIR loss fails high-risk work closed | `test_watchdog_or_receiver_loss_blocks_new_and_pauses_existing_high_risk` | PASS |
| Safe Mode/quarantine routing without observer writes | `test_process_is_not_auto_launched_and_selects_deterministic_interventions` | PASS |
| Phase boundaries remain inert | `test_forward_bound_commands_are_inert_and_never_execute` | PASS |
| Ordered SHA-pinned migration; old migrations unchanged | all `test_watchdog_store.py` cases; dedicated verifier migration check | PASS |
| Private sole writer and read-only consumers | `test_reader_is_structurally_read_only_and_writer_is_not_exported` | PASS |

Real Lane B approval expiry/replay, permission revocation, gateway/file-op denial, and Safe Mode
delivery are cross-lane obligations and are intentionally assigned to authorized M2.
