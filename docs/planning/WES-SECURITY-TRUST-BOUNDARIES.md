# Worker Execution Substrate — Security & Trust Boundary Analysis

> **CLASSIFICATION:** This document describes the **Worker Execution Substrate** (prebuilt PH-4/PH-5 execution infrastructure), **NOT roadmap PH-3**. Roadmap **PH-3 (Watchdog, Permissions, Approval, Audit & Tools) remains UNBUILT** and its plan (`docs/plans/section-3-orchestrator-watchdog-and-permissions.md`) is unchanged. The real `ProcessSpawner` and sandbox isolation remain **PH-5**; **PH-4 may consume this seam only after the true PH-3 security interfaces are frozen**. No roadmap dependency is bypassed. `PH-3`/`T3.x`/`SEC-PH3-xx`/`PROM-PH3` labels denote this substrate's development track only. See `docs/WORKER-EXECUTION-SUBSTRATE-CLASSIFICATION.md`.


**Track:** Worker Execution Substrate (substrate-track label; NOT roadmap PH-3)  
**Authority:** `01R` R1 (single-writer), `01M` (state machine), `01E` (sandbox — deferred to PH-5)  
**Base:** PH-2 Orchestrator

---

## Trust Model

### Trust Zones

```
┌─ ZONE 1: TRUSTED (Orchestrator Core) ─────────────────┐
│  - _OrchestratorStateWriter (single-writer, R1)       │
│  - SQLiteOrchestratorStateReader (read-only)          │
│  - LeaseManager (fencing authority)                   │
│  - Task state DB (source of truth)                    │
└────────────────────────────────────────────────────────┘
         ↑ (controlled interface)
┌─ ZONE 2: SEMI-TRUSTED (Worker Engine) ────────────────┐
│  - WorkerPool (spawns workers; no state write)        │
│  - TaskExecutor (executes; collects events)           │
│  - StateIntegration (routes to Zone 1 writer)         │
│  - LeaseCoordinator (acquires/renews leases)          │
└────────────────────────────────────────────────────────┘
         ↑ (task contract in; events out)
┌─ ZONE 3: UNTRUSTED (Worker Process Output) ───────────┐
│  - stdout/stderr (arbitrary task output)              │
│  - execution result (untrusted until verified)        │
│  - task payload (may contain adversarial content)     │
└────────────────────────────────────────────────────────┘
```

### Trust Boundary Rules

1. **Zone 3 → Zone 2:** All worker output is untrusted. Size-limited, buffered, not executed.
2. **Zone 2 → Zone 1:** State mutations ONLY via _OrchestratorStateWriter (R1). No direct DB writes.
3. **Zone 1 → Zone 2:** Read-only access to state; leases granted with fencing tokens.

---

## Threat Model

### Adversary Capabilities
- Local file system access (can read/write within sandbox)
- Arbitrary task payloads (may attempt injection, overflow, escape)
- Process manipulation (may attempt to spawn subprocesses, signal handlers)

### Adversary Goals
- Corrupt Orchestrator state (bypass R1 single-writer)
- Escape sandbox (PH-5 concern, but PH-3 must not weaken boundaries)
- Steal leases (impersonate other workers via stale tokens)
- Exhaust resources (OOM via output overflow)

---

## Threats & Mitigations

### T-01: State Writer Bypass
**Threat:** Worker process directly writes to Orchestrator DB, bypassing R1 single-writer.  
**Impact:** State corruption; audit trail loss; concurrent write races.  
**Mitigation:**
- `_OrchestratorStateWriter` NOT exported from package `__init__` (structural enforcement)
- Only acquired via StateIntegration context manager (mutual exclusion)
- Worker processes have NO DB handle; all state via IPC to StateIntegration
**Test (SEC-PH3-01):** Attempt direct DB write from worker → rejected; only StateIntegration path succeeds.

### T-02: Lease Impersonation (Stale Token)
**Threat:** Worker from prior process epoch presents old lease token to claim task.  
**Impact:** Two workers execute same task; state corruption.  
**Mitigation:**
- Process epoch immutable per pool; generated at startup (R4)
- `validate_token()` checks `process_epoch == pool.process_epoch AND not released`
- Monotonic token per (resource_type, resource_id) prevents replay
**Test (SEC-PH3-02):** Present lease from old epoch → validate_token() returns false; task rejected.

### T-03: Output Overflow (Resource Exhaustion)
**Threat:** Task produces huge output (GB-scale) → OOM kills orchestrator.  
**Impact:** Denial of service; orchestrator crash.  
**Mitigation:**
- Stream size limit: 512 MB total per task (configurable)
- Per-chunk limit: 64 KB
- Non-blocking buffering: events queued; backpressure applied
- On limit hit: truncate; mark FAILED (output_overflow)
**Test (SEC-PH3-03):** Task emits >512MB → truncated at limit; FAILED; orchestrator survives.

### T-04: Blind State Resume (Data Corruption)
**Threat:** After crash, RUNNING task auto-resumes without verification → double-execution.  
**Impact:** Duplicate side effects; inconsistent state.  
**Mitigation:**
- reconcile_startup() maps RUNNING → BLOCKED (R3; never RESUMABLE)
- Resume requires explicit approval (PH-4) or human intervention
- State/journal consistency verified before any resume
**Test (SEC-PH3-04):** Crash during RUNNING → reconcile → BLOCKED (not resumed).

### T-05: Cancellation Race (State Inconsistency)
**Threat:** SIGTERM sent during state write → task marked both CANCELLED and COMPLETE.  
**Impact:** Ambiguous final state; audit confusion.  
**Mitigation:**
- Lease release gates cancellation completion (release AFTER state written)
- Atomic transition: single critical section per state change
- STOPPING intermediate state: RUNNING → STOPPING → CANCELLED (ordered)
**Test (SEC-PH3-05):** Concurrent SIGTERM + state write → deterministic single final state.

---

## Security Invariants

| Invariant | Enforcement | Verification |
|-----------|-------------|--------------|
| **SI-1: Single-writer only** | `_OrchestratorStateWriter` not exported; context-manager acquired | SEC-PH3-01 |
| **SI-2: Fencing primary** | process_epoch + monotonic token + released flag | SEC-PH3-02 |
| **SI-3: Output bounded** | 512MB total, 64KB/chunk limits | SEC-PH3-03 |
| **SI-4: No blind resume** | reconcile_startup RUNNING → BLOCKED | SEC-PH3-04 |
| **SI-5: Atomic cancellation** | lease release gates completion | SEC-PH3-05 |
| **SI-6: Append-only audit** | journal events immutable (SEC-PH2-02 inherited) | Inherited from PH-2 |
| **SI-7: Untrusted output** | worker output never executed; only logged/hashed | Code audit |

---

## Attack Surface Analysis

### Entry Points
1. **Task payload (Zone 3 → Zone 2):** validated against task contract schema; size-limited
2. **Worker output (Zone 3 → Zone 2):** buffered, size-limited, not executed
3. **Lease tokens (Zone 2 → Zone 1):** validated via fencing (epoch + monotonic)
4. **State transitions (Zone 2 → Zone 1):** routed via single-writer only

### Hardening Measures
- **Input validation:** task contracts schema-checked before dispatch
- **Output bounds:** hard limits prevent resource exhaustion
- **Least privilege:** workers have no DB handle, no orchestrator authority
- **Fencing:** cross-restart lease safety via process epoch
- **No code execution:** worker output treated as data, never eval'd

---

## Deferred Security Concerns (PH-5+)

| Concern | Deferred To | Rationale |
|---------|-------------|-----------|
| Sandbox escape prevention | PH-5 | Sandbox isolation is PH-5 scope; PH-3 assumes valid sandbox |
| Credential redaction | PH-7 | Output redaction during staging; PH-3 stores raw logs |
| Network isolation | PH-5 | Network broker (default-deny) is PH-5 |
| Approval-gated deletion | PH-4 | Permission engine (Dec B) is PH-4 |
| Full audit chain | PH-4 | Hash-chained audit writer is PH-4; PH-3 logs to journal |

**Note:** PH-3 must NOT weaken future boundaries. Worker execution assumes a valid sandbox
(provided by PH-5). PH-3's responsibility is state integration safety and lease coordination.

---

## Security Test Coverage

| Test | Invariant | Type |
|------|-----------|------|
| SEC-PH3-01 | SI-1 (single-writer) | Adversarial: direct DB write attempt |
| SEC-PH3-02 | SI-2 (fencing) | Adversarial: stale lease token |
| SEC-PH3-03 | SI-3 (output bounds) | Resource: output overflow |
| SEC-PH3-04 | SI-4 (no blind resume) | Recovery: crash during RUNNING |
| SEC-PH3-05 | SI-5 (atomic cancellation) | Race: SIGTERM + state write |

**Total: 5 security tests** (all must pass for PROM-PH3-PASS-03).

