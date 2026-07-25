# PH-3 Implementation-Readiness Certificate

**Phase:** PH-3 (Worker Engine)  
**Base:** PH-2 Orchestrator (`claude/ph2-orchestrator-implementation` @ 7e023a2)  
**Branch:** `claude/ph3-worker-engine`  
**Date:** 2026-07-25

---

## Certification Statement

This certificate attests that PH-3 (Worker Engine) has completed its full planning
cycle and is ready for implementation. All prerequisite analysis is locked.

---

## Planning Cycle Completeness

| Pass | Document | Status |
|------|----------|--------|
| **1. Component Spec** | `docs/specifications/components/worker-engine-spec.md` | ✓ LOCKED |
| **2. Implementation Plan** | `docs/plans/section-3-worker-engine.md` | ✓ LOCKED |
| **3. Failure/Recovery/Rollback** | `docs/planning/PH3-FAILURE-RECOVERY-ROLLBACK.md` | ✓ LOCKED |
| **4. Security/Trust Boundaries** | `docs/planning/PH3-SECURITY-TRUST-BOUNDARIES.md` | ✓ LOCKED |
| **5. Verification/Evidence/Promotion** | `docs/planning/PH3-VERIFICATION-EVIDENCE-PROMOTION.md` | ✓ LOCKED |
| **6. Readiness Certificate** | `docs/planning/PH3-IMPLEMENTATION-READINESS-CERTIFICATE.md` | ✓ THIS DOC |

---

## PH-2 Interface Freeze Verification

**Verified against PH-2 source (@ 7e023a2):**

| Interface | Signature | Verified |
|-----------|-----------|----------|
| `_OrchestratorStateWriter.apply_transition` | keyword-only: `(*, task_id, expected_current_state: TaskState\|None, new_state, cause, actor, linked_reference=None, idempotency_key=None) → StateTransitionEvent` | ✓ |
| `SQLiteOrchestratorStateReader.get_task` | `(task_id) → TaskRuntimeRecord \| None` | ✓ |
| `SQLiteOrchestratorStateReader.get_events` | `(task_id) → tuple[StateTransitionEvent, ...]` | ✓ |
| `TaskScheduler.ready_tasks` | `(dependency_graph, states) → tuple[str, ...]` | ✓ |
| `LeaseManager.acquire` | `(resource_type, resource_id, owner_id, ttl_seconds: int) → Lease` | ✓ |
| `LeaseManager.renew` | `(lease, ttl_seconds: int) → Lease` | ✓ |
| `LeaseManager.release` | `(lease) → None` | ✓ |
| `LeaseManager.validate_token` | `(resource_type, resource_id, token) → bool` | ✓ |

**Schema Freeze:** migrations 0001–0003 locked (SHA-256 pinned). PH-3 may only APPEND (0004+).

---

## Task Decomposition Checklist

| Task | Owned Paths | Contracts | Tests | Ready |
|------|-------------|-----------|-------|-------|
| **T3.1 WorkerPool** | `src/factory/workers/pool.py, process.py, lifecycle.py` | CTR-WORKER-DECLARATION | 14 | ✓ |
| **T3.2 Dispatch/Streaming** | `src/factory/workers/dispatcher.py, execution.py, streaming.py` | CTR-TASK-DISPATCH, CTR-EXECUTION-EVENT | 19 | ✓ |
| **T3.3 State Integration** | `src/factory/workers/state_integration.py` | 01M §3, R1 | 11 | ✓ |
| **T3.4 Recovery/Rollback** | `src/factory/workers/recovery.py, quarantine.py` | 01M §5 | 16 | ✓ |
| **T3.5 Lease Coordination** | `src/factory/workers/lease_coordinator.py` | 01M §4, R4 | 9 | ✓ |
| **Integration** | `tests/workers/integration/` | E2E | 9 | ✓ |

---

## Binding Decisions Compliance (R1–R5)

| Decision | Application in PH-3 | Enforcement |
|----------|---------------------|-------------|
| **R1 Single-Writer** | All state mutations via _OrchestratorStateWriter | StateIntegration context manager; no worker DB handle |
| **R2 Append-Only Journal** | Execution events logged immutably | Inherited from PH-2 (SEC-PH2-02) |
| **R3 No Blind Resume** | RUNNING → BLOCKED on crash recovery | reconcile_startup() mapping |
| **R4 Process-Epoch Lease** | Leases validated by epoch + token | LeaseCoordinator.validate_current() |
| **R5 Insert-by-Correction** | Memory updates via insert (no UPDATE) | MemoryStore (inherited from PH-2) |

---

## Pre-Implementation Checklist

- [x] Component spec locked (worker-engine-spec.md)
- [x] Task boundaries agreed (T3.1–T3.5)
- [x] Failure scenarios enumerated (F1.1–F3.3, 12 failure modes)
- [x] Recovery procedures defined (R1–R4 recovery)
- [x] Security threat model defined (T-01 through T-05)
- [x] Security invariants specified (SI-1 through SI-7)
- [x] PH-2 interface contracts frozen (8 interfaces verified)
- [x] Database schema compatibility confirmed (0001–0003 locked, 0004+ appendable)
- [x] Lease TTL budget: task_deadline + 2× renewal + grace (60s)
- [x] Output size limit: 512 MB total, 64 KB/chunk
- [x] Process pool size: default 4, scale-test to 16
- [x] Rollback boundary: worker state disposable; only Orchestrator state persistent
- [x] Test plan: 78 tests (51 unit + 14 failure + 5 security + 8 integration)
- [x] Promotion gates: 5 gates (PROM-PH3-PASS-01 through 05)
- [x] Regression flags: 5 new + 3 inherited

---

## Risk Register (PH-3)

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **RSK-1** Process spawning platform differences (WSL2/Linux) | Medium | Medium | Use `subprocess` with explicit args; test on Linux; document Windows/WSL2 boundary |
| **RSK-2** Lease renewal timing (clock skew) | Low | High | Renew at ttl/2; fencing primary check (not wall-clock) |
| **RSK-3** State writer contention (concurrent orchestrator) | Medium | Medium | Retry 3× backoff; BLOCKED on exhaustion |
| **RSK-4** Output overflow (huge task output) | Medium | High | Hard size limits; truncation; FAILED marking |
| **RSK-5** Zombie/orphan processes | Low | Medium | Process-tree termination; explicit reaping |

---

## Implementation Order

```
T3.1 (WorkerPool) 
   ↓ [foundation: process lifecycle]
T3.5 (LeaseCoordinator)
   ↓ [coordination: fencing before dispatch]
T3.2 (Dispatch/Streaming)
   ↓ [execution: task dispatch + event stream]
T3.3 (State Integration)
   ↓ [state: route results to single-writer]
T3.4 (Recovery/Rollback)
   ↓ [resilience: crash/timeout/lease recovery]
Integration (E2E + 3-cycle recovery)
   ↓
PROM-PH3 Exit Gate
```

**Rationale:** Build lifecycle foundation → coordination → execution → state → recovery.
Each task: TDD (test first), code, ruff+mypy, commit at boundary.

---

## Certificate Sign-Off

**Planning Status:** ✓ COMPLETE (6 passes locked)  
**Interface Freeze:** ✓ PH-2 contracts verified (8 interfaces)  
**Schema Compatibility:** ✓ 0001–0003 locked; 0004+ appendable  
**Binding Decisions:** ✓ R1–R5 compliance mapped  
**Test Plan:** ✓ 78 tests across 4 categories  
**Promotion Gates:** ✓ 5 gates defined  

**READY FOR IMPLEMENTATION: T3.1 → T3.5 → Integration → PROM-PH3**

---

## Post-Implementation Update (2026-07-25)

**Status: ✓ IMPLEMENTED AND VERIFIED — PROM-PH3 EXIT GATE PASSED.**

All tasks complete on `claude/ph3-worker-engine`: T3.1 `270300f`, T3.5 `9dd4ac6`,
T3.2 `db1da21`, T3.3 `be048e1`, T3.4 `aaba6fe`, integration+verification `9814401`.
85 PH-3 tests + 93 PH-2 regression = 178 passing; ruff + mypy --strict clean;
`scripts/verify_section3.py` 18/18. Evidence in `docs/verification/section-3-*.md`,
handoff in `HANDOFF-PH3.md`.

**Planned test estimate was 78; delivered 85** (extra coverage in lifecycle, streaming,
recovery edge cases). **Design correction during T3.3:** success path is RUNNING → VERIFYING,
not RUNNING → COMPLETE (01L §3.1 — no worker self-certification); planning docs updated.

---

## Next Action

Begin T3.1 (WorkerPool & Process Lifecycle) with TDD:
1. Write `tests/workers/unit/test_worker_pool.py` (14 tests)
2. Implement `src/factory/workers/pool.py`, `process.py`, `lifecycle.py`
3. ruff + mypy --strict
4. Commit: `T3.1: WorkerPool and process lifecycle management`

