# Section 3 (PH-3) — Test Execution & Coverage Summary

**Total:** 85 PH-3 tests (100% pass) + 93 PH-2 regression = 178 passing
**Command:** `uv run python3.12 -m pytest tests/workers/ -q`

---

## Coverage by Task

| Task | Module(s) | Unit | Failure | Security | Integration |
|------|-----------|------|---------|----------|-------------|
| T3.1 WorkerPool | pool, process, lifecycle, models | 18 | 3 | — | — |
| T3.5 LeaseCoordinator | lease_coordinator | 7 | 2 | — | — |
| T3.2 Dispatch/Stream/Exec | dispatcher, streaming, execution | 19 | 3 | 2 | — |
| T3.3 State Integration | state_integration | 8 | 2 | 2 | — |
| T3.4 Recovery/Quarantine | recovery, quarantine | 9 | 5 | — | — |
| Integration (E2E) | (whole engine) | — | — | — | 5 |
| **Total** | | **61** | **15** | **4** | **5** |

---

## Unit Tests (61)

### WorkerPool / lifecycle (18)
- pool spawns N idle workers; rejects zero size
- process epoch immutable, stamped on workers; distinct per pool
- deterministic available-worker selection
- assign IDLE→ASSIGNED; assigned not re-offered; duplicate-task rejected
- full slot lifecycle IDLE→ASSIGNED→RUNNING→DONE
- illegal transition (IDLE→RUNNING skip) rejected
- find_by_task live binding; ignores terminal slots
- reclaim replaces terminal slot with fresh handle; rejects live slot
- unknown worker raises; graceful/non-graceful/idempotent shutdown

### LeaseCoordinator (7)
- acquire returns TASK lease owned by pid; monotonic tokens
- validate_current true for fresh; superseded invalidated
- renew keeps valid; release invalidates; non-positive ttl rejected

### Dispatch / Streaming / Execution (19)
- dispatch binds ready QUEUED task; respects capacity; skips non-QUEUED / already-bound
- deterministic order; waits on unmet dependency
- execution: clean/ nonzero / missing-END / cancelled classification; event count; deterministic hash; stream_for
- streaming: accumulator hash/clip/sticky-truncation; stream sequence ordering; stdout bounds; truncation flag

### State Integration (8)
- start_execution QUEUED→RUNNING; rejects already-running
- finalize success→VERIFYING (not COMPLETE); nonzero→FAILED; overflow→FAILED
- cancelled→CANCELLED via STOPPING; idempotent replay; unknown task raises

### Recovery / Quarantine (9)
- retry backoff exponential; exhausted after max; invalid attempt rejected
- quarantine record/dedup; is_quarantined
- recover_crashed fails bound task + reclaims; untasked slot reclaimed silently
- startup RUNNING→BLOCKED (no resume); QUEUED stays QUEUED

---

## Failure-Path Tests (15)

| Test | Scenario |
|------|----------|
| test_poll_health_detects_running_worker_crash | worker exits while RUNNING → DEAD |
| test_poll_health_ignores_idle_and_clean_exit_of_free_slot | IDLE stub exit is not a crash |
| test_crashed_worker_reclaimable_after_detection | reclaim after crash |
| test_output_overflow_truncates_and_fails | > total cap → output_overflow |
| test_incomplete_stream_reports_heartbeat_loss | no END → heartbeat_loss |
| test_cancel_before_any_event | pre-cancel → cancelled |
| test_prior_epoch_lease_rejected_after_restart | R4 cross-restart fencing |
| test_same_epoch_lease_survives_new_coordinator_instance | same epoch valid |
| test_stopping_task_reconciles_to_cancelled | interrupted cancel finishes |
| test_planning_task_reconciles_to_blocked | in-flight PLANNING → BLOCKED |
| test_unknown_task_is_quarantined | unknown → QUARANTINED registry |
| test_blocked_task_not_resumed_on_reconcile | BLOCKED stays BLOCKED |
| test_crashed_task_stays_failed_across_recovery | FAILED terminal |
| test_finalize_success_from_queued_is_rejected | illegal transition surfaced |
| test_start_execution_from_terminal_is_rejected | terminal start rejected |

---

## Security Tests (4 + 1 integration)

| Test | Invariant |
|------|-----------|
| test_sec_ph3_01_writer_not_exported_from_workers_package | SI-1 single-writer confinement |
| test_sec_ph3_01_state_integration_is_sole_writer_holder | SI-1 sole holder |
| test_sec_ph3_03_unbounded_output_is_capped | SI-3 output bounds |
| test_sec_ph3_03_single_giant_chunk_clipped | SI-3 per-chunk clip |
| test_leases_are_epoch_fenced_across_pool_restart (integration) | SI-2 fencing |

---

## Integration Tests (5)

| Test | Flow |
|------|------|
| test_full_pipeline_dispatch_execute_finalize | dispatch→start→execute→finalize→release, ends VERIFYING |
| test_failed_task_pipeline | nonzero exit → FAILED |
| test_crash_recovery_reclaims_and_frees_capacity | crash → FAILED + reclaim |
| test_three_cycle_crash_recovery_keeps_state_consistent | 3× RUNNING→BLOCKED→resume, journal consistent |
| test_leases_are_epoch_fenced_across_pool_restart | epoch A lease rejected by epoch B |

---

## Quality Gates

| Gate | Result |
|------|--------|
| ruff check (workers + tests) | ✓ clean |
| mypy --strict (13 files) | ✓ no issues |
| verify_section3.py | ✓ 18/18 |
| PH-2 regression | ✓ 93/93 |
