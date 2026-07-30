# RPH3-T1 CMP-WATCH Failure-Path Matrix

| Failure/crash point | Expected terminal behavior | Test | Verdict |
|---|---|---|---|
| Watchdog/WIR unavailable, new high-risk work | block admission | `test_watchdog_or_receiver_loss_blocks_new_and_pauses_existing_high_risk` | PASS |
| Watchdog/WIR unavailable, running high-risk work | issue pause decision | same | PASS |
| Bad auth, bulk/wildcard, stale state | reject, no effect, audit rejection | parameterized security test | PASS |
| Authority/approval/permission gate denial | reject, no recovery call | `test_permission_or_approval_gate_cannot_be_bypassed` | PASS |
| Crash/store outage before intent persists | no task effect, no audit | `test_crash_before_intent_persist_has_no_effect_or_audit` | PASS |
| Class-2 crash after intent, before task transition | reconcile rollback/FAILED | `test_class2_crash_windows_roll_forward_or_back` | PASS |
| Class-2 crash after task transition, before audit | roll completion audit forward/APPLIED | same | PASS |
| Class-2 crash after completion audit, before journal commit | reuse durable audit; no duplicate; roll forward | `test_class2_crash_after_completion_reuses_durable_audit` | PASS |
| Illegal Class-2 transition | FAILED, never APPLIED | `test_illegal_transition_is_failed_not_applied` | PASS |
| Audit unavailable after Class-2 execution path | fail closed, never APPLIED | `test_audit_finalize_outage_never_reports_class2_applied` | PASS |
| Restart exhausts bounded recovery | FAILED, audited, circuit opens | `test_failed_restart_is_audited_but_never_reported_applied`; bounded-recovery unit test | PASS |
| Class-3 crash before audit intent | restart cannot have been issued; audit aborted outcome; rollback | `test_class3_crash_before_audit_intent_is_aborted_without_restart` | PASS |
| Class-3 audit intent durable, outcome unproven | QUARANTINED, completion-audited, never retried | `test_class3_crash_after_intent_is_quarantined_without_retry` | PASS |
| Class-3 completion durable, journal commit missing | roll forward APPLIED, never reissue restart | `test_class3_crash_after_completion_rolls_forward_without_restart` | PASS |
| Duplicate/concurrent delivery | one effect, one completion audit | integration concurrency test | PASS |
| Missing/unreliable sensor | `REDUCED_MONITORING`, route to Safe Mode | unit threshold/routing tests | PASS |
| Critical containment trigger | contain/quarantine route | unit routing + containment integration test | PASS |
| Forward-bound PH-5/PH-7 command | INERT, audited, no effect | forward-bound security test | PASS |
