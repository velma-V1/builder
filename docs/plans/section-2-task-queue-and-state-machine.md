# PH-2 (Section 2) — Orchestrator: Task Queue & State Machine — Implementation Plan

**Document ID:** PLAN-S2 · **Status:** Authoritative PH-2 task-by-task implementation plan (expanded in
planning Pass 5) · **Phase:** PH-2 · **Roadmap:** `docs/10` PH-2 + `docs/10A` (execution env).
**Governing:** `01L §3.1` (state machine), `01D §3.1` (lane lifecycle — PH-6, not built here), `02 §4/§6/§7`
(sole-writer, runtime DB, atomic tx), `01M §3.6/§3.12/§3.17/§3.19/§5/§11` (journal, monotonic timing,
fencing, reconciliation, risk class), `01F §2/§3/§4` (memory), `01R` R1. Component specs:
`docs/specifications/components/{orchestrator,workstream-state-machine,task-engine,recovery-journal,lease-fencing,memory-core}-spec.md`.

**R1 throughout:** the **Orchestrator (CMP-ORCH)** is the sole authoritative writer. There is no Watchdog
here (PH-3, separate read-only process). PH-2 builds the transactional primitives the PH-3 Watchdog will
later call through its own narrow interface.

**Do not begin PH-2 product implementation until the operator authorizes it.** This plan is the deterministic
specification that implementation will follow; authoring it is planning, not implementation.

## Uniform execution context (applies to every PH-2 task; deltas noted per task)

From `docs/10A-ROADMAP-EXECUTION-MAP.md` PH-2 row: **Required branch** = task branch from the PH-1-promoted
base (operator assigns the product-implementation branch name at the PH-2 entry gate — not pre-assigned).
**Worktree** none (single serialized lane). **Sandbox** none (offline Python + SQLite; no executing project
code). **Models/Tools** none (py 3.12, uv, stdlib `sqlite3`, pytest, hypothesis, mypy, ruff — all PH-1 pins).
**Permissions/Secrets/Network** none / none / off. **Resources** < 1 GB RAM, no GPU, < 50 MB storage.
**Risk class** (`01M §3.11`): `low` for 2.1/2.5-memory; `medium` for 2.2/2.3/2.4 (they own recovery-critical
runtime state). **Autonomy** (Dec A): N/A at build time (Dec A enforcement is PH-3). **Deletion policy**:
approval-required everywhere (Dec B) — no auto-delete in code or tests. **Permitted routes**: LOCAL_FAST /
LOCAL_SUPERVISOR only. **Coverage obligation**: ≥95% branch coverage for `src/factory/orchestrator` and
`src/factory/memory` (PH-1 precedent). **Environment**: ENV-DEV (this session's Linux dev path); native
Windows 11 Home execution of any OS-specific behavior is a recorded known limitation, as in PH-1.

## Tech stack

Python 3.12; uv; stdlib `sqlite3`; pytest 9.1.1; pytest-cov 7.1.0; Hypothesis 6.161.0; mypy 2.3.0; Ruff
0.15.22 — identical pins to PH-1 (`pyproject.toml`/`uv.lock` already present). `src/factory/contracts`
(implemented, promoted) is a dependency: Task 2.5 reuses `ReferenceResolver.resolve_dependency_graph`.

## Locked file map

```text
migrations/runtime/0001_state.sql
migrations/runtime/0002_leases.sql
migrations/runtime/0003_memory.sql
src/factory/orchestrator/__init__.py
src/factory/orchestrator/models.py
src/factory/orchestrator/errors.py
src/factory/orchestrator/state/{__init__.py,transitions.py}
src/factory/orchestrator/store/{__init__.py,runtime_state.py}
src/factory/orchestrator/journal/{__init__.py,reconciliation.py}
src/factory/orchestrator/leases/{__init__.py,fencing.py}
src/factory/orchestrator/queue/{__init__.py,scheduler.py}
src/factory/memory/{__init__.py,core/__init__.py,core/records.py}
scripts/verify_section2.py
tests/orchestrator/conftest.py
tests/orchestrator/unit/{test_transition_policy,test_runtime_state_store,test_journal_reconciliation,test_fencing,test_scheduler,test_memory_records}.py
tests/orchestrator/integration/test_orchestrator_lifecycle.py
tests/orchestrator/security/test_read_only_state_access.py
tests/orchestrator/failure_paths/{test_atomic_transition_rollback,test_startup_reconciliation_after_crash}.py
docs/verification/section-2-task-queue-and-state-machine.md
```

## Public interfaces (frozen for PH-2; change = Change Contract + consumer impact per `01D §3.2`)

```python
# src/factory/orchestrator/models.py
from enum import StrEnum
from dataclasses import dataclass

class TaskState(StrEnum):
    QUEUED="QUEUED"; PLANNING="PLANNING"; RUNNING="RUNNING"; AWAITING_APPROVAL="AWAITING_APPROVAL"
    VERIFYING="VERIFYING"; BLOCKED="BLOCKED"; PAUSED="PAUSED"; FAILED="FAILED"
    QUARANTINED="QUARANTINED"; STOPPING="STOPPING"; CANCELLED="CANCELLED"; COMPLETE="COMPLETE"
    ROLLED_BACK="ROLLED_BACK"

TERMINAL_STATES = frozenset({TaskState.CANCELLED, TaskState.COMPLETE, TaskState.ROLLED_BACK})

class ReconciliationOutcome(StrEnum):
    RESUMABLE="RESUMABLE"; BLOCKED="BLOCKED"; FAILED="FAILED"
    QUARANTINED="QUARANTINED"; COMPLETED="COMPLETED"; CANCELLED="CANCELLED"

class LeaseResourceType(StrEnum):
    TASK="TASK"; RESOURCE="RESOURCE"     # workspace/branch/model/sandbox/promotion kinds: PH-5+

class MemoryRecordStatus(StrEnum):
    PROPOSED="PROPOSED"; VERIFIED="VERIFIED"; SUPERSEDED="SUPERSEDED"; REFUTED="REFUTED"; ARCHIVED="ARCHIVED"

# frozen slots dataclasses: StateTransitionEvent, TaskRuntimeRecord, Lease, MemoryRecord,
# ProcessEpoch  (fields as specified in the component specs)
```

The full dataclass field sets and method signatures are fixed in the six component specs; this plan does not
restate them (single authority: the specs own the shapes, the plan owns the build procedure).

---

## Task 2.1 — State definitions & legal transition table (CMP-WSSM)

- **Task ID / Title:** T2.1 / State definitions & legal transition policy.
- **Purpose:** encode the authoritative `01L §3.1` state set + legal-transition table as a pure policy.
- **Scope:** `src/factory/orchestrator/{models.py,errors.py,state/**}`. **Exclusions:** no DB, no writes.
- **Authoritative requirements:** `01L §3.1`. **Component:** CMP-WSSM. **Interfaces:** `TransitionPolicy.is_legal`, `ALLOWED_TRANSITIONS`, `TaskState`, `TERMINAL_STATES`. **Contracts:** CTR-TASK-WS-SM. **Schemas:** none.
- **Dependencies (blocking):** none (foundational). **Soft:** none.
- **Inputs:** `01L §3.1` table. **Outputs/Files:** `models.py`, `errors.py`, `state/transitions.py`, `tests/orchestrator/unit/test_transition_policy.py`. **Artifacts:** unit ETM rows.
- **Complexity:** low. **Runtime:** seconds.
- **Implementation procedure (TDD):**
  1. Write `test_transition_policy.py`: parametrized proof every documented transition is legal; and
     `itertools.product(TaskState, TaskState)` minus the table minus `(s,s)` no-ops → all illegal. Run → fails (no `TransitionPolicy`).
  2. Implement `TaskState`, `TERMINAL_STATES`, `ALLOWED_TRANSITIONS` (literal transcription of `01L §3.1`),
     `TransitionPolicy.is_legal`; `OrchestratorError` in `errors.py`.
  3. `ruff check`, `mypy`, run tests green.
- **Execution order:** first. **Checkpoint/Save/Recovery point:** commit after step 3.
- **Rollback procedure:** `git revert` the task commit (pure code; no state). **Failure conditions/signatures:** any documented transition rejected, or any undocumented pair accepted. **Recovery:** fix `ALLOWED_TRANSITIONS`, re-run. **Quarantine:** N/A (deterministic).
- **Verification procedure / Evidence:** exhaustive transition matrix test (VERIFICATION-MATRIX cat #1 unit). **Acceptance:** both tests pass; ruff/mypy clean. **Completion:** committed `feat: define orchestrator task states and legal transitions`.

## Task 2.2 — Runtime-state DB + transactional writer (CMP-ORCH)

- **Task ID / Title:** T2.2 / Runtime-state store + sole-writer transaction. **Risk:** medium.
- **Purpose:** the SQLite runtime store and the atomic `apply_transition` that is the only write path (R1).
- **Scope:** `store/**`, `migrations/runtime/0001_state.sql`. **Exclusions:** no queue/lease/memory logic.
- **Authoritative requirements:** `02 §4/§6/§7`, `01L §3.1` (fail-closed audit on illegal). **Component:** CMP-ORCH. **Interfaces:** `_OrchestratorStateWriter.apply_transition`, `SQLiteOrchestratorStateReader`, `ProcessEpoch`. **Contracts:** CTR-RUNTIME-STATE-DB. **Schemas:** `0001_state.sql` (tasks, task_state_events append-only + triggers, `UNIQUE(task_id, idempotency_key)`).
- **Dependencies (blocking):** T2.1. **Soft:** PH-1 migration-runner pattern.
- **Inputs:** transition requests. **Outputs/Files:** `0001_state.sql`, `store/runtime_state.py`, `tests/orchestrator/unit/test_runtime_state_store.py`, `.../security/test_read_only_state_access.py`, `.../failure_paths/test_atomic_transition_rollback.py`. **Artifacts:** writer-boundary + security + rollback ETM rows.
- **Complexity:** medium. **Runtime:** seconds.
- **Implementation procedure (TDD):**
  1. Write the migration (WAL, FK, append-only triggers, unique idempotency index).
  2. Write failing tests: legal transition updates state + appends one `accepted=1` event, `sequence` +1;
     illegal transition leaves state, appends one `accepted=0` audit event; expected-state mismatch rejected;
     `mode=ro` reader denies INSERT/UPDATE/DELETE/CREATE/DROP/ALTER (reuse PH-1 `_reader_authorizer`);
     **append-only enforcement (SEC-PH2-02): a direct `UPDATE`/`DELETE` on `task_state_events` — even via a
     writable connection — raises (`BEFORE UPDATE/DELETE` triggers `RAISE(ABORT)`);**
     **migration-runner transactional safety (REGR-0003): `apply_migrations` records the `schema_migrations`
     version only after a successful apply, and a migration forced to fail mid-apply leaves no partial schema
     and no version row (one transaction);**
     forced pre-commit failure leaves state+sequence unchanged, no event row.
  3. Implement `apply_migrations` (SHA-256-pinned, one tx), `SQLiteOrchestratorStateReader`,
     `_OrchestratorStateWriter.apply_transition` (`BEGIN IMMEDIATE` → idempotency short-circuit → read →
     expected-state check → legality → sequence+1 → append event → update tasks if accepted → commit).
  4. ruff/mypy/tests green.
- **Checkpoint:** commit after step 4. **Rollback:** revert commit; DB is disposable (gitignored).
- **Failure conditions/signatures:** partial state after a forced failure; any second write path; reader able to mutate. **Recovery:** fix transaction boundary; re-run. **Quarantine:** flaky only if non-deterministic (not expected).
- **Verification/Evidence:** cat #1 unit, #5 security (read-only), #15 failure-path (atomic rollback). **Acceptance:** all three test files pass. **Completion:** `feat: add orchestrator runtime-state store and transactional writer`.

## Task 2.3 — Durable journal + startup reconciliation (CMP-JOURNAL)

- **Task ID / Title:** T2.3 / Journal replay + reconciliation. **Risk:** medium.
- **Purpose:** reconstruct state by folding events; assign one `ReconciliationOutcome` per task; no blind resume.
- **Scope:** `journal/**`. **Exclusions:** no container/worker/worktree reconciliation (none exist; recorded known limitation).
- **Authoritative requirements:** `01M §3.6/§3.17/§5/§11`. **Component:** CMP-JOURNAL. **Interfaces:** `reconcile_startup(reader, task_ids)`. **Contracts:** CTR-RECOVERY-JOURNAL. **Schemas:** reuses `0001_state.sql` task_state_events.
- **Dependencies (blocking):** T2.2. **Soft:** T2.1.
- **Outputs/Files:** `journal/reconciliation.py`, `tests/.../unit/test_journal_reconciliation.py`, `.../failure_paths/test_startup_reconciliation_after_crash.py`. **Artifacts:** replay + crash-recovery ETM rows.
- **Complexity:** medium. **Runtime:** seconds.
- **Implementation procedure (TDD):**
  1. Failing tests: consistent replay + `QUEUED`→`RESUMABLE`; `RUNNING` at simulated crash (row written
     directly)→`BLOCKED`; stored≠replayed→`QUARANTINED`; hard-kill mid-tx leaves DB consistent (WAL) and no
     silent resume.
  2. Implement `reconcile_startup` with the verbatim mapping table from `recovery-journal-spec.md`.
  3. ruff/mypy/tests green.
- **Checkpoint:** commit after step 3. **Rollback:** revert commit. **Failure conditions/signatures:** any non-terminal task mapped `RESUMABLE`; a replay mismatch not quarantined. **Recovery:** correct mapping; re-run. **Quarantine conditions (product behavior):** replay mismatch → task `QUARANTINED` (by design).
- **Verification/Evidence:** cat #16 crash&interruption, #17 journal-replay. **Acceptance:** both test files pass. **Completion:** `feat: add orchestrator startup reconciliation`.

## Task 2.4 — Fenced expiring leases (CMP-LEASE)

- **Task ID / Title:** T2.4 / Fenced leases. **Risk:** medium.
- **Purpose:** strictly increasing persistent fencing tokens + process-epoch staleness so a delayed former owner cannot write.
- **Scope:** `leases/**`, `migrations/runtime/0002_leases.sql`. **Exclusions:** lease kinds beyond TASK/RESOURCE (PH-5+).
- **Authoritative requirements:** `01M §3.6/§3.12/§3.19`. **Component:** CMP-LEASE. **Interfaces:** `LeaseManager.acquire/renew/release/validate_token`. **Contracts:** CTR-LEASE-FENCING. **Schemas:** `0002_leases.sql` (fencing_counters, leases).
- **Dependencies (blocking):** T2.2. **Soft:** none.
- **Outputs/Files:** `0002_leases.sql`, `leases/fencing.py`, `tests/.../unit/test_fencing.py`. **Artifacts:** fencing ETM rows.
- **Complexity:** medium. **Runtime:** seconds.
- **Implementation procedure (TDD):**
  1. Failing tests: repeated acquire → strictly increasing tokens persisted across a simulated restart
     (new `LeaseManager`, same DB); superseded token rejected; renew with stale token raises; lease from a
     different `ProcessEpoch` treated as expired regardless of `expires_at`; release idempotent.
  2. Implement migration + `LeaseManager` (acquire = upsert-increment counter, insert lease with epoch, commit).
  3. ruff/mypy/tests green.
- **Checkpoint:** commit after step 3. **Rollback:** revert commit. **Failure conditions/signatures:** a lower/equal token issued; a prior-epoch lease accepted. **Recovery:** fix counter/epoch logic; re-run. **Quarantine:** N/A.
- **Verification/Evidence:** cat #18 fencing-token. **Acceptance:** `test_fencing.py` passes. **Completion:** `feat: add orchestrator fenced expiring leases`.

## Task 2.5 — Queue, cancellation, idempotent restart, core memory (CMP-TASKENG + CMP-MEM)

- **Task ID / Title:** T2.5 / Scheduler + cancellation + core memory. **Risk:** low (memory) / medium (queue integration).
- **Purpose:** deterministic readiness/ordering, cancellation mechanics, idempotent restart proof, and
  project-authority memory records (partial `01F`).
- **Scope:** `queue/**`, `memory/core/**`, `migrations/runtime/0003_memory.sql`. **Exclusions:** priority
  pre-emption/starvation timing (PH-6); non-PROJECT_AUTHORITY memory classes, retention, holds (PH-7).
- **Authoritative requirements:** `05 S2`, `01L §3.1`, `01F §2/§3/§4`, `01D §3.4`. **Components:** CMP-TASKENG, CMP-MEM. **Interfaces:** `TaskScheduler.ready_tasks`, `request_cancellation`, `finalize_cancellation`, `MemoryStore.propose/verify/supersede/get`. **Contracts:** CTR-MEMORY-RECORD (partial). **Schemas:** `0003_memory.sql`.
- **Dependencies (blocking):** T2.2 (writer), T2.1 (states), PH-1 `ReferenceResolver.resolve_dependency_graph`. **Soft:** T2.3, T2.4 (used by the integration test).
- **Outputs/Files:** `queue/scheduler.py`, `memory/core/records.py`, `0003_memory.sql`, `tests/.../unit/{test_scheduler,test_memory_records}.py`, `tests/.../integration/test_orchestrator_lifecycle.py`. **Artifacts:** queue+memory+end-to-end ETM rows.
- **Complexity:** medium. **Runtime:** seconds.
- **Implementation procedure (TDD):**
  1. Failing scheduler tests: incomplete dependency → not ready; no deps → ready; deterministic stable order
     (dep-count asc, then id asc); cancellation drives …→`STOPPING`→`CANCELLED`; idempotent restart does not
     re-admit an already-committed transition.
  2. Failing memory tests: proposed→`PROPOSED`; verify `PROPOSED`→`VERIFIED` only; supersede inserts new +
     marks prior `SUPERSEDED`, both readable; `MemoryRecord` field set is exactly the 10 named fields
     (structural test — no free-form value field).
  3. Implement `TaskScheduler` (reusing PH-1 resolver graph), cancellation helpers, `0003_memory.sql`, `MemoryStore`.
  4. End-to-end `test_orchestrator_lifecycle.py`: two tasks with a dependency → readiness gating → drive
     TASK-001 QUEUED→…→COMPLETE (sequence monotonic) → TASK-002 becomes ready → lease + stale-token rejection
     → cancel TASK-002 → restart (new epoch) + `reconcile_startup` (TASK-001 COMPLETED, TASK-002 CANCELLED,
     stale-epoch lease invalid) → propose/verify/supersede a memory record.
  5. ruff/mypy/tests green.
- **Checkpoint:** commit after step 5. **Rollback:** revert commit. **Failure conditions/signatures:** non-deterministic ready order; memory in-place edit possible; end-to-end restart resurrecting a cancelled task. **Recovery:** fix and re-run. **Quarantine:** N/A.
- **Verification/Evidence:** cat #1 unit, #2 integration, #16 crash (restart path). **Acceptance:** all Task 2.5 tests pass. **Completion:** `feat: add orchestrator scheduler, cancellation, and core memory`.

## Task 2.6 — Full verification + Section 2 evidence report

- **Task ID / Title:** T2.6 / Verification pipeline + evidence report. **Risk:** low.
- **Purpose:** one reproducible verification command + the `01G` evidence report + Section 3 handoff.
- **Scope:** `scripts/verify_section2.py`, `docs/verification/section-2-...md`, README/index updates. **Exclusions:** no product-logic change.
- **Authoritative requirements:** `01G §3.1/§3.3` (ETM + verdicts), R5. **Components:** all PH-2. **Interfaces:** consumes every PH-2 public interface.
- **Dependencies (blocking):** T2.1–T2.5. **Soft:** none.
- **Outputs/Files:** `scripts/verify_section2.py` (same structure as `verify_section1.py`, retargeted), `docs/verification/section-2-task-queue-and-state-machine.md`, README + `docs/00-DOCUMENTATION-INDEX.md` edits. **Artifacts:** `artifacts/verification/section-2/manifest.json` (gitignored), summarized into the report.
- **Complexity:** low. **Runtime:** ~1 min.
- **Implementation procedure:** run `uv sync --frozen`, `ruff format --check`, `ruff check`, `mypy --strict`,
  unit/integration/security/failure-path suites, then the coverage-gated full run
  (`--cov=src/factory/orchestrator --cov=src/factory/memory --cov-branch --cov-fail-under=95`). Write the
  report: environment table, command/exit-code table, test counts, coverage, a requirement-to-test matrix
  against this plan's acceptance criteria, a security/failure-path matrix, an `01G §3.1` ETM, known
  limitations (scoped reconciliation; no PH-3/4/5 worker/sandbox integration; native-Windows untested), and
  the Section 3 interfaces PH-3 consumes (`apply_transition`, `reconcile_startup`, `LeaseManager`,
  `ready_tasks`). Update README/index only after the run passes.
- **Checkpoint:** commit after report. **Rollback:** revert commit (docs/script only). **Failure conditions/signatures:** coverage < 95%; any verdict non-`PASS` on a required criterion. **Recovery:** fix the implicated task, re-run — anti-weakening (`01G §3.2`) applies once implementation has started. **Quarantine:** numeric flaky policy (`01G §3.5`).
- **Verification/Evidence:** the report itself is the evidence package. **Acceptance:** verify script exit 0; report classified `PASS`. **Completion:** `test: verify Section 2 orchestrator system`.

---

## Task execution graph

```
T2.1 ──► T2.2 ──┬──► T2.3 ──┐
                ├──► T2.4 ──┤
                └──► T2.5 ──┴──► T2.6
                     (T2.5 soft-depends on T2.3, T2.4 for the end-to-end test)
```

- **Execution order:** T2.1 → T2.2 → T2.3 → T2.4 → T2.5 → T2.6 (serialized; matches integration order in `PH2-INTEGRATION §9`).
- **Critical path:** the whole chain (T2.1→T2.6) — PH-2 is a single serialized lane.
- **Parallel execution groups:** none within PH-2 (see review below).
- **Serialized execution groups:** all six tasks; all share one runtime DB + shared migrations (a shared-schema/shared-state artifact ⇒ serialize, `01D §3.4`, `WORKSTREAM-MAP §3`).
- **Shared components:** CMP-ORCH (writer) underlies T2.3/2.4/2.5. **Shared contracts:** CTR-RUNTIME-STATE-DB. **Shared schemas:** `migrations/runtime/0001..0003`. **Shared resources:** one SQLite DB. **Shared state:** the runtime DB. **Shared rollback path:** journal-authoritative; per-task `git revert`. **Shared failure domain:** the single DB.
- **Task integration points:** T2.5 end-to-end lifecycle test (internal IP). **Promotion checkpoints:** PH-2 exit gate (`docs/10 §15`). **Repository checkpoints:** one commit per task (6 commits).

## Parallel execution review

| Question | Determination | Reason / Risk / Sync / Recovery / Verification |
|---|---|---|
| Tasks that can run in parallel | **None** | All six share the runtime DB + the migration sequence; `01D §3.4` forbids parallel work on shared schema/state. Risk of parallel: migration-order and schema conflicts. Sync: serialize. Recovery: journal-authoritative. Verification: T2.6 full suite. |
| Tasks that must be serialized | **All (T2.1→T2.6)** | shared schema/state/writer. |
| Shared state / contracts / schemas / resources | runtime DB / CTR-RUNTIME-STATE-DB / `0001..0003` / one SQLite file | single failure domain by design (`02 §6`). |
| Tasks requiring synchronization | migrations `0001`→`0002`→`0003` must apply in order | enforced by the SHA-pinned versioned runner. |
| Tasks requiring exclusive execution | every write task (single writer, R1) | `BEGIN IMMEDIATE` serializes writers even within a process. |
| **Maximum concurrent implementation workstreams for PH-2** | **1** | PH-2 is off the parallel map; `WORKSTREAM-MAP` parallel sets (A/B) begin at PH-4/PH-8, not here. |

## Implementation validation (this plan)

Every task is independently executable and verifiable; every blocking dependency resolves to PH-1
(implemented/promoted) or an earlier PH-2 task; every component/interface/contract exists (specs +
CONTRACT-REGISTRY); every schema is defined here or in PH-1; every repository path is in the locked file map;
every verification path maps to a VERIFICATION-MATRIX category (#1/#2/#5/#15/#16/#17/#18); every evidence
path is an ETM row + the Section 2 report; every rollback path is journal-authoritative + per-task revert;
the approval path is the PH-2 exit gate. No circular dependency (graph is a DAG), no unreachable task, no
orphan task, no undocumented work.

## Acceptance & promotion gate

Acceptance: `05 S2` outputs + `01L §3.1`/`01M §3.6` criteria `PASS` with `01G §3.1` ETM; ≥95% branch
coverage; external-process deadlock detectable (staleness distinguishable via journal, for the PH-3
Watchdog). Rollback boundary: journal-authoritative; migrations transactional. **Promotion gate: PH-2 exit
approval (operator).** Handoff → PH-3 (Watchdog observes the Orchestrator; permission/approval/audit write
through `apply_transition`).
