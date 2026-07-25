# PH-3 Failure, Recovery & Rollback Analysis

**Phase:** PH-3 (Worker Engine)  
**Authority:** `01M §5` (reconciliation), `01R` R3 (no blind resume)  
**Base:** PH-2 Orchestrator

---

## Failure Taxonomy

### Class 1: Worker Process Failures
| Failure | Cause | Detection | Recovery |
|---------|-------|-----------|----------|
| **F1.1 Process crash** | OOM, segfault, unhandled exception | `process.poll()` returns exit_code | Mark FAILED (heartbeat_loss); return worker to pool |
| **F1.2 Hung process** | Deadlock, infinite loop | Wall-clock timeout | SIGTERM → SIGKILL; mark FAILED (timeout) |
| **F1.3 Zombie process** | Improper cleanup | pid exists but unresponsive | Reap; mark FAILED; restart worker |

### Class 2: State Coordination Failures
| Failure | Cause | Detection | Recovery |
|---------|-------|-----------|----------|
| **F2.1 Lease expiry mid-task** | Renewal missed; clock skew | `validate_token()` false | Mark FAILED (lease_expiry); no resume |
| **F2.2 State writer contention** | Concurrent orchestrator write | `apply_transition()` raises | Retry 3× backoff; 4th → BLOCKED |
| **F2.3 State mismatch** | Journal/state divergence | `state_reader` != expected | QUARANTINED (manual review) |
| **F2.4 Process epoch stale** | Pool restart during task | epoch check fails | Reject lease; force pool restart |

### Class 3: Data Integrity Failures
| Failure | Cause | Detection | Recovery |
|---------|-------|-----------|----------|
| **F3.1 Output overflow** | Huge task output | Stream size limit (512MB) | Truncate; mark FAILED (output_overflow) |
| **F3.2 Partial state commit** | Crash during apply_transition | Journal incomplete | Reconcile on startup; BLOCKED |
| **F3.3 Duplicate execution** | Retry after ambiguous failure | idempotency_key collision | Deduplicate; return cached result |

---

## Recovery Procedures

### R1: Worker Crash Recovery
```
DETECT: process.poll() returns non-None during RUNNING
  ↓
CAPTURE: log heartbeat_loss event to journal (sequence-ordered)
  ↓
TRANSITION: _OrchestratorStateWriter.apply_transition(
    task_id, RUNNING → FAILED, cause="heartbeat_loss", actor=pool_id
)
  ↓
RELEASE: LeaseCoordinator.release_task_lease(lease)
  ↓
RECLAIM: return worker slot to IDLE pool
```

### R2: Startup Reconciliation (Crash Recovery)
```
STARTUP: WorkerPool initializes; new process_epoch generated
  ↓
RECONCILE: reconcile_startup() scans all task states
  ↓
MAP (per 01M §5):
    QUEUED           → RESUMABLE   (safe to re-dispatch)
    RUNNING          → BLOCKED     (NO blind resume; R3)
    PLANNING         → BLOCKED     (in-flight; needs verification)
    AWAITING_APPROVAL→ BLOCKED     (approval state; PH-4 resumes)
    VERIFYING        → BLOCKED
    terminal states  → unchanged   (COMPLETE/CANCELLED/ROLLED_BACK)
  ↓
QUARANTINE: any state where stored ≠ replay ≠ reconcile → QUARANTINED
```

**Critical Rule (R3):** RUNNING tasks NEVER auto-resume. They map to BLOCKED, requiring
explicit human/approval-engine verification before re-execution.

### R3: Lease Expiry Recovery
```
RENEWAL: TaskExecutor renews every (ttl_seconds / 2)
  ↓
FAILURE: validate_token() returns false (epoch mismatch or released)
  ↓
CAPTURE: log lease_expiry event; note token, epoch
  ↓
TRANSITION: RUNNING → FAILED (cause="lease_expiry")
  ↓
NO RESUME: task must be re-dispatched from scratch (new lease, new token)
```

### R4: State Writer Contention Recovery
```
ATTEMPT: apply_transition() raises (e.g., SQLite BUSY, lock timeout)
  ↓
RETRY LOOP (max 3):
    wait backoff (1s, 2s, 4s + jitter)
    re-attempt apply_transition()
  ↓
SUCCESS: proceed
  ↓
EXHAUSTED (4th failure):
    log to journal (manual_review_required)
    mark task BLOCKED
    escalate to operator (PH-4 approval queue)
```

---

## Rollback Boundaries

### What CAN Be Rolled Back
- **Worker process state:** disposable; no persistent state; recreate on demand
- **In-flight execution:** cancel via SIGTERM; task returns to BLOCKED/FAILED
- **Lease grants:** auto-expire (TTL) or explicit release; no manual cleanup

### What CANNOT Be Rolled Back (Append-Only)
- **Journal events:** immutable; append-only (SEC-PH2-02)
- **State transitions:** recorded permanently; corrections via new events (not edits)
- **Memory records:** insert-by-correction (R5); prior records marked SUPERSEDED

### Rollback Safety Guarantees
1. **No data loss on crash:** task state persisted to Orchestrator DB before/after each transition
2. **No blind resume:** RUNNING → BLOCKED on reconciliation (R3)
3. **No orphaned leases:** TTL ensures cleanup; process epoch prevents cross-restart reuse
4. **No partial state corruption:** atomic transitions; retry on contention; BLOCKED on exhaustion

---

## Recovery Testing Matrix

| Test | Scenario | Expected Outcome | Task |
|------|----------|------------------|------|
| **RT-1** | Kill worker mid-execution | FAILED (heartbeat_loss); worker reclaimed | T3.4 |
| **RT-2** | Restart pool during RUNNING task | reconcile → BLOCKED (no resume) | T3.4 |
| **RT-3** | Lease expires (no renewal) | FAILED (lease_expiry); no resume | T3.4 + T3.5 |
| **RT-4** | Task exceeds deadline | SIGTERM → SIGKILL → FAILED (timeout) | T3.2 + T3.4 |
| **RT-5** | Output exceeds 512MB | Truncate; FAILED (output_overflow) | T3.2 |
| **RT-6** | State writer BUSY (contention) | Retry 3×; success or BLOCKED | T3.3 + T3.4 |
| **RT-7** | State/journal mismatch | QUARANTINED (manual review) | T3.4 |
| **RT-8** | Process epoch mismatch (old lease) | Lease rejected; pool restart | T3.5 |
| **RT-9** | Duplicate task dispatch | Deduplicate via idempotency_key | T3.3 |
| **RT-10** | 3-cycle crash/recovery | State consistent after each cycle | Integration |

---

## Idempotency & Deduplication

**Every task execution links to a state transition via idempotency_key.**

```python
idempotency_key = f"{task_id}:{execution_attempt}:{worker_pid}:{output_hash}"
```

**Deduplication:**
- If apply_transition() detects duplicate idempotency_key (UNIQUE constraint):
  - Return existing StateTransitionEvent (already recorded)
  - Skip re-execution (result already known)

**Guarantees:**
- Task never double-executes (unless explicitly re-dispatched with new attempt number)
- Ambiguous failure (crash after state write) → recovery uses idempotency to detect completion

---

## Failure Escalation Path

```
Worker Failure
    ↓
[Automatic Recovery Attempt]
    ↓ (success)
    Continue
    ↓ (failure, 3× exhausted)
[Mark BLOCKED]
    ↓
[Operator Review (PH-4 approval queue)]
    ↓ (approved resume)
    Re-dispatch task (new attempt)
    ↓ (rejected)
    Mark ROLLED_BACK or CANCELLED
```

