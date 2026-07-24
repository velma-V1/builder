# PH-2 Verification, Evidence & Promotion Architecture

**Document ID:** VEP-PH2
**Repository path:** `docs/planning/PH2-VERIFICATION-EVIDENCE-PROMOTION.md`
**Status:** Active — PH-2-scoped verification/evidence/promotion plan (planning Pass 6)
**Authority level:** Plan (subordinate to `01G`, `VERIFICATION-MATRIX`, `TEST-STRATEGY`)
**Owner:** PH-2 planning · **Established:** 2026-07-24
**Governing:** `01G §3.1/§3.2/§3.3/§3.5` (ETM, anti-weakening, verdicts, flaky policy), `VERIFICATION-MATRIX`
(35 categories), `TEST-STRATEGY`, PLAN-S2, the six PH-2 component specs, `PH2-INTEGRATION.md`, RISK-REGISTER.

## 0. Scope & single-authority boundary

This document defines verification/evidence/promotion **for PH-2 only**. The system-wide test taxonomy
(`VERIFICATION-MATRIX` 35 categories), verdict set and anti-weakening/flaky rules (`TEST-STRATEGY`, `01G`),
ETM/promotion-package field schemas (templates), and the promotion concept remain owned by those documents;
this plan cites them and maps PH-2's slice. It produces no product code and requires none — the actual
Section 2 verification **report** (`docs/verification/section-2-...md`) and the `artifacts/verification/
section-2/manifest.json` are generated at implementation time by Task 2.6, not now.

## 1. PH-2 requirements (verification definition per requirement)

Requirement fields per Pass 6: source · owner · acceptance · method · environment · procedure · expected ·
failure · evidence · location · evidence-owner · retention · approval · promotion · rollback. Standing
values: **environment** = ENV-DEV; **evidence location** = `artifacts/verification/section-2/manifest.json`
(gitignored) summarized into `docs/verification/section-2-...md` (committed); **evidence owner** = PH-2
verification (Task 2.6); **retention** = permanent verification report (committed), regenerable manifest;
**approval** = PH-2 exit gate (operator); **promotion** = PROM-PH2; **rollback** = journal-authoritative +
per-task `git revert`. Only deltas below.

| Req ID | Source | Owner (cmp) | Acceptance criterion | Method / Category | Expected | Failure | Risk link |
|---|---|---|---|---|---|---|---|
| REQ-PH2-01 | `01L §3.1` #3-4 | CMP-WSSM/ORCH | only legal transitions occur; illegal fail closed + audit event | unit/contract (#1) | exhaustive matrix: legal legal, all others rejected + `accepted=0` event | any legal rejected or illegal accepted | RISK-ARCH-01 |
| REQ-PH2-02 | `02 §7`, R1 | CMP-ORCH | every state change atomic; single writer; failure leaves prior state | unit + failure-path (#1/#15) | one `accepted=1` event, `sequence`+1; forced pre-commit failure → no change, no row | partial state observable; 2nd writer path | RISK-ARCH-02 |
| REQ-PH2-03 | `02 §6`, R1 | CMP-ORCH | runtime state readable only via read-only interface | security (#5) | `mode=ro` reader denies INSERT/UPDATE/DELETE/CREATE/DROP/ALTER | reader can mutate | RISK-ARCH-02 |
| REQ-PH2-04 | `01M §3.6/§5/§11` | CMP-JOURNAL | startup assigns one outcome/task; no blind resume; replay idempotent | crash + journal-replay (#16/#17) | QUEUED→RESUMABLE; non-terminal→BLOCKED; mismatch→QUARANTINED; replay idempotent | non-terminal→RESUMABLE; mismatch not quarantined; replay duplicates | **RISK-REC-02 (blocks PH-2)** |
| REQ-PH2-05 | `01M §3.6/§3.19/§3.12` | CMP-LEASE | fencing tokens strictly increasing + persistent; stale/prior-epoch owner cannot write | fencing-token (#18) | tokens increase across restart; superseded/prior-epoch rejected | lower/equal token issued; prior-epoch accepted | RISK-REC-02 |
| REQ-PH2-06 | `05 S2`, `01D §3.4` | CMP-TASKENG | deterministic dependency-gated readiness; idempotent restart | unit/scheduler+concurrency (#1) | incomplete-dep not ready; stable order; committed transition not re-admitted | non-deterministic order; re-admission | RISK-SCHED-01 |
| REQ-PH2-07 | `01L §3.1` | CMP-TASKENG | cancellation drives …→STOPPING→CANCELLED legally | unit (#1) | legal transitions only; terminal-task cancel rejected | illegal transition applied | — |
| REQ-PH2-08 | `01F §2/§3` | CMP-MEM | project-authority memory: provenance, status lifecycle, versioned correction, no auto-persist, no secret field | unit/contract (#1) | PROPOSED→VERIFIED only; supersede-by-insert; field set exact (no value field) | in-place edit possible; secret-bearing field present | RISK-DATA-02 |
| REQ-PH2-09 | `01G §3.1`, `01O §2.19` | all PH-2 | migrations SHA-verified+transactional; ≥95% branch cov; full verify green | system/regression/migration (#22/#4) | verify_section2 exit 0; cov ≥95%; all suites PASS | cov<95%; any required non-PASS | RISK-DEP-01, RISK-VERIF-02 |

## 2. PH-2 tests (test definition)

Test fields: purpose · category · components · tasks · contracts · schemas · deps · env · procedure ·
expected · failure · evidence · approval · regression · promotion. Standing: env ENV-DEV; evidence = ETM
row + captured stdout/exit in the manifest; approval = none per-test (PH-2 exit gate covers the package);
regression = re-run in Task 2.6 full suite and on any change (`01G §2.4`); promotion = feeds PROM-PH2.

| Test ID | File | Category | Cmp | Task | Req | Expected result |
|---|---|---|---|---|---|---|
| T-PH2-U1 | `unit/test_transition_policy.py` | unit, contract, interface | WSSM | T2.1 | 01 | exhaustive legal/illegal matrix holds |
| T-PH2-U2 | `unit/test_runtime_state_store.py` | unit, schema | ORCH | T2.2 | 01,02 | legal applies+events; illegal audited; expected-state mismatch rejected |
| T-PH2-SEC1 | `security/test_read_only_state_access.py` | security, permission | ORCH | T2.2 | 03 | read-only reader cannot mutate |
| T-PH2-SEC2 | `security/test_read_only_state_access.py` (append-only assertion) | security, audit-chain | ORCH | T2.2 | 02,03 | direct UPDATE/DELETE on `task_state_events` raises (append-only triggers) — SEC-PH2-02 |
| T-PH2-FP1 | `failure_paths/test_atomic_transition_rollback.py` | rollback, failure-path | ORCH | T2.2 | 02 | forced pre-commit failure → no state change, no event row |
| T-PH2-U3 | `unit/test_journal_reconciliation.py` | recovery, journal-replay | JOURNAL | T2.3 | 04 | mapping table holds; mismatch→QUARANTINED |
| T-PH2-FP2 | `failure_paths/test_startup_reconciliation_after_crash.py` | crash-recovery | JOURNAL | T2.3 | 04 | WAL crash-consistency; no silent resume |
| T-PH2-U4 | `unit/test_fencing.py` | fencing-token, recovery | LEASE | T2.4 | 05 | increasing persistent tokens; stale/prior-epoch rejected; release idempotent |
| T-PH2-U5 | `unit/test_scheduler.py` | scheduler, concurrency | TASKENG | T2.5 | 06,07 | readiness gating; deterministic order; cancellation transitions |
| T-PH2-U6 | `unit/test_memory_records.py` | contract, unit | MEM | T2.5 | 08 | status lifecycle; supersede-by-insert; exact field set |
| T-PH2-INT1 | `integration/test_orchestrator_lifecycle.py` | integration, interface, crash | all | T2.5 | 01-08 | full lifecycle + restart + reconciliation + memory |
| T-PH2-MIG1 | `unit/test_runtime_state_store.py` (migration-runner assertion) | migration, schema | ORCH | T2.2 | 09 | `apply_migrations` records version only on success; failed migration leaves no partial schema/version row (REGR-0003) |
| T-PH2-SYS1 | `scripts/verify_section2.py` | system, regression, migration, evidence-integrity | all | T2.6 | 09 | exit 0; ≥95% cov; manifest hashes recorded |

## 3. Required-test-category applicability to PH-2

| Category (Pass 6 list) | PH-2? | Where / why |
|---|---|---|
| Unit, Integration, System, Regression, Contract, Schema, Interface | **Yes** | §2 tests T-PH2-U1..U6/INT1/SYS1 |
| Security, Permission | **Yes (subset)** | T-PH2-SEC1 (read-only writer boundary); full permission suite is PH-3 |
| Recovery, Rollback, Crash Recovery, Journal Replay | **Yes** | T-PH2-U3/FP1/FP2 (matrix #16/#17) |
| Concurrency, Scheduler | **Yes** | T-PH2-U5 + `BEGIN IMMEDIATE` single-writer serialization |
| Evidence Integrity | **Yes (partial)** | T-PH2-SYS1 manifest hashing; full evidence-store integrity is PH-7 |
| Migration | **Yes** | SHA-verified transactional runner for `0001..0003` (matrix #22) |
| Promotion, Evidence-integrity (full) | Planning-level here | PROM-PH2 §5; full promotion engine is PH-7 |
| Trust Boundary, Sandbox, Path Safety, Audit Chain, Performance, Stress, Model Routing, Tool Gateway, Offline, Windows 11 Home, WSL2, Docker, Installer, Updater, Release Verification | **No — deferred** | owned by `VERIFICATION-MATRIX` categories; bind at PH-3/4/5/8. Recorded, not skipped. |

## 4. PH-2 evidence architecture

Every PH-2 evidence artifact carries the `01G §3.1` ETM fields (see the ETM template). PH-2 evidence set:

| Evidence ID | Type | Creation method | Req/Test/Cmp/Task | Location | Retention | Verdict field |
|---|---|---|---|---|---|---|
| EV-PH2-ETM | Evidence Traceability Manifest (per required criterion) | Task 2.6 report authoring | REQ-PH2-01..09 / §2 tests / all / T2.6 | `docs/verification/section-2-...md` (ETM section) | permanent | per-criterion PASS/… |
| EV-PH2-MANIFEST | run manifest (commands, exit codes, stdout/stderr SHA-256, env identity, git commit, dep-lock hash) | `scripts/verify_section2.py` | REQ-PH2-09 / T-PH2-SYS1 / all / T2.6 | `artifacts/verification/section-2/manifest.json` (gitignored, regenerable) | regenerable | overall exit code |
| EV-PH2-COV | branch-coverage report | pytest-cov `--cov-fail-under=95` | REQ-PH2-09 | in manifest + report | regenerable | ≥95% gate |
| EV-PH2-REPORT | Section 2 verification report (package classification) | Task 2.6 | package | `docs/verification/section-2-...md` | permanent | package PASS |

Evidence rules inherited (not re-decided here): hashes are lowercase SHA-256; proportionate hashing
(`01G §2.19`); a retry-dependent pass is `UNSTABLE` and cannot alone satisfy a required criterion
(`01G §3.5`, RISK-VERIF-02); anti-weakening (`01G §3.2`, RISK-VERIF-01) applies once implementation starts.

## 5. PH-2 promotion architecture — gate PROM-PH2

| Field | Value |
|---|---|
| Promotion ID | PROM-PH2 (PH-2 phase-exit; `docs/10 §15` item 3, `docs/10 §4` exit-gate) |
| Required inputs | all six PH-2 component implementations at their task-completion commits; expanded PLAN-S2 |
| Required evidence | EV-PH2-ETM (complete for every required criterion), EV-PH2-MANIFEST, EV-PH2-COV (≥95%), EV-PH2-REPORT (package PASS) |
| Required tests | every §2 test PASS; no required criterion `FAIL/BLOCKED/INCONCLUSIVE/NOT_TESTABLE`; no `UNSTABLE` required-criterion pass |
| Required approvals | operator phase-exit approval (`docs/10 §15`); no merge/`main` change implied |
| Required reviews | independent verification (a model cannot certify its own work — `01G §1`); deterministic evidence authoritative |
| Required artifacts | Section 2 report + regenerable manifest; PH-2 handoff to PH-3 (Section 3 interfaces) |
| Promotion procedure | run `verify_section2.py` in a clean env → confirm exit 0 + all verdicts PASS + cov ≥95% → finalize report with ETM + integrity hashes → request operator phase-exit approval → record approval in CL-000 |
| Failure conditions | any required criterion non-PASS; coverage <95%; missing/hash-mismatched ETM link; a required pass that is retry-dependent |
| Rollback procedure | journal-authoritative; per-task `git revert`; migrations transactional (no partial schema) |
| Recovery procedure | on failure, fix the implicated task under anti-weakening (`01G §3.2`), re-run the full suite, regenerate evidence |
| Promotion output | PH-2 promoted; Orchestrator substrate available to PH-3; PH-3 entry gate inputs satisfied |

**No promotion without complete evidence:** PROM-PH2 blocks if the ETM is incomplete for any required
criterion (`01G §3.1`), exactly as PH-1's gate did.

## 6. PH-2 traceability matrices

**Requirement → Task / Component / Test / Evidence / Promotion**

| Req | Task | Component | Test(s) | Evidence | Promotion |
|---|---|---|---|---|---|
| REQ-PH2-01 | T2.1/T2.2 | WSSM/ORCH | U1,U2 | ETM,REPORT | PROM-PH2 |
| REQ-PH2-02 | T2.2 | ORCH | U2,FP1 | ETM,REPORT | PROM-PH2 |
| REQ-PH2-03 | T2.2 | ORCH | SEC1 | ETM,REPORT | PROM-PH2 |
| REQ-PH2-04 | T2.3 | JOURNAL | U3,FP2,INT1 | ETM,REPORT | PROM-PH2 |
| REQ-PH2-05 | T2.4 | LEASE | U4,INT1 | ETM,REPORT | PROM-PH2 |
| REQ-PH2-06 | T2.5 | TASKENG | U5,INT1 | ETM,REPORT | PROM-PH2 |
| REQ-PH2-07 | T2.5 | TASKENG | U5,INT1 | ETM,REPORT | PROM-PH2 |
| REQ-PH2-08 | T2.5 | MEM | U6,INT1 | ETM,REPORT | PROM-PH2 |
| REQ-PH2-09 | T2.6 | all | SYS1 | MANIFEST,COV,REPORT | PROM-PH2 |

**Task → Verification / Evidence / Promotion:** each task Tn → its §2 tests → EV-PH2-ETM row(s) → PROM-PH2.
**Component → Verification / Evidence / Promotion:** each CMP → its component-spec `required_tests` → ETM →
PROM-PH2. **Contract → Verification:** CTR-TASK-WS-SM→U1/U2; CTR-RUNTIME-STATE-DB→U2/SEC1/FP1;
CTR-RECOVERY-JOURNAL→U3/FP2; CTR-LEASE-FENCING→U4; CTR-MEMORY-RECORD→U6. **Schema → Verification:**
`0001_state.sql`→U2/SEC1; `0002_leases.sql`→U4; `0003_memory.sql`→U6 (each also exercised by the migration
runner in SYS1). **Approval → Promotion:** operator phase-exit approval → PROM-PH2. **Rollback → Recovery:**
journal-authoritative rollback → reconciliation-based recovery (T2.3), no cross-component coordination
(single writer/DB).

**Orphan check:** every REQ maps to ≥1 task, component, test, evidence, and promotion; every §2 test maps to
≥1 REQ; every evidence artifact maps to ≥1 REQ and test. **No orphan requirement, test, or evidence.**

## 7. Verification validation & consistency review (this pass)

- Every PH-2 requirement has a verification method, an evidence artifact, an owner, and a promotion gate: **PASS**.
- Every promotion-gate input (evidence/tests/approvals/rollback/recovery) is defined: **PASS**.
- Cross-checked against PLAN-S2 (tasks/acceptance), the component specs (`required_tests`), VERIFICATION-MATRIX
  (categories #1/#2/#5/#15/#16/#17/#18/#22), TEST-STRATEGY (verdicts/anti-weakening/flaky), RISK-REGISTER
  (RISK-REC-02 blocking PH-2 is covered by REQ-PH2-04/05; RISK-VERIF-01/02 covered by §4 rules): **no
  inconsistency found; no repair required.**
- The one modeling choice recorded: 17 of the 33 Pass-6 test categories are deferred to PH-3/4/5/7/8 (owned by
  VERIFICATION-MATRIX) rather than authored for PH-2 where they don't apply — deferral is explicit (§3), not a
  silent gap.

## 8. Update rules

Regenerated if PLAN-S2, the component specs, or the governing verification documents change. The actual ETM
rows, manifest, and report are produced by Task 2.6 at implementation time and are not pre-filled here (doing
so would fabricate evidence — forbidden). Superseded by pointer, never deleted.
