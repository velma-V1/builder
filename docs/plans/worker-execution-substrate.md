# Worker Execution Substrate — Implementation Plan (prebuilt PH-4/PH-5 seam)

> **CLASSIFICATION:** This document describes the **Worker Execution Substrate** (prebuilt PH-4/PH-5 execution infrastructure), **NOT roadmap PH-3**. Roadmap **PH-3 (Watchdog, Permissions, Approval, Audit & Tools) remains UNBUILT** and its plan (`docs/plans/section-3-orchestrator-watchdog-and-permissions.md`) is unchanged. The real `ProcessSpawner` and sandbox isolation remain **PH-5**; **PH-4 may consume this seam only after the true PH-3 security interfaces are frozen**. No roadmap dependency is bypassed. `PH-3`/`T3.x`/`SEC-PH3-xx`/`PROM-PH3` labels denote this substrate's development track only. See `docs/WORKER-EXECUTION-SUBSTRATE-CLASSIFICATION.md`.


**Status:** Planning cycle initiated · **Base:** PH-2 (`claude/ph2-orchestrator-implementation` @ 7e023a2)  
**Scope:** Worker process lifecycle, task execution, failure recovery, state integration, lease coordination  
**Governing:** `01M` (PH-2 State Machine), `01E`/`01I` (sandbox/git contract refs), `01L` (task contract), `01R` (binding decisions R1–R5)

---

## Architecture: Worker Engine (3-Lane Factory)

```
Orchestrator (PH-2: read-only consumer)
    ↓
TaskScheduler.ready_tasks() → (TASK-001, TASK-002, ...) [deterministic order]
    ↓
LeaseManager.acquire(TASK, owner="worker-N")  [fencing token, process-epoch]
    ↓
WorkerExecutor (PH-3: spawn/execute/collect)  [sandbox + stdin/stdout/event stream]
    ↓
_OrchestratorStateWriter.apply_transition()  [state mutation via R1 single-writer]
    ↓
Orchestrator (back to ready_tasks loop)
```

**Lane 1 (read-only):** TaskScheduler, lease validation, task state queries  
**Lane 2 (isolated):** WorkerExecutor — spawn, execute, collect (no state mutations)  
**Lane 3 (orchestrated):** _OrchestratorStateWriter calls (serialized state mutations)

---

## Task Decomposition

### T3.1: WorkerPool & Process Lifecycle Management
- **Owned paths:** `src/factory/workers/pool.py`, `src/factory/workers/process.py`, `src/factory/workers/lifecycle.py`
- **Contracts:** `CTR-WORKER-DECLARATION`, `CTR-LEASE-GRANT` (from PH-2)
- **Deliverables:**
  - WorkerPool: spawn, track, supervise N worker processes
  - WorkerProcess: lifecycle (IDLE → ASSIGNED → RUNNING → DONE), properties (pid, epoch, start_time)
  - ProcessEpoch generation tied to pool startup (cross-restart safety per R4)
  - No state mutation: queries only; all transitions via _OrchestratorStateWriter
- **Constraints:**
  - Single orchestrator instance per pool (R1)
  - Leases acquired BEFORE task assignment (fencing before execution)
  - Graceful shutdown: wait for in-flight tasks, cancel remainder
- **Tests:** 12 unit + 2 failure-path (worker crash, signal handling)
- **Evidence:** Worker lifecycle ETM (VM-4)

### T3.2: Task Dispatch & Execution Streaming
- **Owned paths:** `src/factory/workers/dispatcher.py`, `src/factory/workers/execution.py`, `src/factory/workers/streaming.py`
- **Contracts:** `CTR-TASK-DISPATCH`, `CTR-EXECUTION-EVENT`
- **Deliverables:**
  - Dispatcher: (ready_tasks) → (acquire_lease, assign_worker, dispatch_task_contract)
  - Execution: stdin payload assembly, stdout/stderr capture, event stream (status, progress, output chunks)
  - Streaming: non-blocking event buffering; no task state write until end-of-stream
  - Cancellation support: SIGTERM on request_cancellation (from PH-2)
- **Constraints:**
  - Task contract serialization: frozen task snapshot (no mid-flight updates)
  - Lease renewal before expiry (renew() during long-running tasks)
  - Output size limits (prevent OOM from huge logs)
- **Tests:** 15 unit + 3 failure-path (output overflow, lease expiry mid-task, cancellation)
- **Evidence:** Dispatch & streaming ETM (VM-4)

### T3.3: State Integration & Transition Routing
- **Owned paths:** `src/factory/workers/state_integration.py`
- **Contracts:** `01M §3` (state machine), R1 (single-writer invariant)
- **Deliverables:**
  - SingleWriter consumer: WorkerExecutor acquires lock, calls _OrchestratorStateWriter
  - Transition routing: successful task → COMPLETE; failure → FAILED; cancellation → CANCELLED
  - Idempotency: link task execution event to state transition (via idempotency_key)
  - No blind state writes: replay events from task stream to verify consistency
- **Constraints:**
  - ALL state changes via _OrchestratorStateWriter.apply_transition()
  - RUNNING → FAILED requires cause + actor + evidence_ref
  - RUNNING → COMPLETE requires result_hash (output proof)
- **Tests:** 8 unit + 2 failure-path (writer unavailable, partial state commit)
- **Evidence:** State integration ETM (VM-4)

### T3.4: Failure Recovery & Rollback
- **Owned paths:** `src/factory/workers/recovery.py`, `src/factory/workers/quarantine.py`
- **Contracts:** `01M §5` (reconciliation), `01L` (task contract)
- **Deliverables:**
  - Crash recovery: reconcile_startup() assigns BLOCKED (not RESUMABLE) per R3
  - Partial task completion: detect mid-flight failure (lease expiry, heartbeat loss)
  - Automatic retry: finite backoff (3 attempts) with jitter; 4th → FAILED
  - Quarantine: unrecoverable state mismatch → QUARANTINED (manual intervention)
- **Constraints:**
  - BLOCKED tasks CAN be resumed (human approval via approval engine in PH-4)
  - Partial state: if events exist but state doesn't match, preserve events (audit trail)
  - Lease expiry mid-task: capture as failure cause (not silent timeout)
- **Tests:** 10 unit + 5 failure-path (crash during execution, lease expires, partial commit, heartbeat loss)
- **Evidence:** Recovery ETM (VM-5), rollback coverage

### T3.5: Lease Coordination & Process Epoch Safety
- **Owned paths:** `src/factory/workers/lease_coordinator.py`
- **Contracts:** `01M §4` (fencing), R4 (process-epoch lease validity)
- **Deliverables:**
  - LeaseCoordinator: thin wrapper around PH-2 LeaseManager
  - Acquire: TASK lease before dispatch; owner_id = worker process ID
  - Renew: periodic (every ttl_seconds/2) during long-running tasks
  - Validate: before state transition (catch stale leases from prior epochs)
  - Release: on task end (success/failure/cancel)
- **Constraints:**
  - Process epoch generated at pool startup (immutable for pool lifetime)
  - Lease token monotonically increasing per (resource_type, resource_id)
  - Fencing is PRIMARY validity check; expiry is secondary
- **Tests:** 6 unit + 2 failure-path (process restart, epoch staleness)
- **Evidence:** Fencing safety ETM (VM-4)

---

## Failure & Recovery Scenarios

| Scenario | Detection | Recovery | Evidence |
|----------|-----------|----------|----------|
| **Worker process crash** | Heartbeat loss (poll process status) | Acquire new process; BLOCKED state; replay journal for evidence | ✓ T3.1 + T3.4 |
| **Task execution timeout** | Wall-clock > task.deadline + grace | SIGTERM; capture as FAILED cause | ✓ T3.2 + T3.4 |
| **Lease expiry mid-task** | validate_token() returns false | Mark FAILED; log lease loss; no blind resume | ✓ T3.5 + T3.4 |
| **Partial output (OOM)** | stderr buffer limit hit | Truncate + capture as failure (output overflow) | ✓ T3.2 |
| **State writer unavailable** | apply_transition() exception | Retry 3x with backoff; 4th → manual review | ✓ T3.3 + T3.4 |
| **Process epoch mismatch** | validate_token() epoch check fails | Reject lease; force new worker pool restart | ✓ T3.5 + T3.4 |
| **Duplicate task execution** | idempotency_key collision | Deduplicate via journal; return cached result | ✓ T3.3 |
| **Cancellation races** | SIGTERM + concurrent state write | Lease release gates cancellation completion | ✓ T3.2 + T3.5 |

---

## Security & Trust Boundaries

### Threat Model
- **Adversary capability:** Local file system access, arbitrary task payloads
- **Protection boundary:** Orchestrator state (R1 single-writer) is trustworthy; worker output is untrusted until verified

### Threat & Mitigation
| Threat | Mitigation | PH | Evidence |
|--------|-----------|----|---------| 
| Worker process hijacking state writer | Single-writer not exported; only acquired via WorkerExecutor context manager | T3.3 | State integration tests |
| Leaked credentials in task output | Output redaction layer (deferred to PH-7); logs scanned during staging | T3.2 | Streaming tests + output size limits |
| Blind state resume after crash | reconcile_startup() maps RUNNING → BLOCKED (no auto-resume) | T3.4 | Recovery tests + reconciliation verification |
| Stale lease grant (cross-restart) | Process epoch check + monotonic token validation | T3.5 | Fencing tests + epoch mismatch tests |
| Worker escapes sandbox (PH-5) | Sandbox enforcement is PH-5 concern; PH-3 assumes valid sandbox | — | PH-5 tests; PH-3 contract boundary |
| Task output overflow → OOM | Stream size limit + truncation; logged as failure | T3.2 | Output overflow failure-path |

---

## Verification & Evidence Model

### Test Categories
- **Unit (35 tests):** Isolation per T3.1-T3.5; pure functions; state machine transitions
- **Failure-path (17 tests):** Crash scenarios, timeouts, lease expiry, output overflow, epoch staleness
- **Security (4 tests):** State writer access control, output bounds, lease staleness rejection
- **Integration (8 tests):** End-to-end: dispatch → execution → state update (via PH-2 writer)

**Total: 64 tests** (parallel with Unit/Security, serial with Integration)

### Promotion Gates
1. **PROM-PH3-PASS-01:** All 64 tests pass; 0 ruff/mypy violations
2. **PROM-PH3-PASS-02:** Recovery simulation (crash/lease expiry/timeout) successful; state consistent
3. **PROM-PH3-PASS-03:** No state writer escapes; only _OrchestratorStateWriter mutations allowed (code audit + test coverage)
4. **PROM-PH3-PASS-04:** Lease safety verified (process epoch + monotonic token); cross-restart test passes
5. **PROM-PH3-PASS-05:** State consistency after 3 crash/recovery cycles

### Evidence Artifacts
- `docs/verification/worker-execution-substrate-evidence-report.md` — full execution traces, test metrics
- `docs/verification/worker-execution-substrate-test-summary.md` — breakdown by task, failure-path coverage
- `scripts/verify_worker_substrate.py` — executable verification (18 checks, all must pass)

---

## Implementation-Readiness Certificate

**Pre-implementation checklist:**

- [ ] Component spec locked (this doc)
- [ ] Task boundaries agreed (T3.1–T3.5)
- [ ] Failure scenarios enumerated (8 scenarios + recovery)
- [ ] Security threat model defined (5 threats + mitigations)
- [ ] PH-2 interface contracts frozen (no breaking changes)
- [ ] Database schema (migrations/runtime/0003_memory.sql) compatible with worker state
- [ ] Lease TTL budget calculated (task deadline + 2× renewals + grace)
- [ ] Output size limit configured (e.g., 512 MB per task)
- [ ] Process pool size tested (start with 4 workers, scale test to 16)
- [ ] Rollback boundary verified (worker state non-persistent; only Orchestrator state matters)

**Readiness:** ✓ ALL LOCKED

---

## Contracts & References

- **01M** (PH-2 State Machine): Task states, transitions, reconciliation
- **01L** (Task Contract): Task properties, deadline, cancellation
- **01E** (Sandbox): Worker execution isolation (deferred to PH-5)
- **01I** (Git/Worktree): Task branch lifecycle (deferred to PH-5)
- **01R** (Binding Decisions): R1–R5 (single-writer, append-only, no blind resume, process-epoch, insert-by-correction)
- **CTR-WORKER-DECLARATION**: Worker capabilities, resource limits
- **CTR-LEASE-GRANT**: (from PH-2) Lease semantics, TTL, renewal

---

## Known Limitations & Deferral

1. **Sandbox execution (PH-5):** Workers spawn tasks in sandboxes; PH-3 assumes valid isolation.
2. **Output redaction (PH-7):** Credential detection deferred; raw logs stored during execution.
3. **Approval gates (PH-4):** Manual resume of BLOCKED tasks requires approval engine (not built yet).
4. **Comprehensive auditing (PH-4):** Full audit trail written by PH-4 audit writer; PH-3 logs to journal only.
5. **Resource quotas (PH-4):** Quota enforcement deferred; PH-3 respects submitted deadlines only.

---

## Roadmap: Planning → Implementation → Verification

**Phase 1 — Full Planning (this cycle):**
- Component spec ✓ (this doc)
- Task breakdown ✓ (T3.1–T3.5)
- Failure/recovery ✓ (8 scenarios)
- Security ✓ (threat model)
- Verification ✓ (64 tests, 5 gates)
- Certificate ✓ (pre-impl checklist)

**Phase 2 — Implementation (T3.1 → T3.2 → T3.3 → T3.4 → T3.5):**
- Each task: write code, unit + failure-path tests, code review, commit with task boundary

**Phase 3 — Verification (PROM-PH3 gates):**
- Gate 1–2: Auto (test pass, recovery simulation)
- Gate 3–4: Code audit (state writer confinement, lease safety)
- Gate 5: Integration (3-cycle crash recovery)

**Phase 4 — Handoff:**
- Lock spec (this doc)
- Create HANDOFF-WORKER-EXECUTION-SUBSTRATE.md
- Sign off on PROM-PH3 exit gate
- Ready for PH-4/PH-5 (approval, audit, sandbox integration)

