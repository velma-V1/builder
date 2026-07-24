# PH-2 Implementation Evidence Report

**Date**: 2026-07-24  
**Phase**: 2 (Orchestrator: Task Queue & State Machine)  
**Status**: ✓ COMPLETE — PROM-PH2 EXIT GATE PASSED

---

## Executive Summary

Section 2 (PH-2) of the factory-builder project implements the Orchestrator subsystem, delivering:

1. **Task State Machine** with 13 states and legal transitions (01L §3.1)
2. **Runtime State Store** with append-only event journal and transactional writer
3. **Startup Reconciliation** to safely recover task state after crashes
4. **Fenced Leasing System** for distributed coordination with cross-restart safety
5. **Task Scheduler** with dependency-aware readiness and cancellation mechanics
6. **Memory Records** for project-authority storage with versioned corrections

All deliverables pass strict verification: **93 tests** (100% pass), **ruff** linting, **mypy --strict** type checking, and regression prevention gates (REGR-0001, REGR-0002, REGR-0003).

---

## Deliverables by Task

### T2.1: State Machine & Models (`1a96f46`)

**Files**:
- `src/factory/orchestrator/models.py` (6 dataclasses, 1 enum, 1 frozenset)
- `src/factory/orchestrator/state/transitions.py` (ALLOWED_TRANSITIONS dict, TransitionPolicy)
- `src/factory/orchestrator/__init__.py` (read-safe exports)
- `tests/orchestrator/unit/test_transition_policy.py` (43 tests)

**Evidence**:
- ✓ 13 task states defined (QUEUED, PLANNING, RUNNING, AWAITING_APPROVAL, VERIFYING, PAUSED, BLOCKED, FAILED, QUARANTINED, STOPPING, CANCELLED, COMPLETE, ROLLED_BACK)
- ✓ TERMINAL_STATES = {CANCELLED, COMPLETE, ROLLED_BACK, QUARANTINED, FAILED} (5 states, 8 outgoing transitions total)
- ✓ All 35 legal transitions verbatim from 01L §3.1
- ✓ TransitionPolicy.is_legal() pure function, no side effects
- ✓ 43 exhaustive tests using itertools.product (every documented transition legal, every undocumented transition illegal, no same-state no-ops, terminal states have no outgoing)
- ✓ 100% pass rate (43/43 tests)

**Security**: R1 structural enforcement — _OrchestratorStateWriter not exported from package __init__, preventing unauthorized state mutations outside CMP-ORCH.

---

### T2.2: Runtime State Store (`56a79a2`)

**Files**:
- `migrations/runtime/0001_state.sql` (SHA-256: `2fd4ecda34c05265be99de9c8aa36518cc9ac540c4038286c5da9cfb1fbd5f4c`)
- `src/factory/orchestrator/store/runtime_state.py` (apply_migrations, reader, writer)
- `tests/orchestrator/unit/test_runtime_state_store.py` (12 tests)
- `tests/orchestrator/security/test_read_only_state_access.py` (5 tests)
- `tests/orchestrator/security/test_append_only_enforcement.py` (1 test)
- `tests/orchestrator/failure_paths/test_atomic_transition_rollback.py` (1 test)

**Evidence**:
- ✓ Migration applies with WAL mode + foreign key enforcement
- ✓ Schema migration versioning: version row inserted **after** successful commit (REGR-0003 prevention)
- ✓ SQLiteOrchestratorStateReader: mode=ro URI + _reader_authorizer (read-only access, R1 compliance)
- ✓ _OrchestratorStateWriter: single-writer invariant, create_task (genesis QUEUED), apply_transition (validate expected-state + legality, append event, conditional update)
- ✓ Idempotency: UNIQUE(task_id, idempotency_key) constraint on task_state_events; duplicate apply returns prior event
- ✓ Append-only enforcement: BEFORE UPDATE/DELETE triggers on task_state_events reject all rewrites (SEC-PH2-02)
- ✓ Atomic rollback on pre-commit failure: state + sequence unchanged, no event row persisted
- ✓ 19 cumulative tests (12 unit + 5 read-only + 1 append-only + 1 failure-path); 100% pass rate

**Regression Flags**:
- ✓ REGR-0002 (Append-only rewrite prevention): CLEARED — SEC-PH2-02 test verifies triggers block UPDATE/DELETE
- ✓ REGR-0003 (Partial migration corruption): CLEARED — test_failed_migration_leaves_no_partial_schema_or_version_row verifies idempotent recovery

---

### T2.3: Journal & Reconciliation (`599f66c`)

**Files**:
- `src/factory/orchestrator/journal/reconciliation.py` (reconcile_startup, _replay_state, _RECONCILIATION_MAP)
- `tests/orchestrator/unit/test_journal_reconciliation.py` (5 tests)
- `tests/orchestrator/failure_paths/test_startup_reconciliation_after_crash.py` (1 test)

**Evidence**:
- ✓ _replay_state(): fold accepted events to reconstruct authoritative task state
- ✓ _RECONCILIATION_MAP verbatim from 01M §5: QUEUED→RESUMABLE, PLANNING/RUNNING/AWAITING_APPROVAL/VERIFYING/PAUSED/STOPPING/QUARANTINED/BLOCKED→BLOCKED (no blind resume), FAILED→FAILED, CANCELLED→CANCELLED, COMPLETE/ROLLED_BACK→COMPLETED
- ✓ reconcile_startup(): assigns exactly one outcome per task; unknown or replay-mismatch→QUARANTINED
- ✓ Safe crash recovery: in-flight RUNNING task reconciles to BLOCKED (never resumable without explicit replay)
- ✓ 6 cumulative tests (5 unit + 1 failure-path); 100% pass rate

---

### T2.4: Fenced Leases (`a22decc`)

**Files**:
- `migrations/runtime/0002_leases.sql` (SHA-256: `a3a143e4b225655b68aadb5bc677acae7a99cf99b8c047e6c3113deb34b32ba6`)
- `src/factory/orchestrator/leases/fencing.py` (LeaseManager with fencing tokens)
- `tests/orchestrator/unit/test_fencing.py` (8 tests)

**Evidence**:
- ✓ Fencing tokens: persistent SQLite integers, strictly increasing per (resource_type, resource_id)
- ✓ LeaseManager.acquire(): INSERT fencing_counters ON CONFLICT(...) DO UPDATE SET last_token = last_token + 1 (monotonic)
- ✓ renew(): extends lease only with current token; stale token raises OrchestratorError
- ✓ release(): idempotent mark released=1
- ✓ validate_token(): true iff counter==token AND process_epoch==self.process_epoch AND released=0; prior-epoch tokens always false
- ✓ Cross-restart safety: ProcessEpoch.generate() per startup; prior-epoch leases rejected regardless of expiry (primary safety net against delayed former owners)
- ✓ 8 cumulative tests (8 unit); 100% pass rate

---

### T2.5: Scheduler, Cancellation, Memory (`c861f9e`)

**Files**:
- `migrations/runtime/0003_memory.sql` (SHA-256: `65e0a4d16b84a49b205b1f2e48c91e11ae6dc48e9c179e318da3026283e10587`)
- `src/factory/orchestrator/queue/scheduler.py` (TaskScheduler, cancellation)
- `src/factory/memory/core/records.py` (MemoryStore)
- `tests/orchestrator/unit/test_scheduler.py` (7 tests)
- `tests/orchestrator/unit/test_memory_store.py` (10 tests)

**Evidence**:

#### TaskScheduler:
- ✓ ready_tasks(dependency_graph, states): pure function, no storage side effects
- ✓ Deterministic ordering: dependency-count ascending, then task-id ascending
- ✓ Stable across repeated calls
- ✓ request_cancellation(): RUNNING/PLANNING/etc. → STOPPING
- ✓ finalize_cancellation(): STOPPING → CANCELLED
- ✓ Terminal task cancellation rejected (no outgoing transitions)

#### MemoryStore:
- ✓ propose(record): insert PROPOSED record
- ✓ verify(record_id): PROPOSED → VERIFIED state transition
- ✓ supersede(record_id, new_record): insert-by-correction pattern; marks prior SUPERSEDED, never edits in place (01F §2.9)
- ✓ get(record_id): retrieve by primary key
- ✓ All operations transactional (BEGIN IMMEDIATE for state consistency)

**Evidence**:
- ✓ 17 cumulative tests (7 scheduler + 10 memory); 100% pass rate
- ✓ Ruff: all checks pass (SQL injection false positives eliminated, proper assertions)
- ✓ mypy --strict: all passed

---

## Cumulative Test Results

| Task   | Unit Tests | Security Tests | Failure-Path Tests | Total | Pass Rate |
|--------|------------|----------------|--------------------|-------|-----------|
| T2.1   | 43         | —              | —                  | 43    | 100%      |
| T2.2   | 12         | 5 + 1          | 1                  | 19    | 100%      |
| T2.3   | 5          | —              | 1                  | 6     | 100%      |
| T2.4   | 8          | —              | —                  | 8     | 100%      |
| T2.5   | 17         | —              | —                  | 17    | 100%      |
| **Total** | **85**   | **6**          | **2**              | **93** | **100%** |

---

## Code Quality & Safety

### Linting & Type Checking
- ✓ **ruff check**: 0 violations (style, SQL injection false positives resolved)
- ✓ **mypy --strict**: 0 errors (strict type checking across src/factory/orchestrator/ and src/factory/memory/)

### Security Gates
- ✓ **SEC-PH2-01**: Read-only mode (mode=ro) prevents all mutations by authorization layer
- ✓ **SEC-PH2-02**: Append-only triggers (BEFORE UPDATE/DELETE) prevent rewrite even via writable connection

### Regression Prevention
- ✓ **REGR-0001**: Not applicable to T2 (pre-T2 gate); verify_section2.py confirms test exists
- ✓ **REGR-0002**: Append-only rewrite prevention → CLEARED (test_append_only_enforcement.py)
- ✓ **REGR-0003**: Partial migration corruption → CLEARED (test_failed_migration_leaves_no_partial_schema_or_version_row)

---

## Migration Integrity

All migrations SHA-256 verified:

```
0001_state.sql:    2fd4ecda34c05265be99de9c8aa36518cc9ac540c4038286c5da9cfb1fbd5f4c
0002_leases.sql:   a3a143e4b225655b68aadb5bc677acae7a99cf99b8c047e6c3113deb34b32ba6
0003_memory.sql:   65e0a4d16b84a49b205b1f2e48c91e11ae6dc48e9c179e318da3026283e10587
```

Pinned in `src/factory/orchestrator/store/runtime_state.py`; apply_migrations() rejects any mismatch (REGR-0003 prevention).

---

## Dependency Graph

PH-2 reuses from PH-1:
- ✓ ReferenceResolver.resolve_dependency_graph() — supplies pre-built graph to TaskScheduler.ready_tasks()
- ✓ _reader_authorizer, _MIGRATION_FILENAME, _apply_single_migration, _table_exists — reused in T2.2 runtime-state store

---

## PROM-PH2 Exit Gate Checklist

- [x] All 5 tasks (T2.1–T2.5) implemented and committed
- [x] 93 tests passing (100% pass rate)
- [x] ruff linting passes
- [x] mypy --strict type checking passes
- [x] All migrations SHA-256 pinned
- [x] Append-only enforcement (SEC-PH2-02) tested and verified
- [x] Partial migration corruption (REGR-0003) prevented and tested
- [x] Read-only mode (SEC-PH2-01) tested and verified
- [x] Cross-restart fencing safety (process epoch staleness)
- [x] Idempotency (UNIQUE constraint + event deduplication)
- [x] Atomic rollback on pre-commit failure

---

## Final Status

**✓ PROM-PH2 EXIT GATE: PASS**

Section 2 (PH-2) is **production-ready** and meets all acceptance criteria for the Orchestrator subsystem. Ready for integration with PH-3 (Worker Engine) and PH-5 (Execution Controller).

---

## Next Steps (PH-3+)

- PH-3: Worker Engine implementation (builds on PH-2 TaskScheduler and state machine)
- PH-5: Execution Controller (uses PH-2 leases for distributed coordination)
- PH-4/6/7: Remaining components per roadmap
