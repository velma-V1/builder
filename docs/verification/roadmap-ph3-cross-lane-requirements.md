# RPH3 Cross-Lane Requirement-to-Test Matrix

| Requirement | Test evidence | Verdict |
|---|---|---|
| Lane A consumes accepted Lane B interfaces by value | dedicated verifier real-interface check; all focused tests | PASS |
| Permission denial and approval-required propagate | `test_real_permission_results_propagate_allow_deny_and_approval_required` | PASS |
| Approval pending/granted/expired/replay propagate | `test_real_approval_required_expired_and_replay_results_propagate` | PASS |
| ToolGateway denial propagates; no direct gateway bypass | `test_tool_gateway_denial_propagates_without_bypass`; static verifier | PASS |
| FileOp denial propagates | `test_fileop_revoked_permission_propagates_terminal_denial` | PASS |
| Healthy audit status produces no intervention | `test_healthy_lane_b_has_no_intervention`; full-flow test | PASS |
| Audit break/failure produces containment via WIR | audit-break and validator-outage tests | PASS |
| Dependency loss produces pause via WIR | `test_dependency_failure_pauses_and_safe_mode_escalation_is_read_only` | PASS |
| Safe Mode escalation is capability-scoped/read-only | same; asserts `autonomous_write` blocked | PASS |
| WIR valid, stale/rejected, unavailable delivery | audit/dependency tests; `test_stale_intervention_and_wir_outage_are_explicit_terminal_results` | PASS |
| Duplicate delivery is idempotent across restart | `test_restart_duplicate_delivery_uses_wir_durable_result` | PASS |
| Conflicting op-key reuse fails closed | `test_duplicate_pure_denial_is_deterministic_and_conflict_fails_closed` | PASS |
| Concurrent domain isolation | `test_concurrent_domain_signals_are_isolated_and_no_bypass_surface_exists` | PASS |
| Unbounded/wildcard message rejection | `test_unbounded_or_wildcard_cross_lane_message_is_rejected` | PASS |
| Full repository-defined Lane A/Lane B path | `test_full_permission_approval_fileop_audit_watchdog_flow` | PASS |
| No task intake/execution/continuation/host path | static verifier + bridge surface assertions | PASS |
| T1 and accepted Lane B behavior unchanged | T1/T2/T3/T4/T5 verifiers + full repository | PASS |
