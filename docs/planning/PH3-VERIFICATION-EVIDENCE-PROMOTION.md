# PH-3 Verification, Evidence & Promotion Gates

**Phase:** PH-3 (Worker Engine)  
**Base:** PH-2 Orchestrator (93 tests passing)  
**Target:** 64 PH-3 tests + PROM-PH3 exit gate

---

## Verification Matrix

### Task → Test Mapping

| Task | Unit | Failure-Path | Security | Integration | Total |
|------|------|--------------|----------|-------------|-------|
| **T3.1 WorkerPool** | 12 | 2 | — | — | 14 |
| **T3.2 Dispatch/Streaming** | 15 | 3 | 1 (output) | — | 19 |
| **T3.3 State Integration** | 8 | 2 | 1 (writer) | — | 11 |
| **T3.4 Recovery/Rollback** | 10 | 5 | 1 (resume) | — | 16 |
| **T3.5 Lease Coordination** | 6 | 2 | 1 (fencing) | — | 9 |
| **Integration (E2E)** | — | — | 1 (cancel race) | 8 | 9 |
| **TOTAL** | 51 | 14 | 5 | 8 | **78** |

**Note:** Revised from initial 64 estimate to 78 for full coverage.

---

## Promotion Gates (PROM-PH3)

### Gate 1: Test Pass & Code Quality (PROM-PH3-PASS-01)
**Criteria:**
- [ ] All 78 tests pass (100%)
- [ ] ruff check: 0 violations
- [ ] mypy --strict: 0 errors
- [ ] Cumulative PH-2 tests still pass (93 tests; no regression)

**Verification:** `uv run pytest tests/ -q` + `ruff check src/` + `mypy src/ --strict`

### Gate 2: Recovery Simulation (PROM-PH3-PASS-02)
**Criteria:**
- [ ] Worker crash → FAILED (heartbeat_loss); worker reclaimed
- [ ] Pool restart during RUNNING → BLOCKED (no resume)
- [ ] Lease expiry → FAILED (lease_expiry)
- [ ] Task timeout → SIGTERM/SIGKILL → FAILED
- [ ] Output overflow → truncate → FAILED

**Verification:** Failure-path test suite (RT-1 through RT-10)

### Gate 3: State Writer Confinement (PROM-PH3-PASS-03)
**Criteria:**
- [ ] Code audit: `_OrchestratorStateWriter` not exported from any `__init__.py`
- [ ] SEC-PH3-01: direct DB write from worker rejected
- [ ] All state mutations route through StateIntegration → single-writer
- [ ] No worker process holds a DB write handle

**Verification:** Code audit + SEC-PH3-01 test + grep for writer imports

### Gate 4: Lease Safety (PROM-PH3-PASS-04)
**Criteria:**
- [ ] SEC-PH3-02: stale lease (old epoch) rejected
- [ ] Process epoch immutable per pool
- [ ] Monotonic token per resource verified
- [ ] Cross-restart safety: new pool → new epoch → old leases invalid

**Verification:** SEC-PH3-02 + fencing tests + epoch mismatch test

### Gate 5: State Consistency (PROM-PH3-PASS-05)
**Criteria:**
- [ ] 3-cycle crash/recovery: state consistent after each cycle
- [ ] Journal/state agreement verified post-recovery
- [ ] No orphaned leases after recovery
- [ ] Idempotency: no double-execution across cycles

**Verification:** Integration test (3-cycle) + journal replay validation

---

## Evidence Artifacts

### Required Deliverables
1. **`docs/verification/section-3-evidence-report.md`**
   - Full PROM-PH3 exit gate report
   - Test execution logs (all 78 tests)
   - Recovery simulation traces
   - Code audit results (writer confinement)

2. **`docs/verification/section-3-test-summary.md`**
   - Test breakdown by task (T3.1–T3.5)
   - Failure-path coverage matrix
   - Security test results (SEC-PH3-01 through 05)

3. **`scripts/verify_section3.py`**
   - Executable verification suite (18 checks)
   - Auto-runs: test pass, ruff, mypy, writer confinement grep, migration pinning

---

## Regression Prevention

### New Regression Flags
| Flag | Description | Test |
|------|-------------|------|
| **REGR-PH3-01** | Worker cannot bypass single-writer | SEC-PH3-01 |
| **REGR-PH3-02** | No blind resume from RUNNING | SEC-PH3-04 |
| **REGR-PH3-03** | Stale lease rejected (process epoch) | SEC-PH3-02 |
| **REGR-PH3-04** | Output bounded (no OOM) | SEC-PH3-03 |
| **REGR-PH3-05** | Cancellation atomic (no dual state) | SEC-PH3-05 |

### Inherited PH-2 Flags (must remain green)
- REGR-0001: Atomic rollback on pre-commit failure
- REGR-0002: Append-only rewrite prevention
- REGR-0003: Partial migration corruption prevention

---

## Verification Suite Checks (verify_section3.py)

```
✓ Check 01: Worker module files exist (pool, dispatcher, execution, recovery, lease_coordinator)
✓ Check 02: WorkerPool class defined with lifecycle methods
✓ Check 03: TaskExecutor class with execute/cancel
✓ Check 04: StateIntegration routes to _OrchestratorStateWriter
✓ Check 05: LeaseCoordinator wraps LeaseManager
✓ Check 06: _OrchestratorStateWriter NOT exported from workers __init__
✓ Check 07: Recovery module (reconciliation integration)
✓ Check 08: All 78 tests pass
✓ Check 09: ruff linting passes
✓ Check 10: mypy --strict passes
✓ Check 11: SEC-PH3-01 (single-writer confinement) test exists
✓ Check 12: SEC-PH3-02 (fencing) test exists
✓ Check 13: SEC-PH3-03 (output bounds) test exists
✓ Check 14: SEC-PH3-04 (no blind resume) test exists
✓ Check 15: SEC-PH3-05 (atomic cancellation) test exists
✓ Check 16: Failure-path tests (crash, timeout, lease expiry) exist
✓ Check 17: Integration test (3-cycle recovery) exists
✓ Check 18: PH-2 regression tests still pass (93 tests)

TOTAL: 18/18 → PROM-PH3 EXIT GATE: PASS
```

---

## Exit Criteria Summary

**PH-3 is COMPLETE when:**
- ✓ All 5 promotion gates pass (PROM-PH3-PASS-01 through 05)
- ✓ 78 PH-3 tests + 93 PH-2 tests = 171 total tests passing
- ✓ ruff + mypy --strict clean
- ✓ verify_section3.py: 18/18 checks pass
- ✓ Evidence artifacts complete
- ✓ HANDOFF-PH3.md written
- ✓ 5 new regression flags cleared + 3 PH-2 flags green

**Handoff → PH-4 (Model Routing) / PH-5 (Sandbox):**
- Worker Engine provides: WorkerPool, ExecutionResult, event stream
- PH-4 consumes: routing decisions feed worker task assignment
- PH-5 consumes: sandbox wraps worker execution

