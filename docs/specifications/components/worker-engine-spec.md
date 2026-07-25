# Worker Execution Substrate — Component Specification (CMP-WORKER; prebuilt PH-4/PH-5 seam)

> **CLASSIFICATION:** This document describes the **Worker Execution Substrate** (prebuilt PH-4/PH-5 execution infrastructure), **NOT roadmap PH-3**. Roadmap **PH-3 (Watchdog, Permissions, Approval, Audit & Tools) remains UNBUILT** and its plan (`docs/plans/section-3-orchestrator-watchdog-and-permissions.md`) is unchanged. The real `ProcessSpawner` and sandbox isolation remain **PH-5**; **PH-4 may consume this seam only after the true PH-3 security interfaces are frozen**. No roadmap dependency is bypassed. `PH-3`/`T3.x`/`SEC-PH3-xx`/`PROM-PH3` labels denote this substrate's development track only. See `docs/WORKER-EXECUTION-SUBSTRATE-CLASSIFICATION.md`.


**Authority:** `01M` (State Machine), `01L` (Task Contract), `01R` (Binding Decisions)  
**Scope:** Worker process lifecycle, task execution, state integration, failure recovery  
**Base:** PH-2 Orchestrator (read-only + single-writer)

---

## Component Identity

**CMP-WORKER (Worker Execution Substrate)** — prebuilt PH-4/PH-5 seam (substrate-track "PH-3", **NOT** roadmap PH-3)

Spawns and manages worker processes; assigns tasks; collects execution events; integrates with PH-2 state machine. Does NOT write state directly — all mutations via _OrchestratorStateWriter (R1 single-writer invariant).

---

## Logical Architecture

```
┌─ WorkerPool ────────────────────────────────────────────┐
│                                                         │
│  ┌─ WorkerProcess[0] (IDLE) ─────────────────────┐    │
│  │  pid=1234; epoch=E1; state=IDLE               │    │
│  │  [ready to accept task]                        │    │
│  └────────────────────────────────────────────────┘    │
│                                                         │
│  ┌─ WorkerProcess[1] (ASSIGNED) ────────────────┐     │
│  │  pid=1235; epoch=E1; task_id=TASK-001        │     │
│  │  [waiting for task contract to arrive]       │     │
│  └────────────────────────────────────────────────┘    │
│                                                         │
│  ┌─ WorkerProcess[2] (RUNNING) ──────────────────┐    │
│  │  pid=1236; epoch=E1; task_id=TASK-002        │     │
│  │  [executing stdin → stdout/stderr → events]  │     │
│  │  lease_token=42; expires_at=2026-07-25T...   │     │
│  └────────────────────────────────────────────────┘    │
│                                                         │
│  ┌─ ProcessEpoch ────────────────────────────────┐    │
│  │  epoch="e-1721901453-abc123" (pool startup)  │     │
│  │  [immutable for pool lifetime; tied to all    │     │
│  │   leases from this pool]                      │     │
│  └────────────────────────────────────────────────┘    │
│                                                         │
└─────────────────────────────────────────────────────────┘
         ↓ (Dispatcher)
    TaskScheduler.ready_tasks()
         ↓
    LeaseManager.acquire(TASK, owner_id=worker_pid)
         ↓
    TaskExecutor.execute(task_contract)
         ↓ (StateIntegration)
    _OrchestratorStateWriter.apply_transition()
```

---

## Component Interfaces (Public API)

### WorkerPool
```python
class WorkerPool:
    """Manages N independent worker processes."""
    
    def __init__(self, size: int = 4, timeout_sec: float = 300.0):
        """Initialize pool; generate process_epoch; spawn workers."""
        self.size = size
        self.process_epoch = ProcessEpoch.generate()
        self.workers: list[WorkerProcess] = [...]
    
    def get_available_worker(self) -> WorkerProcess | None:
        """Return IDLE worker or None."""
    
    def assign_task(self, worker: WorkerProcess, task: TaskContract) -> None:
        """Move worker IDLE → ASSIGNED; store task_id."""
    
    def get_worker_status(self, task_id: str) -> WorkerStatus:
        """Query (pid, state, lease_token, task_id)."""
    
    def shutdown(self, graceful: bool = True) -> None:
        """Send SIGTERM to all RUNNING; wait; SIGKILL remainder."""
    
    @property
    def process_epoch(self) -> ProcessEpoch:
        """Immutable epoch tied to pool startup."""
```

### TaskExecutor
```python
class TaskExecutor:
    """Executes single task in worker process; collects events; no state writes."""
    
    def execute(
        self,
        task_contract: TaskContract,
        worker_process: WorkerProcess,
        lease_mgr: LeaseManager,
        state_reader: SQLiteOrchestratorStateReader,
    ) -> ExecutionResult:
        """
        Execute task in worker; stream events; return result.
        
        Contract:
        - Acquire lease BEFORE dispatch
        - Renew lease every (ttl_sec / 2)
        - On task end, validate final state via state_reader
        - Release lease on exit
        - Return ExecutionResult (exit_code, output_hash, events)
        """
    
    def cancel(self, task_id: str) -> None:
        """Send SIGTERM to task process; mark STOPPING."""
```

### StateIntegration
```python
class StateIntegration:
    """Route execution result → state transition via single-writer."""
    
    def finalize(
        self,
        task_id: str,
        execution_result: ExecutionResult,
        state_writer: _OrchestratorStateWriter,
    ) -> StateTransitionEvent:
        """
        Apply execution result to state machine.
        
        - Success (exit_code=0) → RUNNING → VERIFYING  (worker cannot self-certify COMPLETE)
        - Failure (exit_code≠0) → RUNNING → FAILED
        - Cancellation (SIGTERM) → RUNNING → STOPPING → CANCELLED
        - Crash (lease expired) → RUNNING → FAILED (cause: lease_expiry)
        
        Idempotency: link execution to state transition via idempotency_key.
        """
```

### LeaseCoordinator
```python
class LeaseCoordinator:
    """Wrapper around PH-2 LeaseManager for PH-3 task execution."""
    
    def acquire_task_lease(
        self,
        task_id: str,
        worker_pid: int,
        ttl_seconds: int = 300,
    ) -> Lease:
        """Acquire TASK lease; owner_id = worker_pid. PH-2 LeaseManager requires int TTL."""
    
    def renew_lease(self, lease: Lease, ttl_seconds: int = 300) -> Lease:
        """Refresh lease TTL; return new Lease."""
    
    def validate_current(self, task_id: str, lease: Lease) -> bool:
        """Check lease.process_epoch == pool.process_epoch AND not released."""
    
    def release_task_lease(self, lease: Lease) -> None:
        """Mark lease released; invalidates for future use."""
```

---

## State Lifecycle (per Worker)

```
IDLE
 ↓ [assign_task]
ASSIGNED
 ↓ [dispatch task contract to worker process]
RUNNING (+ lease acquired)
 ↓ [task completes OR timeout OR lease expires OR cancelled]
DONE (+ lease released)
 ↓ [reuse]
IDLE
```

**Task State Transitions (via _OrchestratorStateWriter only):**
- QUEUED → PLANNING → RUNNING (dispatch → worker ready to execute)
- RUNNING → VERIFYING (exit_code=0) — worker CANNOT self-certify COMPLETE; success hands
  off to verification (01L §3.1: COMPLETE is reachable only from VERIFYING, enforcing "no
  worker certifies its own work"). VERIFYING → COMPLETE is a later phase.
- RUNNING → FAILED (exit_code≠0 or timeout or lease expiry or output overflow)
- RUNNING → STOPPING → CANCELLED (cancellation; reuses PH-2 request/finalize_cancellation)
- RUNNING → BLOCKED (crash recovery; reconcile_startup)

---

## Execution Event Stream

**Event model (per task execution):**
```python
@dataclass
class ExecutionEvent:
    task_id: str
    sequence: int
    event_type: str  # "START", "PROGRESS", "STDOUT", "STDERR", "HEARTBEAT", "END"
    timestamp: str
    data: dict  # depends on event_type
```

**Sequence within single task execution:**
1. START: {exit_code: None, pid: worker_pid}
2. PROGRESS: {percent_complete: 0–100}
3. STDOUT: {chunk_id: N, data: "..."}
4. HEARTBEAT: {memory_mb: X, cpu_percent: Y}
5. STDERR: {chunk_id: N, data: "..."}
6. END: {exit_code: 0 or non-zero, output_hash: "sha256...", events_captured: N}

**Constraints:**
- Max event payload: 64 KB per chunk (prevent OOM)
- Max total output: 512 MB per task (configurable)
- Non-blocking buffering (events queued; no thread-blocking waits)

---

## Failure Detection & Recovery

### Heartbeat Loss
- WorkerPool polls each RUNNING worker every 5 seconds (configurable)
- If process.poll() indicates crash: transition to FAILED, capture `heartbeat_loss` as cause

### Lease Expiry
- TaskExecutor renews lease every (ttl_seconds / 2)
- If renewal fails (validate_token returns false): transition to FAILED, capture `lease_expiry` as cause

### Task Timeout
- TaskExecutor checks wall-clock vs task.deadline + grace_period (e.g., 60 sec)
- If exceeded: SIGTERM; wait 10 sec; SIGKILL; transition to FAILED

### Partial State (Crash During State Write)
- If _OrchestratorStateWriter.apply_transition() fails mid-commit:
  - Retry 3× with backoff (1s, 2s, 4s)
  - 4th failure: log event to journal, manually mark task BLOCKED (operator review)

### Crash Recovery (Startup)
- WorkerPool.shutdown() called on pool teardown
- On next startup: reconcile_startup() maps all RUNNING tasks → BLOCKED
- Never auto-resume from RUNNING (R3 constraint)

---

## Synchronization & Concurrency

### Single-Writer Invariant (R1)
- Only _OrchestratorStateWriter may mutate task state
- TaskExecutor acquires writer lock (mutual exclusion with Orchestrator)
- Write is atomic: one state transition per task per critical section

### Lease-Based Coordination
- Lease token is monotonically increasing per (resource_type, resource_id)
- Process epoch staleness check: `lease.process_epoch == pool.process_epoch`
- Fencing prevents cross-restart state corruption

### No Blind State Writes
- Before finalizing task state, TaskExecutor validates via state_reader
- If stored state ≠ expected, mark QUARANTINED (manual intervention)

---

## Error Cases & Handling

| Error | Detection | Response |
|-------|-----------|----------|
| Worker process crash | heartbeat_loss (poll returns non-None) | Transition to FAILED; log to journal; return to pool |
| Lease expiry during execution | validate_token() → false | Transition to FAILED; note lease_expiry cause |
| Task output overflow (>512MB) | stream size limit | Truncate; mark FAILED; save up-to limit |
| Timeout (>deadline + grace) | wall-clock check | SIGTERM; SIGKILL; mark FAILED |
| State writer unavailable | apply_transition() exception | Retry 3×; 4th: manual review (mark BLOCKED) |
| Cancellation race (SIGTERM + state write) | Lease release gates completion | Ensure lease released AFTER state written |
| Process epoch mismatch | validate_token() epoch check | Reject lease; force pool restart |

---

## Contracts & Dependencies

**Consumed from PH-2:**
- `_OrchestratorStateWriter.apply_transition(task_id, expected_state, new_state, cause, actor) → StateTransitionEvent`
- `SQLiteOrchestratorStateReader.get_task(task_id) → TaskRuntimeRecord | None`
- `TaskScheduler.ready_tasks(dependency_graph, states) → tuple[str, ...]`
- `LeaseManager.acquire/renew/release/validate_token(...)`
- `TaskState` enum: QUEUED, PLANNING, RUNNING, AWAITING_APPROVAL, VERIFYING, BLOCKED, PAUSED, FAILED, QUARANTINED, STOPPING, CANCELLED, COMPLETE, ROLLED_BACK
- `ReconciliationOutcome` enum: RESUMABLE, BLOCKED, FAILED, QUARANTINED, COMPLETED, CANCELLED

**Provided to PH-4+:**
- `WorkerPool(size, timeout) → ready for task assignment`
- `ExecutionResult(exit_code, output_hash, events) → for approval/auditing`
- Event stream (STDOUT, STDERR, HEARTBEAT) → for dashboard display

---

## Design Constraints & Invariants

1. **No state mutation outside _OrchestratorStateWriter** — R1 single-writer only
2. **Leases primary validity check** — process_epoch + monotonic token + released flag
3. **No blind resume after crash** — reconcile_startup() maps RUNNING → BLOCKED
4. **Insert-by-correction memory** — all future memory updates via MemoryStore.insert (not UPDATE)
5. **Append-only audit trail** — all execution events logged to journal (immutable)
6. **Graceful degradation** — worker crash doesn't lose task state (persisted to DB)
7. **Deterministic output hashing** — idempotent re-execution uses output hash for deduplication
8. **Process epoch immutability** — tied to pool lifetime; changes require new pool

---

## Testing Strategy

| Category | Tests | Focus |
|----------|-------|-------|
| **Unit** | 35 | WorkerPool lifecycle, StateIntegration routing, LeaseCoordinator calls, event streaming |
| **Failure-path** | 17 | Crash scenarios (5), lease expiry (3), timeout (2), output overflow (2), epoch staleness (3), state writer failure (2) |
| **Security** | 4 | State writer confinement, output bounds, lease staleness rejection, process isolation |
| **Integration** | 8 | End-to-end: ready → dispatch → execute → state update (via PH-2 writer) |
| **Total** | 64 | |

---

## Rollback Boundaries & Cleanup

**Rollback:**
- Worker state: non-persistent (worker processes disposable)
- Task state: persistent (Orchestrator DB owns it); reconcile_startup handles recovery
- Leases: auto-released on task end; stale leases auto-expire (TTL)

**Cleanup on shutdown:**
- `WorkerPool.shutdown()`: SIGTERM all; wait; SIGKILL remainder
- Unreleased leases: expire naturally (no manual cleanup needed; TTL ensures cleanup)
- Logs: flushed to journal; no in-process state left behind

