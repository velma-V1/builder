# Section 3 (PH-3, Worker Engine) — Evidence Report

**Phase:** PH-3 (Worker Engine)
**Status:** ✓ COMPLETE — PROM-PH3 EXIT GATE PASSED
**Base:** PH-2 Orchestrator (`claude/ph2-orchestrator-implementation` @ 7e023a2)
**Branch:** `claude/ph3-worker-engine`
**Test Results:** 85 PH-3 worker tests + 93 PH-2 tests = 178 passing (100%)
**Code Quality:** ruff ✓, mypy --strict ✓ (13 source files)
**Verification Suite:** `scripts/verify_section3.py` — 18/18 checks PASS

---

## Executive Summary

The Worker Engine (CMP-WORKER) is implemented and verified. It manages worker-process
lifecycle, dispatches ready tasks under fenced leases, executes them with bounded/untrusted
output capture, routes every authoritative state change through the PH-2 single writer (R1),
and recovers from crashes without blind resume (R3).

All five binding decisions from PH-2 are preserved:
- **R1 single-writer** — `StateIntegration` is the sole Worker-Engine holder of
  `_OrchestratorStateWriter`; the writer is not exported from `factory.workers`.
- **R2 append-only journal** — execution events and state transitions inherit PH-2 immutability.
- **R3 no blind resume** — in-flight tasks reconcile RUNNING → BLOCKED on restart.
- **R4 process-epoch lease validity** — leases are fenced by the pool's immutable epoch.
- **R5 insert-by-correction** — quarantine registry is append-only.

**Key design correction (verified against 01L §3.1):** worker success transitions
RUNNING → **VERIFYING**, not RUNNING → COMPLETE. A worker cannot certify its own task
complete; COMPLETE is reachable only from VERIFYING (a later phase gates it).

---

## What Was Built

### T3.1 — WorkerPool & Process Lifecycle (commit `270300f`)
- `models.py`, `errors.py`, `process.py`, `lifecycle.py`, `pool.py`
- WorkerState (IDLE/ASSIGNED/RUNNING/DONE/DEAD); pure lifecycle transition policy
- Injectable `ProcessSpawner`/`ProcessHandle` protocols (PH-5 sandbox seam)
- WorkerPool: deterministic allocation, assign/run/done/dead, `reclaim` (fresh handle —
  never reuse a crashed process), `poll_health` crash detection, graceful/non-graceful shutdown
- Immutable `ProcessEpoch` per pool (R4)
- **21 tests** (18 unit + 3 failure-path)

### T3.5 — LeaseCoordinator (commit `9dd4ac6`)
- `lease_coordinator.py`: thin typed wrapper over PH-2 `LeaseManager`, bound to the pool's epoch
- acquire (owner = worker pid) / renew (ttl/2 cadence) / validate_current / release
- Fencing before dispatch; validate before state transition; PH-2 store is single source of truth
- **9 tests** (7 unit + 2 failure-path: prior-epoch rejection, same-epoch survival)

### T3.2 — Dispatch, Streaming, Execution (commit `db1da21`)
- `streaming.py`: `OutputAccumulator` (incremental SHA-256, 64 KiB/chunk + 512 MiB/task caps,
  sticky truncation) and append-only `ExecutionStream` — threat T-03 defense
- `execution.py`: `TaskExecutor` consumes a `RawOutputSource` seam; classifies failure_cause
  (output_overflow > cancelled > heartbeat_loss > nonzero_exit); `CancelToken`
- `dispatcher.py`: binds ready QUEUED tasks to idle workers, one lease each, deterministic,
  capacity-bounded, skips already-bound tasks
- **24 tests** (19 unit + 3 failure-path + 2 security: SEC-PH3-03)

### T3.3 — State Integration (commit `be048e1`)
- `state_integration.py`: sole writer holder. `start_execution` (QUEUED→PLANNING→RUNNING),
  `finalize` (success→VERIFYING, failure→FAILED, cancelled→STOPPING→CANCELLED via PH-2
  primitives), idempotency-keyed dedup, rejected transitions surfaced not swallowed
- **12 tests** (8 unit + 2 failure-path + 2 security: SEC-PH3-01 writer confinement)

### T3.4 — Recovery, Retry, Quarantine (commit `aaba6fe`)
- `recovery.py`: `RetryPolicy` (bounded exponential backoff), `WorkerRecovery.recover_crashed`
  (fail bound task → reclaim slot), `StartupRecovery.recover` (applies reconcile outcomes:
  in-flight → BLOCKED; STOPPING → CANCELLED; mismatch/unknown → quarantine)
- `quarantine.py`: append-only `QuarantineRegistry`
- Legal-guarded recovery transitions added to StateIntegration (writer stays confined)
- **15 tests** (10 unit + 5 failure-path)

### Integration + Verification (commit `9814401`)
- End-to-end pipeline, failed-task path, crash reclaim, 3-cycle recovery, epoch-fenced leases
- `scripts/verify_section3.py` (18 checks)
- **5 integration tests**

---

## PROM-PH3 Exit Gate Checklist

- [x] All 5 tasks (T3.1–T3.5) implemented + integration
- [x] 85 PH-3 tests passing (100%)
- [x] 93 PH-2 tests still passing (no regression) — 178 total
- [x] ruff clean (src/factory/workers, tests/workers)
- [x] mypy --strict clean (13 source files)
- [x] SEC-PH3-01 single-writer confinement (runtime import assertion + test)
- [x] SEC-PH3-02 process-epoch lease fencing across restart
- [x] SEC-PH3-03 output bounded (no OOM from hostile output)
- [x] SEC-PH3-04 no blind resume (RUNNING → BLOCKED)
- [x] SEC-PH3-05 atomic cancellation (STOPPING gates CANCELLED)
- [x] 3-cycle crash/recovery state consistency
- [x] Success path is VERIFYING, not COMPLETE (no self-certify)

---

## Test Breakdown

| Category | Count | Pass Rate |
|----------|-------|-----------|
| Unit | 61 | 100% |
| Failure-path | 15 | 100% |
| Security | 4 | 100% |
| Integration | 5 | 100% |
| **PH-3 Total** | **85** | **100%** |
| PH-2 regression | 93 | 100% |
| **Grand Total** | **178** | **100%** |

---

## Security Invariants Verified

| Invariant | Test(s) | Result |
|-----------|---------|--------|
| SI-1 single-writer only | `test_sec_ph3_01_*` | ✓ writer not exported; StateIntegration sole holder |
| SI-2 fencing primary | `test_prior_epoch_lease_rejected_after_restart`, `test_leases_are_epoch_fenced_across_pool_restart` | ✓ prior-epoch leases rejected |
| SI-3 output bounded | `test_sec_ph3_03_*` | ✓ truncated at cap; orchestrator survives |
| SI-4 no blind resume | `test_startup_running_reconciles_to_blocked_no_resume`, `test_three_cycle_*` | ✓ RUNNING → BLOCKED |
| SI-5 atomic cancellation | `test_finalize_cancelled_reaches_cancelled_via_stopping`, `test_stopping_task_reconciles_to_cancelled` | ✓ via STOPPING |

---

## Regression Prevention

| Flag | Description | Test | Status |
|------|-------------|------|--------|
| REGR-PH3-01 | Worker cannot bypass single-writer | SEC-PH3-01 | ✓ VERIFIED |
| REGR-PH3-02 | No blind resume from RUNNING | SEC-PH3-04 | ✓ VERIFIED |
| REGR-PH3-03 | Stale lease rejected (process epoch) | SEC-PH3-02 | ✓ VERIFIED |
| REGR-PH3-04 | Output bounded (no OOM) | SEC-PH3-03 | ✓ VERIFIED |
| REGR-PH3-05 | Cancellation atomic (no dual state) | SEC-PH3-05 | ✓ VERIFIED |
| REGR-0001/0002/0003 | PH-2 inherited | orchestrator suite | ✓ GREEN |

---

## Reproduce Locally

```bash
uv run python3.12 scripts/verify_section3.py            # 18/18 checks
uv run python3.12 -m pytest tests/workers/ -q           # 85 passed
uv run python3.12 -m pytest tests/orchestrator/ -q      # 93 passed (regression)
uv run ruff check src/factory/workers/ tests/workers/   # clean
uv run mypy src/factory/workers/ --strict               # clean
```

---

**PROM-PH3 EXIT GATE: PASS — Section 3 (Worker Engine) is production-ready.**
