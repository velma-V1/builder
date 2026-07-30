# PH-2 Failure, Recovery, Rollback & Resilience Plan

**Document ID:** FRR-PH2
**Repository path:** `docs/planning/PH2-FAILURE-RECOVERY-ROLLBACK.md`
**Status:** Active — PH-2-scoped failure/recovery/rollback/resilience plan (planning Pass 7)
**Authority level:** Plan (subordinate to `01M`, `04`, `docs/release/ROLLBACK-PLAN.md`, RISK-REGISTER)
**Owner:** PH-2 planning · **Established:** 2026-07-24
**Governing:** `01M §3.6/§3.12/§3.17/§5` (journal, fencing, monotonic timing, reconciliation outcomes),
`04 §1-10` (recovery policy + result states), `docs/release/ROLLBACK-PLAN.md §1-3` (rollback layers,
snapshot model, reconciliation), `01G §3.2` (anti-weakening), PLAN-S2, VEP-PH2, the six PH-2 component specs,
RISK-REGISTER (RISK-REC-02 blocks PH-2).

## 0. Scope & single-authority boundary

Failure/recovery/rollback **for PH-2 only**. `01M` governs recovery/Watchdog/snapshots; `04` the coarse
policy; `ROLLBACK-PLAN` the layer map; the risk register the risk inventory. Where `04` and `01M` differ,
**`01M` governs** (per ROLLBACK-PLAN). This plan maps PH-2's slice and cites those owners; it redesigns
nothing. PH-2 has **no sandbox, container, WSL2/Docker, model, tool, or network layer** — those failure
classes bind at PH-3/4/5/8 and are owned by the risk register; this plan marks them out-of-scope, not absent.

**Reconciliation outcomes** are exactly the six from `01M §5` (`RESUMABLE/BLOCKED/FAILED/QUARANTINED/
COMPLETED/CANCELLED`); **recovery result states** are exactly the five from `04 §9`
(`RECOVERED/DEGRADED/BLOCKED/ESCALATED/STOPPED`). This plan invents neither.

## 1. PH-2 credible failure modes

Standing values (per `04`, `01M`, PLAN-S2): **automatic repair allowed** = code-level repair only under the
repair-first rule §5 (never silent state mutation); **data preservation** = append-only journal + audit never
erased (`04 §10`); **operator approval** = only at the PH-2 exit gate, not per-failure at build time;
**verification after repair** = re-run the implicated test + regression per `01G §2.4`. Only deltas below.
`AR` = automatic-repair-allowed at runtime (product behavior), distinct from build-time developer repair.

| ID | Failure | Pass-7 category | Sev | Cmp | Detection / signature | Immediate safe action | Containment | Rollback | Recovery | Risk |
|---|---|---|---|---|---|---|---|---|---|---|
| F-PH2-01 | process/power crash mid-transition | Process Crash / Power Interruption | High | ORCH,JOURNAL | startup: WAL not clean-committed | none needed — SQLite WAL leaves tx fully-applied-or-not | one DB | n/a (tx atomic) | startup reconciliation → outcome per task | RISK-REC-02 |
| F-PH2-02 | partial write / state corruption | State Corruption / Partial File Write | High | ORCH | replay ≠ stored `current_state` | fail closed | one task row | journal-authoritative | reconcile → `QUARANTINED` | RISK-REC-02 |
| F-PH2-03 | disk full during commit | Storage Exhaustion | Med | ORCH | `sqlite3` OperationalError on commit | abort tx (no partial) | one DB | tx rolled back | retry after space freed; never delete audit to free space (`01M §3.34`) | — |
| F-PH2-04 | journal corruption | Journal Corruption | High | JOURNAL | replay inconsistency / trigger-violation attempt | fail closed | task | n/a | `QUARANTINED`; no silent resume | RISK-REC-02 |
| F-PH2-05 | illegal transition requested | Interface / Contract Failure | Med | WSSM,ORCH | `is_legal` False | append `accepted=0` audit event; leave state | that request | none (state unchanged) | caller corrects; deterministic | RISK-ARCH-01 |
| F-PH2-06 | optimistic-concurrency conflict | Race Condition / Concurrency | Med | ORCH | expected_current_state ≠ actual | reject write | that request | none | caller re-reads + retries | — |
| F-PH2-07 | stale / prior-epoch lease writes | Concurrency / Lock Recovery | High | LEASE | `validate_token` False; epoch mismatch | reject write | that resource | none (write blocked) | acquire fresh lease (new token) | RISK-REC-02 |
| F-PH2-08 | failed migration | Migration / Schema Failure | High | ORCH/schema | SHA mismatch or tx error; version row absent | abort migration tx | whole DB init | tx rolled back (no partial schema) | fix migration; re-run; incompatible downgrade fails closed (`01O §2.29`) | RISK-DEP-01 |
| F-PH2-09 | non-idempotent replay / failed reconciliation | Recovery Failure | High | JOURNAL | duplicate effect on replay | fail closed → `BLOCKED`/`QUARANTINED` | task | n/a | idempotent replay is the design; a violation blocks, never resumes | **RISK-REC-02 (blocks PH-2)** |
| F-PH2-10 | memory in-place edit / secret-field attempt | Memory / Data Failure | Med | MEM | supersede-by-insert violated; field-set test fails | reject | one record | none | insert-only correction; DB constraint on class | RISK-DATA-02 |
| F-PH2-11 | idempotency-key retry duplicate | Duplicate Execution | Med | ORCH | 2nd call same `(task_id, idempotency_key)` | return existing event, no new row | that request | none | idempotent by unique index | RISK-REC-02 |
| F-PH2-12 | pinned dependency unavailable | Dependency Failure | Med | env | `uv sync --frozen` non-zero | block env setup | build env | n/a | nearest approved pin, recorded (`RISK-DEP-01`) | RISK-DEP-01 |
| F-PH2-13 | test / verification failure at Task 2.6 | Test / Verification / Promotion Failure | Med | all | `verify_section2` non-zero; verdict ≠ PASS; cov<95% | stop forward execution (repair-first §5) | that task | per-task `git revert` | fix under anti-weakening (`01G §3.2`), re-run full suite | RISK-VERIF-01/02 |

**Out-of-scope for PH-2 (owned by risk register / later phases):** sandbox/container/WSL2/Docker failure
(PH-5, RISK-ISO/DOCKER/WIN), model/tool/routing failure (PH-4, RISK-MODEL), path-safety/permission/audit-chain
(PH-1/3), snapshot/updater/installer (PH-7/8, RISK-REC-01/UPDATE/INSTALL). Recorded, not skipped.

## 2. Repair-first execution rule (PH-2 binding)

On any PH-2 test/verification/task failure during implementation: **stop forward execution → preserve failure
evidence → identify the exact failing area → root-cause → apply the smallest authority-compliant repair (never
weaken a test to pass; `01G §3.2`/`04 §4`) → re-run the failed check → re-run directly-affected + dependent +
required regression tests → continue only if all pass → flag the area in the Continuation Ledger and
`REGRESSION-REGISTER.md` even after success.** If repair fails: attempt rollback (per-task `git revert`;
journal-authoritative state) → re-run → if that fails, quarantine the state, classify the blocker, STOP. Every
repair records: Failure ID · original failure · root cause · affected area · reverted state · repair · files
changed · tests re-run · verification re-run · results · evidence location · regression flag · remaining risk
(the Regression Register row schema).

## 3. Checkpoint & save-point architecture (PH-2)

| Checkpoint ID | Creation trigger | Artifacts / hashes captured | Restore procedure | Invalidation |
|---|---|---|---|---|
| CKP-PH2-REPO (per task) | task-boundary commit (6 commits T2.1–T2.6) | git tree + commit SHA | `git checkout <sha>` | superseded by next task commit |
| CKP-PH2-STATE | every committed transition | `task_state_events` append-only rows (the journal) | fold events → current state | replay mismatch → QUARANTINED |
| CKP-PH2-SCHEMA | successful migration | `schema_migrations` version + pinned SHA-256 | re-run SHA-verified migration | SHA mismatch blocks apply |
| CKP-PH2-EVIDENCE | Task 2.6 report finalize | ETM rows + manifest SHA-256s | regenerate via `verify_section2` | anti-weakening violation invalidates |

PH-2 has **no worktree/sandbox/snapshot checkpoints** (those bind at PH-5/PH-7). The runtime DB itself is
gitignored and disposable; the git commits + the append-only journal are the authoritative PH-2 checkpoints.

## 4. Rollback architecture (PH-2)

Maps to `ROLLBACK-PLAN §1` layers **"Task/checkpoint"** and **"Contract activation"** (PH-2 is the journal
layer). PH-2 rollback is atomic-by-construction: a transition either commits or does not.

| Rollback ID | Scope | Trigger | Authority | Source → target | Procedure | Verification |
|---|---|---|---|---|---|---|
| RB-PH2-TX | one transition | pre-commit failure | CMP-ORCH (auto) | in-flight → prior committed state | SQLite tx rollback (nothing observable) | T-PH2-FP1 (atomic rollback) |
| RB-PH2-MIG | schema init | migration failure | migration runner (auto) | partial → no schema | tx rollback; version row not written | migration re-apply test |
| RB-PH2-COMMIT | one task's code | test failure post-commit | developer (build-time) | task commit → prior commit | `git revert <sha>` | re-run task suite |

**Rollback invariants verified:** atomic where required (tx-level); crosses no prohibited boundary (single DB,
single writer); **never deletes audit/journal** (append-only; `04 §10`); restores no incompatible schema
(SHA-pinned; incompatible downgrade fails closed); returns to a deterministically verified state (journal
replay). No `main`/protected-ref rollback is in scope (no promotion to `main` in PH-2).

## 5. Recovery architecture (PH-2)

| Recovery ID | Type | Trigger | Required inputs | Procedure | State/integrity validation | Completion | Escalation |
|---|---|---|---|---|---|---|---|
| REC-PH2-CRASH | crash / cold / state recovery | restart after crash | runtime DB, `task_ids` | `reconcile_startup` (CMP-JOURNAL) | fold events; compare to stored state; check lease epochs | each task → one `01M §5` outcome | mismatch → `QUARANTINED` |
| REC-PH2-JOURNAL | journal replay | any restart | `task_state_events` | idempotent fold in `sequence` order | replay consistency | authoritative state reconstructed | inconsistency → `BLOCKED`/`QUARANTINED` |
| REC-PH2-LEASE | lock recovery | restart with held leases | `fencing_counters`, `ProcessEpoch` | prior-epoch leases treated expired; counters persist | token monotonicity preserved | stale owners cannot write | — |

PH-2 recovery is **cold/crash/state/journal/lock** only. Warm-resume of in-flight tasks is deliberately
**not** offered (no worker/Watchdog layer yet): non-terminal tasks reconcile `BLOCKED` (no blind resume,
`01M §11`); PH-3's Watchdog performs the fuller reconciliation. Automatic *task* resume is out of PH-2 scope;
only automatic *state reconstruction* (journal replay) is in scope. Recovery result maps to `04 §9`:
`RECOVERED` (clean replay, resumable/terminal), `BLOCKED` (non-terminal/inconsistent), `QUARANTINED`→
effectively `STOPPED` for that task until operator/PH-3.

## 6. Resilience requirements (PH-2 implementation plan)

| Requirement | PH-2 mechanism |
|---|---|
| Fail-closed behavior | illegal transition / expected-state mismatch / replay mismatch / token conflict all reject or quarantine, never proceed |
| Atomic writes / transactional changes | every `apply_transition` is one `BEGIN IMMEDIATE` … commit |
| Journaled operations / crash-safe persistence | append-only `task_state_events` written in the same tx; SQLite WAL |
| Corruption detection | startup event-fold vs stored state; SHA-pinned migrations |
| Integrity hashing | SHA-256-pinned migration files; evidence hashes (Task 2.6) |
| Idempotent operations / duplicate-execution prevention | `UNIQUE(task_id, idempotency_key)`; idempotent replay |
| Lock recovery / deadlock & race prevention | persistent fencing tokens + process epoch; single writer + `BEGIN IMMEDIATE` serialize writers (no deadlock across writers) |
| Cancellation handling | `STOPPING → CANCELLED` via legal transitions |
| Safe shutdown / safe restart | no special shutdown needed (journal authoritative); restart runs reconciliation before serving |
| Offline operation | no network/model/tool dependency in PH-2 (inherently offline) |
| Watchdog monitoring / health / liveness | **out of PH-2 scope** — PH-2 emits the journal staleness signal the PH-3 Watchdog will consume; the Watchdog process is PH-3 |

## 7. Failure-injection & resilience tests (PH-2 subset)

Each maps to a PLAN-S2 test file. Fields: initial state · injected failure · expected detection · containment ·
recovery · rollback · evidence · audit entry · final state · pass criteria (abbreviated to the decisive columns).

| Inj ID | Injected failure | Test file | Expected detection → final state |
|---|---|---|---|
| INJ-PH2-01 | process termination mid-transition | `failure_paths/test_startup_reconciliation_after_crash.py` | WAL crash-consistency → no silent resume; non-terminal → `BLOCKED` |
| INJ-PH2-02 | partial write / forced pre-commit failure | `failure_paths/test_atomic_transition_rollback.py` | tx rolled back → state + sequence unchanged, no event row |
| INJ-PH2-03 | corrupted state (stored ≠ replayed) | `unit/test_journal_reconciliation.py` | replay mismatch → `QUARANTINED` |
| INJ-PH2-04 | concurrency conflict (stale expected-state) | `unit/test_runtime_state_store.py` | expected-state mismatch rejected, no write |
| INJ-PH2-05 | stale / prior-epoch lease | `unit/test_fencing.py` | `validate_token` False; prior-epoch expired |
| INJ-PH2-06 | duplicate idempotency-key retry | `unit/test_runtime_state_store.py` | identical event returned; one row only |
| INJ-PH2-07 | disk-full on commit (simulated) | `failure_paths/test_atomic_transition_rollback.py` (variant) | commit aborts; no partial state |

Deferred injections (owned by later phases / risk register): container/WSL2/Docker/host restart, model/tool
timeout-crash, sandbox escape, failed upgrade/installer, snapshot failure — PH-4/5/7/8.

## 8. Failure traceability

| Failure | Component | Task | Detection | Containment | Rollback | Recovery | Test | Evidence | Approval |
|---|---|---|---|---|---|---|---|---|---|
| F-PH2-01 | ORCH/JOURNAL | T2.2/T2.3 | startup replay | one DB | RB-PH2-TX | REC-PH2-CRASH | INJ-PH2-01 | ETM | exit gate |
| F-PH2-02 | ORCH | T2.2 | replay≠stored | task row | RB-PH2-TX | REC-PH2-JOURNAL | INJ-PH2-03 | ETM | exit gate |
| F-PH2-03 | ORCH | T2.2 | commit error | one DB | RB-PH2-TX | retry | INJ-PH2-07 | ETM | exit gate |
| F-PH2-04 | JOURNAL | T2.3 | replay inconsistency | task | n/a | REC-PH2-JOURNAL | INJ-PH2-03 | ETM | exit gate |
| F-PH2-05 | WSSM/ORCH | T2.1/T2.2 | is_legal False | request | none | deterministic | T-PH2-U1/U2 | ETM | exit gate |
| F-PH2-06 | ORCH | T2.2 | expected-state≠actual | request | none | retry | INJ-PH2-04 | ETM | exit gate |
| F-PH2-07 | LEASE | T2.4 | token/epoch | resource | none | REC-PH2-LEASE | INJ-PH2-05 | ETM | exit gate |
| F-PH2-08 | ORCH/schema | T2.2 | SHA/tx error | DB init | RB-PH2-MIG | fix+re-run | migration test | ETM | exit gate |
| F-PH2-09 | JOURNAL | T2.3 | replay duplication | task | n/a | REC-PH2-JOURNAL | INJ-PH2-01/03 | ETM | exit gate |
| F-PH2-10 | MEM | T2.5 | insert-only violated | record | none | insert-only | T-PH2-U6 | ETM | exit gate |
| F-PH2-11 | ORCH | T2.2 | unique index | request | none | idempotent | INJ-PH2-06 | ETM | exit gate |
| F-PH2-12 | env | (setup) | `uv sync` non-zero | env | n/a | nearest pin | uv.lock | env log | — |
| F-PH2-13 | all | T2.6 | verify non-zero | task | RB-PH2-COMMIT | repair-first §2 | full suite | REPORT | exit gate |

**No unhandled PH-2 failure mode; no orphan recovery/rollback path; no rollback without verification; no repair
without evidence** (each repair logs to the Regression Register). Deferred failure classes are explicitly
owned by later phases.

## 9. Consistency review (this pass)

Cross-checked against `01M §5` (six reconciliation outcomes — used verbatim), `04 §9` (five recovery result
states — used verbatim), `ROLLBACK-PLAN §1` (PH-2 = journal + contract-activation layers — consistent),
PLAN-S2 (failure-path tests exist for INJ-PH2-01/02), VEP-PH2 (REQ-PH2-02/04/05 cover atomicity/reconciliation/
fencing), component specs (failure_modes/recovery_behavior fields align), RISK-REGISTER (RISK-REC-02 blocking
PH-2 mapped by F-PH2-01/02/04/09; RISK-VERIF by F-PH2-13; RISK-DEP-01 by F-PH2-12): **no inconsistency found;
no repair required.** No new PH-2 risk beyond the register; RISK-REC-02 annotated to cite this plan.

## 10. Update rules

Regenerated if PLAN-S2, the component specs, `01M`, `04`, or `ROLLBACK-PLAN` change. Actual failure-injection
results are produced by Task 2.6/failure-path tests at implementation time — not pre-filled (no fabricated
evidence). Superseded by pointer, never deleted.
