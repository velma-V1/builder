# Continuation Ledger

**Document ID:** CL-000
**Repository path:** `docs/planning/00-CONTINUATION-LEDGER.md`
**Status:** Active — cross-session / cross-pass state of record
**Authority level:** Derived index (records state; never overrides a governing source)
**Owner:** Every planning/implementation pass (append + realign)
**Established:** 2026-07-24 (PH-2 planning, Pass 2)

## 1. Purpose

The single running record of where the project actually is, so any new session or pass can resume without
relying on chat history. It records the authoritative branch/HEAD, the approval state of each phase, the
active pass, open decisions, flagged-but-non-blocking items, and the exact next allowed action. It carries no
technical authority — repository evidence and the governing corpus govern; this ledger points at them.

## 2. Current state of record

| Field | Value |
|---|---|
| Date | 2026-07-24 |
| Active repository | `velma-V1/builder` |
| PH-1 implementation branch | `claude/builder-handoff-pr8-inc9p8` (HEAD `14f1f5f`) |
| PH-2 planning branch | `claude/ph2-orchestrator-planning` (forked from `14f1f5f`) |
| `main` | untouched; no merge performed or authorized |
| Active phase | PH-2 (planning only; product implementation NOT started) |
| Active framework | Principal-Architect PH-2 planning framework (10 passes) |
| Active pass | Pass 10 (Final Integration, Validation, Handoff & Certification) — COMPLETE |

## 3. Phase approval state

| Phase | Implementation | Verification evidence | Promotion (operator) |
|---|---|---|---|
| PH-1 (Requirements & Contracts) | Complete | `PASS`, 96.85% cov (`docs/verification/section-1-requirements-contracts.md`, commit `2f37f8d`) | **Promoted for phase-order purposes** by operator (2026-07-24). Final promotion re-verification **flagged as deferred**, non-blocking (`HANDOFF-PH1.md §7`) |
| PH-2 (Orchestrator: Queue & State Machine) | Not started | — | — |
| PH-S, PH-3…PH-8 | Not started | — | — |

## 4. Operator decisions on record (this project)

- **Operator Authority policy:** operator's explicit in-conversation approval is authoritative for workflow
  gates; once given, record and treat as satisfied; do not re-request absent new repository evidence.
- **PH-1:** "its promoted just flag it for later and move on to ph-2." → PH-1 promoted for phase order;
  final verify deferred; **do not merge PH-1 or modify `main`**; **do not re-request F-01**.
- **F-06 resolved:** PH-2 planning authorized now.
- **PH-2 planning branch:** `claude/ph2-orchestrator-planning` from latest `claude/builder-handoff-pr8-inc9p8`.
- **Constraint:** do not begin PH-2 *product implementation* yet (planning only).
- **Pass protocol:** each pass runs the Repository Realignment Protocol, stops after its report, and waits
  for exactly `CONTINUE` before the next pass.

## 5. Flagged / deferred (non-blocking)

- **DEF-01 — RESOLVED (2026-07-24):** PH-1 final re-verification executed at commit `c3d085e` via
  `scripts/verify_section1.py`: overall exit 0; ruff/mypy/all suites green; **288 passed / 1 skipped
  (Windows-only), 96.85% branch coverage** — matches the recorded S1 evidence
  (`docs/verification/section-1-requirements-contracts.md`). Regenerable manifest at
  `artifacts/verification/section-1/manifest.json` (gitignored). PH-1 is verified at the current head.
- **DEF-02 — RESOLVED (2026-07-24):** PR #6 (competing stale Section-1 attempt via local Aider+Ollama,
  based on pre-freeze `main` `d06c7537`, all task gates unchecked) **closed as superseded** by the completed +
  verified PH-1 implementation. Supersession comment posted; `main` untouched.
- **DEF-03** — `HANDOFF-PH1.md §7` forward-references an "expanded section-2 plan"; that expansion lands on
  the PH-2 planning branch. Reconcile the reference when PH-2 planning merges. Non-blocking.
- **Planning gaps G-01…G-08** — see `docs/planning/00-PLANNING-AUTHORITY-LEDGER.md §6`. Each owned by a named
  later pass. Non-blocking for PH-2 planning.
- **REGR-0002 — CLEARED (T2.2):** append-only-trigger tests implemented and passing in
  `tests/orchestrator/security/test_read_only_state_access.py`.
- **REGR-0003 — CLEARED (T2.2):** migration-runner transactional-safety tests implemented and passing in
  `tests/orchestrator/unit/test_runtime_state_store.py`.

## 5a. PH-2 implementation progress (branch `claude/ph2-orchestrator-implementation`)

DEF-01/DEF-02 resolved; PH-2 planning merged via **PR #9** into `claude/builder-handoff-pr8-inc9p8`
(`9280d24`); implementation branch cut from there. `main` untouched throughout.

| Task | Component | Status | Commit |
|---|---|---|---|
| T2.1 | CMP-WSSM (states + transition policy) | DONE (43 tests) | `1a96f46` |
| T2.2 | CMP-ORCH (runtime store + writer) | DONE (62 tests cumulative; REGR-0002/0003 cleared) | (this commit) |
| T2.3 | CMP-JOURNAL (reconciliation) | DONE (68 tests cumulative) | (this commit) |
| T2.4 | CMP-LEASE (fenced leases) | DONE (76 tests cumulative) | (this commit) |
| T2.5 | CMP-TASKENG + CMP-MEM | pending | — |
| T2.6 | verification + evidence report | pending | — |

## 6. Pass log

| Pass | Scope | Verdict | Artifacts |
|---|---|---|---|
| PH-2 Pass 1 | Implementation-readiness realignment | `READY_FOR_PH2_ARCHITECTURE_PLANNING` | (analysis only; no files) |
| PH-2 Pass 2 | Implementation-planning hierarchy | `PASS_WITH_NONBLOCKING_GAPS` | `00-PLANNING-AUTHORITY-LEDGER.md`, `00-CONTINUATION-LEDGER.md` |
| PH-2 Pass 3 | Master implementation roadmap (execution companion) | `PASS_WITH_NONBLOCKING_GAPS` | `docs/10A-ROADMAP-EXECUTION-MAP.md` |
| PH-2 Pass 4 | Component implementation specifications (6 PH-2 components + integration) | `PASS_WITH_NONBLOCKING_GAPS` | `docs/specifications/components/{orchestrator,workstream-state-machine,task-engine,recovery-journal,lease-fencing,memory-core}-spec.md`, `PH2-INTEGRATION.md` |
| PH-2 Pass 5 | Task-by-task implementation spec (PH-2 T2.1–T2.6 + execution graph + parallel review) | `PASS_WITH_NONBLOCKING_GAPS` | `docs/plans/section-2-task-queue-and-state-machine.md` (expanded) |
| PH-2 Pass 6 | Verification/evidence/promotion architecture (9 reqs, 11 tests, PROM-PH2, traceability) | `PASS_WITH_NONBLOCKING_GAPS` | `docs/planning/PH2-VERIFICATION-EVIDENCE-PROMOTION.md` |
| PH-2 Pass 7 | Failure/recovery/rollback/resilience plan (13 failure modes, checkpoints, rollback, recovery, injections, traceability) + Regression Register established | `PASS_WITH_NONBLOCKING_GAPS` | `docs/planning/PH2-FAILURE-RECOVERY-ROLLBACK.md`, `docs/planning/REGRESSION-REGISTER.md` |
| PH-2 Pass 8 | Security/trust-boundary plan (5 assets, 7 threats, 7 security tests, traceability) + 1 repair (REGR-0002) | `PASS_WITH_NONBLOCKING_GAPS` | `docs/planning/PH2-SECURITY-TRUST-BOUNDARIES.md`; edits to PLAN-S2, VEP-PH2, REGRESSION-REGISTER |
| PH-2 Pass 9 | Deployment/migration plan (platform footprint, 3 runtime migrations, PH-8 deferral) + 1 repair (REGR-0003) | `PASS_WITH_NONBLOCKING_GAPS` | `docs/planning/PH2-DEPLOYMENT-MIGRATION.md`; edits to PLAN-S2, VEP-PH2, REGRESSION-REGISTER |
| PH-2 Pass 10 | Final integration/validation/handoff/certification (inventory, 10 audits, handoff, start package, certificate) | `PH2_CERTIFIED_WITH_NONBLOCKING_GAPS` | `docs/planning/PH2-IMPLEMENTATION-READINESS-CERTIFICATE.md` |

## 7. Next allowed action

**PH-2 planning is COMPLETE (Passes 1–10).** Pass 10 produced the Implementation-Readiness Certificate
(CERT-PH2, verdict `PH2_CERTIFIED_WITH_NONBLOCKING_GAPS`). The entire PH-2 implementation-planning package is
repository-native and usable without chat history — a future implementer starts at
`docs/planning/PH2-IMPLEMENTATION-READINESS-CERTIFICATE.md`.

**Required operator action to proceed:** explicit authorization to begin **PH-2 product implementation**
(first task T2.1, per CERT-PH2 §7). Until then: do not begin implementation, do not merge, do not modify
`main`, do not open/close/modify PRs, do not promote branches. Open items: REGR-0002 / REGR-0003 (clear
during implementation); DEF-01 (PH-1 re-verify); DEF-02 (PR #6).

## 8. Update rules

Append/realign at the start and end of every pass. Never delete rows; supersede with a pointer. Correct any
field that repository evidence contradicts, and record the correction in the pass log.

## 9. Realignment — 2026-07-25 (PH-2 complete; Worker Execution Substrate reclassified)

This section supersedes the stale fields in §2/§3/§5a above (kept per the never-delete rule).

**Current authoritative state**

| Field | Value |
|---|---|
| Date | 2026-07-25 |
| `main` | untouched; no merge performed or authorized |
| PH-2 (Orchestrator) | **COMPLETE** on `claude/ph2-orchestrator-implementation` @ `7e023a2`; 93 tests; PROM-PH2 passed; **not merged** (by standing "do not modify main") |
| Active branch | `claude/ph3-worker-engine` (HEAD moves with the reclassification commit) |
| Roadmap PH-3 (Watchdog, Permissions, Approval, Audit & Tools) | **NOT started / UNBUILT** — plan `docs/plans/section-3-orchestrator-watchdog-and-permissions.md` unchanged |
| Worker Execution Substrate (`CMP-WORKER`) | **COMPLETE** on `claude/ph3-worker-engine`; 85 substrate + 93 PH-2 = 178 tests; substrate gate 18/18. **Reclassified as prebuilt PH-4/PH-5 execution infrastructure — NOT roadmap PH-3.** See `docs/WORKER-EXECUTION-SUBSTRATE-CLASSIFICATION.md` |
| PH-4 … PH-8 | Not started |

**Operator decision on record (2026-07-25):** the work on `claude/ph3-worker-engine` is **not** roadmap
PH-3. It is the **Worker Execution Substrate** (Options A+C: reclassify, do not amend the roadmap, treat as
prebuilt PH-4/PH-5 seam). Roadmap PH-3 remains the Watchdog security spine and is still to build. The real
`ProcessSpawner`/sandbox isolation remain PH-5; **PH-4 may consume the substrate seam only after roadmap
PH-3 security interfaces (permission enforcement + tool gateway) are frozen**. No roadmap dependency is
bypassed.

**Branch supersession:** `claude/ph3-worker-engine-xefzze` — tip `7e023a2` (the PH-2 base), **zero commits
unique to it**, not on the remote. **No unique required work → SUPERSEDED by `claude/ph3-worker-engine`.**
Left inert; not fast-forwarded.

**Next allowed action:** prepare the Worker Execution Substrate reclassification PR (base `main`, head
`claude/ph3-worker-engine`); **do not merge; do not modify `main`**; await explicit merge authorization.
After merge, the next roadmap phase to plan/build is **roadmap PH-3 (Watchdog/Permissions/Approval/Audit/
Tools)**.

## 10. Realignment — 2026-07-25 (Roadmap PH-3 planning started; Pass 2 complete)

Supersedes the prior "active branch / next allowed action" fields for the purpose of roadmap PH-3 planning
(earlier sections retained per the never-delete rule). Roadmap PH-3 is the **Watchdog security spine** and is
distinct from the Worker Execution Substrate (out-of-roadmap; `docs/WORKER-EXECUTION-SUBSTRATE-CLASSIFICATION.md`).

**Current authoritative state**

| Field | Value |
|---|---|
| Date | 2026-07-25 |
| `main` | untouched (`9bce1ca`); no merge performed or authorized |
| PR #10 (Worker Execution Substrate) | open / draft / **unmerged**; head `claude/ph3-worker-engine` @ `7b1922e`; **not modified** |
| Active branch | `claude/roadmap-ph3-security-spine-planning` (forked from `claude/ph3-worker-engine` @ `7b1922e`) |
| Active phase | **Roadmap PH-3 planning** (Watchdog/Permissions/Approval/Audit/Tools) — **planning only; no implementation** |
| Active framework | Principal-Architect planning framework (per-pass: realign → report → `CONTINUE`) |
| Roadmap PH-3 implementation | **UNBUILT** — target dirs `src/factory/{watchdog,permission,approval,audit,tools,fileops,diagnostics}` absent |
| Worker Execution Substrate (`CMP-WORKER`) | COMPLETE on `claude/ph3-worker-engine`; out-of-roadmap; **NOT roadmap PH-3** |
| PH-1 / PH-2 | COMPLETE (unmerged) |

**Operator decisions on record (2026-07-25)**

- Session switched to `claude/ph3-worker-engine` and re-verified; temp branch
  `claude/repository-realignment-handoff-esxexm` (created from `main`, lacking all PR #10 work) **abandoned**.
- Authorized **roadmap PH-3 planning only**: do not modify or merge PR #10; do not modify `main`; do not
  implement PH-3 code.
- Planning corpus authored on dedicated branch `claude/roadmap-ph3-security-spine-planning` from `7b1922e`.
- **Keep roadmap PH-3 identifiers separate from the substrate** — satisfied by the `RPH3` namespace
  (PLANNING-AUTHORITY-LEDGER §9.1).
- Per-pass protocol: complete one pass, report, stop, await explicit `CONTINUE`.

**Roadmap PH-3 planning pass log**

| Pass | Scope | Verdict | Artifacts |
|---|---|---|---|
| RPH3 Pass 1 | Implementation-readiness realignment (readiness verdict, governing inputs, task/contract inventory, pass plan) | `READY_FOR_RPH3_ARCHITECTURE_PLANNING` | analysis only; no files |
| RPH3 Pass 2 | Planning-hierarchy realignment: `RPH3` identifier namespace + planning-document registry | `PASS_WITH_NONBLOCKING_GAPS` | `docs/planning/00-PLANNING-AUTHORITY-LEDGER.md §9`; `docs/planning/00-CONTINUATION-LEDGER.md §10` (this) |
| RPH3 Pass 3 | Roadmap-execution environment alignment: PH-3 row disambiguated to `RPH3`; §3A per-task execution detail; §4 PH-2→RPH3→{PH-4,PH-5} order validation | `PASS_WITH_NONBLOCKING_GAPS` | `docs/10A-ROADMAP-EXECUTION-MAP.md` (header, §2, §3 row, §3A, §4, §5) |
| RPH3 Pass 4 | Component implementation specifications (9 RPH3 component specs + integration review); resolved file-op gap by adding CMP-FILEOP (#40) | `PASS_WITH_NONBLOCKING_GAPS` | `docs/specifications/components/{watchdog,permission,approval,audit-writer,audit-validator,tool-registry,tool-gateway,safe-mode,file-op-service}-spec.md`, `RPH3-INTEGRATION.md`; edits to `00-COMPONENT-MAP.md`, PAL §9 |
| RPH3 Pass 5 | Task-by-task executable plan: expanded PLAN-S3 (RPH3-T1…T5, frozen-input decl, exec graph, VM-2 path, `01M`/`01K`/Dec A-B coverage map, 4 external PR#10 blockers XIB-01..04, self-verification) | `PASS_WITH_NONBLOCKING_GAPS` | `docs/plans/section-3-orchestrator-watchdog-and-permissions.md` (full expansion); PAL §9.2 |
| RPH3 Pass 6 | Verification/evidence/promotion architecture: VEP-RPH3 (18 VR rows, test categories, ETM, VM-2 gate, `PROM-RPH3`); resolved gap G-06 (VERIFICATION-REPORT template) | `PASS_WITH_NONBLOCKING_GAPS` | `docs/planning/RPH3-VERIFICATION-EVIDENCE-PROMOTION.md`, `docs/templates/VERIFICATION-REPORT.template.md`; PAL §9.2/§9.4 |
| RPH3 Pass 7 | Failure/recovery/rollback: FRR-RPH3 (18 FM rows, recovery, per-task rollback, injections, resilience); resolved gap G-02 (RESOURCE-ALLOCATION-PLAN) | `PASS_WITH_NONBLOCKING_GAPS` | `docs/planning/RPH3-FAILURE-RECOVERY-ROLLBACK.md`, `docs/planning/RESOURCE-ALLOCATION-PLAN.md`; PAL §3/§9.2/§9.4 |
| RPH3 Pass 8 | Security/trust-boundaries: SEC-RPH3 (8 assets, 13 threats→controls, 4 trust zones, 7 core-control invariants, SEC-RPH3-01..12); PH-5 isolation + substrate blockers kept out of scope | `PASS_WITH_NONBLOCKING_GAPS` | `docs/planning/RPH3-SECURITY-TRUST-BOUNDARIES.md`; PAL §9.2 |
| RPH3 Pass 9 | Deployment/migration: DEP-RPH3 (platform footprint, PH-3 schemas/migrations, migration ordering/rollback); **resolved ODI-RPH3-01** to a separate PH-3-owned store (frozen PH-2 untouched); reconciled Pass-4 spec phrasing + SCHEMA-REGISTRY + PLAN-S3 file map | `PASS_WITH_NONBLOCKING_GAPS` | `docs/planning/RPH3-DEPLOYMENT-MIGRATION.md`; edits to SCHEMA-REGISTRY, PLAN-S3, permission/approval/tool-registry specs, RPH3-INTEGRATION; PAL §9.2 |
| RPH3 Pass 10 | Final integration/certification: CERT-RPH3 (corpus inventory, 12 readiness audits all PASS, implementation-start package, `PROM-RPH3`); resolved gap G-05 (PHASE-EXIT-CHECKLIST template). **RPH3 planning COMPLETE.** | `RPH3_CERTIFIED_WITH_NONBLOCKING_GAPS` | `docs/planning/RPH3-IMPLEMENTATION-READINESS-CERTIFICATE.md`, `docs/templates/checklist/PHASE-EXIT-CHECKLIST.template.md`; PAL §3/§9.2/§9.4 |

**Next allowed action**

**Autonomous-run authorization (2026-07-26):** operator authorized continuing through all remaining RPH3
planning passes (6–10) without stopping between passes; pause only for a genuine operator decision, an
unresolved contradiction, an unrepairable verification failure, implementation authorization, PR-merge
authorization, or a change to approved architecture. Standing constraints unchanged (no implementation, no
merge, `main`/PR #10 untouched, roadmap not amended).

Proceeding to **RPH3 Pass 6** (verification/evidence/promotion architecture — VEP-RPH3) and onward through
Pass 10 (readiness certificate).

### RPH3 planning COMPLETE (2026-07-26)

All ten RPH3 planning passes are complete on `claude/roadmap-ph3-security-spine-planning`. Certificate:
`CERT-RPH3` — verdict `RPH3_CERTIFIED_WITH_NONBLOCKING_GAPS`. The roadmap PH-3 implementation-planning package
is repository-native and usable without chat history; a future implementer starts at
`docs/planning/RPH3-IMPLEMENTATION-READINESS-CERTIFICATE.md`.

**Decision gate — nothing pre-authorized.** Plausible next actions (operator selects):
1. Authorize **roadmap PH-3 product implementation** (first task RPH3-T4, Lane B audit foundation).
2. Authorize a **dedicated PR #10 correction** to clear the four substrate blockers XIB-01..04 (separate from
   RPH3; owned by that correction / PH-5).
3. Merge PR #10 (Worker Execution Substrate) into `main` — still draft/unmerged.
4. Other operator-directed work.

**Standing constraints (in force until explicitly lifted):** no implementation without authorization; no merge
to `main`; do not modify `main`; roadmap not amended; RPH3 identifiers stay disjoint from the substrate; the
four substrate blockers are external prerequisites for any PR #10 merge, not RPH3 work.

### RPH3 Pass-10 certification REJECTED — verdict downgraded (2026-07-26)

Operator **rejected** the Pass-10 certification. Commit `1d3b860` issued verdict
`RPH3_CERTIFIED_WITH_NONBLOCKING_GAPS` for an **invalid planning state**: its audits did not detect (a)
`01M`/`01K` traceability defects — decision-list numbers (`01M §2` 36 decisions, `01K §2` 33 decisions)
conflated with acceptance criteria (`01M §6` 32, `01K §5` 25), and ambiguous `01M #NN`/`01K #NN` references;
(b) architecture gaps — no crash-consistent cross-store protocol, no defined Watchdog intervention receiver,
false implication that the frozen PH-2 transition writer can execute non-transition interventions; (c) stale
migration/dependency contradictions (`migrations/runtime/0004_*`, audit-append-via-CMP-ORCH, a `10A` claim
that RPH3 consumes CMP-LEASE); (d) PH-5 enforcement (process-tree termination, orphan prevention, sandbox
quarantine/recording/evidence) falsely certifiable under `PROM-RPH3`; (e) no enforceable shared-store ownership.

**Verdict downgraded to `RPH3_PLANNING_REPAIR_REQUIRED`.** Continuous corpus repair in progress on
`claude/roadmap-ph3-security-spine-planning` (autonomous; logical corrections committed separately); a
corrected certificate is issued only after the full final audit passes. Standing constraints unchanged.

### RPH3 planning repair COMPLETE — corrected certification (2026-07-26)

Repair commits R1–R7 landed. Defect classes cleared: **D1** (rebuilt `01M-AC-01..32`/`01K-AC-01..25` +
`01M-DEC`/`01K-DEC` traceability in TRACE-RPH3; corpus-wide identifier rewrite; output-validation → `01K-DEC-25`
not `01K-AC-25`); **D2** (XSC-RPH3 crash-consistent cross-store protocol, audit-as-commit-point, every crash
window, fail-closed); **D3** (WIR-RPH3 Watchdog intervention receiver; no false `apply_transition` claim;
INERT PH-5/PH-7 commands); **D4** (separate PH-3 stores `migrations/security/0001` + `migrations/audit/0001`;
audit not via CMP-ORCH; CMP-LEASE not consumed); **D5** (PH-5 enforcement gates `EG-PH5-01..10` excluded from
`PROM-RPH3`); **D6** (DEP-RPH3 §4A structural store-ownership enforcement).

Repository-wide final audit: **22/23 automated checks PASS**, the one flag a filter false-positive on the
"no-reuse" declarations (zero actual substrate-identifier reuse; corpus uses `PROM-RPH3`/`SEC-RPH3-*`).
Implementation files untouched (docs-only). New authoritative docs: TRACE-RPH3, XSC-RPH3, WIR-RPH3.

**Corrected verdict: `RPH3_CERTIFIED_WITH_NONBLOCKING_GAPS` (v2).** Certifies **planning readiness only** — NOT
implementation authorization, NOT merge authorization, NOT PH-3 completion.

### RPH3 planning repair — review round 2 (2026-07-26)

Operator review of the v2 certificate: "major improvement, but would not authorize implementation yet" — four
further corrections. Repaired in R8–R11 (still autonomous, docs-only):
- **Correction 1 (R8):** XSC-RPH3 replaced the `authoritative ⟺ audited` biconditional with **3 operation
  classes** (reversible security-store / frozen-PH-2 transition / external-irreversible) + **INV-1..INV-4**; no
  fabricated rollback; uncertain external outcomes → `UNCERTAIN`→`QUARANTINED`; every WIR command mapped to its
  class (`RESTART_SERVICE` = Class 3). (defect D7)
- **Correction 2 (R9):** DEP-RPH3 migration inventory now defines the `*_intents` tables + `intervention_journal`
  with `op_key`/status/reconciliation/audit_seq columns, audit `UNIQUE(op_key, record_kind)` (R12), indexes, ownership, retention,
  migration-order. (D8)
- **Correction 3 (R10):** split `01M-AC-19`, `01K-AC-21`, `01M-AC-30` into an RPH3 request/containment half +
  PH-5/PH-7 enforcement gates (`EG-PH5-11/12`, `EG-PH7-01..03`); no obligation removed. (D9)
- **Correction 4 (R11):** CERT-RPH3 restructured — top-level verdict now v2 certified, the interim
  `RPH3_PLANNING_REPAIR_REQUIRED` is closed (not active), the v1 body moved to
  `docs/planning/superseded/RPH3-CERT-v1-SUPERSEDED.md` (INVALID/historical); reproducible evidence in
  `docs/verification/rph3-planning-audit.md` (**28/28 checks, 0 false positives**).

Standing constraints unchanged; next action requires explicit operator authorization to begin roadmap PH-3
implementation (first task RPH3-T4).

### RPH3 planning repair — review round 3 (R12, 2026-07-26)

Operator review of the round-2 v2 certificate found **one blocking architectural contradiction** and **one
evidence defect**; verdict returned to `RPH3_PLANNING_REPAIR_REQUIRED` pending R12. Both fixed in R12
(docs-only):
- **D10 (blocking):** the audit store's `UNIQUE(op_key)` made **Class 3 impossible** — it needs both an
  `INTENT` (pre-execution) and a `COMPLETION` (post-execution) audit record. Fixed: audit store now
  **`UNIQUE(op_key, record_kind)`** with `record_kind ∈ {INTENT, COMPLETION}` (≤1 each per op; Class-3
  completion cannot precede intent); operation-intent tables keep `op_key` unique. Updated XSC-RPH3
  §1/§2/§3/§6/§9, DEP-RPH3 §3/§3.1, SCHEMA-REGISTRY, audit-writer-spec (append-only unchanged — two distinct
  rows, no update).
- **D11 (evidence):** the audit report named `59eb778` + uncommitted edits and recorded an unclean tree.
  Fixed: report re-run against the clean committed R12 tree; the uncommitted-tree record is replaced with
  clean-tree + remote-head verification; totals updated to **30/30** with the new Class-3 audit-record
  cardinality checks. **R12 = `5a5e10310b6e9f12022970e61fcd09e4ec8877a5`** (parent `971d49e`).
- **R13 (evidence hygiene, docs-only):** per operator note, the audit report now literally prints
  `Reviewed commit: 5a5e10310b6e9f12022970e61fcd09e4ec8877a5`, and this ledger records the same SHA; the
  certificate wording is corrected accordingly. R13 changes no reviewed artifact.

Recommendation on record: `READY_FOR_OPERATOR_AUTHORIZATION_OF_RPH3-T4`.

### RPH3-T4 implementation (audit foundation) — 2026-07-26

Operator authorization received (`AUTHORIZED: BEGIN RPH3-T4 ONLY`, from tip `76f1162`). Implemented the
tamper-evident audit chain (CMP-AUDITW writer + CMP-AUDITV validator) — the first genuine RPH3 implementation
gate — on `claude/roadmap-ph3-security-spine-planning`. **Lane A / Watchdog remain paused; no other RPH3 task
started; PR #10 unmerged; `main` untouched.**

Delivered (authorized 10-step sequence):
1. `migrations/audit/0001_audit_chain.sql` — separate append-only hash-chained store; `record_kind ∈
   {INTENT, COMPLETION}`; **`UNIQUE(op_key, record_kind)`**; `BEFORE UPDATE/DELETE` `RAISE(ABORT)`; SHA-256
   pinned in the writer (mirrors CMP-ORCH's runner).
2. `src/factory/audit/{models,errors}.py` — `RecordKind`, `AuditEvent` (no chain-identity fields →
   forge-resistant), `AuditRecord` (+ `compute_hash`), `BreakClass`, `IntegrityVerdict`, `ChainHead`.
3. `src/factory/audit/writer.py` — `AuditWriter` sole appender (sequence=prev+1, genesis anchor, computes all
   chain-identity fields), head/export, fail-closed.
4. `src/factory/audit/validator.py` — `AuditValidator` read-only; verify_chain/verify_export/classify_break.
5. `UNIQUE(op_key, record_kind)` enforcement (≤1 INTENT + ≤1 COMPLETION; duplicate rejected).
6. Class-3 completion-after-intent enforcement.
7. Concurrency + duplicate handling (retry past a taken sequence; no fork/gap; exhaustion fails closed).
8. Partial-write fault injection (failed append rolls back; mid-apply migration fails closed).
9. Chain-corruption + tampering tests (deletion / truncation / reorder / rewrite / bad-anchor, incl. a
   consistent re-forge — record self-verifies but is still detected via linkage / expected-head).
10. Evidence report `docs/verification/roadmap-ph3-t4-audit-evidence.md` + gate `scripts/verify_roadmap_ph3_t4.py`.

Results: **42 audit tests pass** (99.34% branch coverage on `src/factory/audit`); **full repo 508 passed,
1 skipped (Windows-only) — no regression**; ruff clean; mypy --strict clean; T4 gate **9/9 PASS**.

### RPH3-T3 implementation (Approval Engine / CMP-APPROVAL) — 2026-07-26

Operator authorization received ("Implement the Approval Engine next … RPH3-T3 is the only newly authorized
gate"; T4 accepted). Implementing CMP-APPROVAL on `claude/roadmap-ph3-security-spine-planning`. **Lane A /
Watchdog remain paused; RPH3-T2 and RPH3-T5 not started; PR #10 unmerged; `main` untouched; the accepted T4
audit foundation is unmodified.**

**Contradiction found + resolution (migration packaging).** `DEP-RPH3 §3/§3.1` (frozen) pins
`migrations/security/0001_security_spine.sql` to **all** security-spine tables created in a **single**
transaction (permission + approval + tool records, all `*_intents`, and `intervention_journal`). RPH3-T3 can
build only the **approval** tables — the permission/tool/watchdog domain-record schemas are unspecified by any
frozen doc and designing them is T2/T5/WIR work that the T3 boundary forbids.
- **Wrong fix (reverted):** an earlier T3 draft **edited `DEP-RPH3 §3` in place** to describe incremental
  per-task migrations. Editing a frozen normative plan to fit an implementation is not allowed; the operator
  flagged it and it was reverted (`git checkout -- docs/planning/RPH3-DEPLOYMENT-MIGRATION.md`; frozen doc now
  byte-identical to its committed form).
- **Resolution (recorded, not absorbed):** the frozen doc stays untouched; the incremental-migration rationale
  and the **honest deviation disclosure** live in a new **non-normative** note,
  `docs/planning/RPH3-T3-IMPLEMENTATION-NOTE.md`. The approval-only `0001_security_spine.sql` **does deviate**
  from the frozen literal single-file inventory (it is not silent conformance) but preserves every frozen
  *invariant* (ODI-RPH3-01 store boundary, §4A single-writer, §3.1 intent shape verbatim, XSC-RPH3 Class-1
  ordering/reconciliation, SHA-pinned runner) and the frozen *end-state table set*. **Planning debt:**
  `DEP-RPH3 §3/§3.1` must be **formally amended** (operator-signed, via the normal change process) when
  RPH3-T2/T5/WIR land, to describe the store as an ordered set of per-task SHA-pinned migrations. This is
  flagged for **operator acceptance**, not self-certified.

Delivered (authorized scope):
1. `migrations/security/0001_security_spine.sql` — approval domain only: `approval_records`
   (+`commit_state`/`prior_state` XSC Class-1 marker, `requires_confirmation` for 01K §2.10-11),
   `approval_queue`, `approval_intents` (XSC §3.1 shape verbatim + 3 indexes). SHA-256 pinned in the store
   (`099ae959d6f06c6b944925af151d8fa8dd2b65fdffd63660cf2a4355b7878a51`).
2. `src/factory/approval/{errors,models}.py` — `ApprovalState`, `CommitState`, `ApprovalRequest`,
   `ApprovalCard` (full 01L §3.2 scope + `is_complete`), `ApprovalRecord`, `Denial`, `OperatorDecision`,
   `action_fingerprint`, `Clock`.
3. `src/factory/approval/store.py` — SHA-pinned `apply_security_migrations`; read-only `SQLiteApprovalReader`;
   `_approval_writer_authorizer` (writer partition); `audit_completion_seq` (read-only `op_key` join into the
   audit store).
4. `src/factory/approval/writer.py` — private, un-exported `_ApprovalWriter` (sole writer): stage / commit /
   rollback XSC Class-1 primitives.
5. `src/factory/approval/engine.py` — `ApprovalEngine`: enqueue / decide / consume / revoke / expire /
   is_valid / reconcile_startup; every lifecycle event Class-1-audited via CMP-AUDITW; security violations
   denied + audited, never queued; fail-closed on audit failure.
6. Tests present so far: `tests/approval/unit/test_engine.py`, `tests/approval/security/
   test_binding_and_reuse.py`, `tests/approval/failure_paths/test_crash_reconciliation.py`,
   `tests/approval/conftest.py`. **NOT yet written:** integration tests, a store-unit test,
   `scripts/verify_roadmap_ph3_t3.py`, and `docs/verification/roadmap-ph3-t3-approval-evidence.md`.

#### RPH3-T3 status: `RPH3-T3_COMPLETE — READY_FOR_OPERATOR_REVIEW`

Approval Engine (CMP-APPROVAL) complete against `approval-spec`, `XSC-RPH3` Class-1, and `DEP-RPH3`
§2/§3/§4A. **Not yet operator-accepted; not `PROM-RPH3`.**

- **Delivered:** `migrations/security/0001_security_spine.sql` (approval domain; SHA-pinned
  `099ae959d6f06c6b944925af151d8fa8dd2b65fdffd63660cf2a4355b7878a51`); `src/factory/approval/{errors,
  models,store,writer,engine,__init__}.py`; tests (unit / store / security / failure-path / integration);
  `scripts/verify_roadmap_ph3_t3.py`; `docs/verification/roadmap-ph3-t3-approval-evidence.md`;
  `docs/planning/RPH3-T3-IMPLEMENTATION-NOTE.md`.
- **Tests (exact):** `tests/approval` = **56 passed, 0 failed** (unit 27, security 9, failure-path 16,
  integration 4). Full repo = **564 passed, 1 skipped** (Windows-only; +56 vs 508 at T4, no regression).
- **Coverage (exact):** `src/factory/approval` = **100.00% branch** (obligation ≥95%).
- **Static analysis (exact):** ruff `src/factory/approval tests/approval scripts/verify_roadmap_ph3_t3.py`
  → **clean**; mypy --strict `src/factory/approval tests/approval` → **clean (14 files)**.
- **Verifier:** `scripts/verify_roadmap_ph3_t3.py` → **9/9 PASS**.
- **Migration-contract question RESOLVED:** operator adopted the **ordered per-domain migration model**
  (single security-spine SQLite; one SHA-pinned migration per authorized domain; never edit an applied
  migration). `DEP-RPH3 §3/§3.1` **amended** (operator-authorized 2026-07-30) to describe it; cumulative
  end-state inventory unchanged; `0001_security_spine.sql` retained as the approval bootstrap.
- **Boundaries held:** Lane A / Watchdog paused; RPH3-T5 not started; PR #10 unmerged; `main` untouched;
  the accepted T4 audit foundation unmodified. (RPH3-T2 authorized next in this run.)

### RPH3-T2 implementation (Permission Enforcement / CMP-PERM) — 2026-07-30

Operator authorized autonomous continuation (T3 → T2 → T5). Migration model **resolved** by the operator:
ordered per-domain migrations in one security-spine store; `DEP-RPH3 §3/§3.1` and `SCHEMA-REGISTRY.md`
amended accordingly (directly-affected plans/registries only).

#### RPH3-T2 status: `RPH3-T2_COMPLETE — READY_FOR_OPERATOR_REVIEW`

Permission Enforcement (CMP-PERM) complete against `permission-spec`, `01R` Dec A/B, `XSC-RPH3` Class-1,
`DEP-RPH3` §2/§3/§4A. **Not yet operator-accepted; not `PROM-RPH3`.**

- **Delivered:** `migrations/security/0002_permission.sql` (permission domain; SHA-pinned
  `a65d227d9683eb060c834ae8b3cb65f33186ba37420b4065eec8623f8ded88cb`; `CREATE TABLE IF NOT EXISTS
  schema_migrations` so it composes with `0001` in canonical order); `src/factory/permission/{errors,
  models,autonomy,store,writer,engine,__init__}.py`; tests (unit / autonomy / store / security /
  failure-path / integration); `scripts/verify_roadmap_ph3_t2.py`;
  `docs/verification/roadmap-ph3-t2-permission-evidence.md`. **Path safety reuses** the tested
  `factory.contracts.validation.paths.PathAuthority` (canonicalize + contain + TOCTOU) rather than
  reinventing it.
- **Behavior:** least-privilege deny-by-default `decide` (allow/deny/requires-approval); Decision B (every
  deletion approval-gated — no auto-delete path); Decision A (autonomy envelope); path escapes (#10)
  denied; scoped/expiring/revocable grants; TOCTOU `revalidate`; XSC-RPH3 Class-1 (issue/revoke/expire) via
  CMP-AUDITW; startup reconciliation; fail-closed on audit/storage failure; private `_PermissionWriter`
  sole-writer with an authorizer that denies writes to `approval_*` and any non-permission table.
- **Tests (exact):** `tests/permission` = **69 passed, 0 failed** (unit 33, security 18, failure-path 15,
  integration 3). Full repo = **633 passed, 1 skipped** (Windows-only; +69 vs 564 at T3, no regression).
- **Coverage (exact):** `src/factory/permission` = **100.00% branch** (obligation ≥95%).
- **Static analysis (exact):** ruff `src/factory/permission tests/permission
  scripts/verify_roadmap_ph3_t2.py` → **clean**; mypy --strict `src/factory/permission tests/permission`
  → **clean (16 files)**.
- **Verifier:** `scripts/verify_roadmap_ph3_t2.py` → **10/10 PASS**.
- **Boundaries held:** Lane A / Watchdog paused; RPH3-T5 not started (authorized next); PR #10 unmerged;
  `main` untouched; the accepted T4 audit foundation and the T3 approval domain unmodified.

### RPH3-T5 implementation (Tools enforcement) — 2026-07-30

#### RPH3-T5 status: `RPH3-T5_COMPLETE — READY_FOR_OPERATOR_REVIEW`

CMP-TOOLREG + CMP-TOOLGW + CMP-FILEOP + CMP-DIAG (Safe Mode, PH-3 scope) complete against their specs,
`01R` Dec B, `XSC-RPH3` (Class-1 registry ops, Class-3 file delete), `DEP-RPH3` §2/§3/§4A. **Not yet
operator-accepted; not `PROM-RPH3`. RPH3 performs no direct host execution (PH-5 owns OS enforcement).**

- **Delivered:** `migrations/security/0003_tools.sql` (tool domain: `tool_registry`, `tool_declarations`,
  `tool_quarantine`, `tool_registry_intents`; SHA-pinned
  `0050e74f80932fb58ea15d1f60f95661c7589d57dd623aad7691e26ea73a69b5`; `IF NOT EXISTS schema_migrations`);
  `src/factory/tools/{errors,models,store,writer,registry,gateway,__init__}.py`;
  `src/factory/fileops/{errors,models,service,__init__}.py`; `src/factory/safemode/__init__.py`; tests
  (tools unit/security/failure-path/integration, fileops, safemode); `scripts/verify_roadmap_ph3_t5.py`;
  `docs/verification/roadmap-ph3-t5-tools-evidence.md`. `SCHEMA-REGISTRY.md` updated (0003 present).
- **Behavior:** registry default-DENY (unregistered/quarantined uncallable), complete-declaration +
  provenance required, version pinning, repeated-failure quarantine (durable, no auto-release), Class-1
  audited register/quarantine/release + reconciliation; gateway single no-bypass path (default-deny +
  TOCTOU permission revalidation + resource/termination REQUEST CONTRACTS + limit-increase→approval +
  untrusted-output validation + **fail-closed without a PH-5 sandbox executor — no direct host exec**);
  file-op path canonicalization/containment (reused PathAuthority), **Decision-B delete with no path
  without a consumed approval (Class-3 INTENT+COMPLETION audit)**, atomic bounded writes, archive
  bomb/zip-slip caps; Safe Mode read-only inspect/export + approval+permission-gated audited repair with
  **no autonomous-write path** and out-of-scope refusal. Private per-domain sole-writer denies writes to
  approval/permission tables.
- **Tests (exact):** RPH3-T5 = **88 passed, 0 failed** (tools 57 [unit 38, security 6, failure-path 11,
  integration 2], fileops 21, safemode 10). Full repo = **721 passed, 1 skipped** (Windows-only; +88 vs
  633 at T2, no regression).
- **Coverage (exact):** tools **98.7%**, fileops **97.6%**, safemode **98%** branch (each ≥95%).
- **Static analysis (exact):** ruff over all T5 src + tests + verifier → **clean**; mypy --strict per
  package (tools/fileops/safemode + tests) → **clean**.
- **Verifier:** `scripts/verify_roadmap_ph3_t5.py` → **10/10 PASS**.
- **Boundaries held:** Lane A / Watchdog **not started**; no PH-5 enforcement gate (EG-PH5-*) claimed;
  PR #10 unmerged; `main` untouched; the accepted T4 audit foundation + T3 approval + T2 permission
  domains unmodified. **This completes the authorized T3 → T2 → T5 sequence; stopping.**

### RPH3 T3/T2/T5 Windows and Python 3.14 correction — 2026-07-29

Operator authorized a bounded correction from
`8fee3a7f8d8a13e6bb741cc3d52d596e9358b843` on
`claude/roadmap-ph3-security-spine-planning`. Correction implementation commit:
`928535961e9e1224d00a933b3be0cc899e954b96`.

#### Status: `RPH3-T3/T2/T5_CORRECTED — READY_FOR_OPERATOR_REVIEW`

- **Windows checkout portability:** `.gitattributes` now sets `*.sql text eol=lf`. No SQL text changed;
  all eight byte-exact SHA-256 pins remain exact. A fresh `core.autocrlf=true` checkout passed all 16
  portability/hash cases.
- **Python 3.14 compatibility:** eight frozen-dataclass public exceptions are now normal typed exception
  classes with constructor, attributes, `str`, `repr`, traceback, chaining, and context behavior verified.
- **Matrix:** CPython 3.12.13, 3.13.14, and 3.14.6 each passed focused tests (34), T3 (9/9), T2 (10/10),
  T5 (10/10), and the full repository (**755 passed, 1 explicitly classified Windows skip**).
- **Migration behaviors:** 26 focused cases passed for new DB, existing/idempotent startup, failure
  rollback, and tampered-migration rejection.
- **Static/coverage:** repository Ruff clean; strict mypy clean for all affected packages and new tests;
  all T3/T2/T5 coverage thresholds remain above 95%.
- **Evidence:** `docs/verification/roadmap-ph3-windows-python314-correction-evidence.md`.
- **Boundaries held:** `main` unchanged; PR #10 draft/unmerged/unmodified; Watchdog and Lane A not started;
  no `PROM-RPH3`, phase promotion, merge, or new milestone claim.

### Operator acceptance of corrected RPH3 T3/T2/T5 gates — 2026-07-29

This section supersedes the correction section's `READY_FOR_OPERATOR_REVIEW` status. The operator reviewed
the pushed correction/evidence state (`928535961e9e1224d00a933b3be0cc899e954b96`,
`61fcc8cf68080ab3796de906d3a279ef73c1c2bf`) and issued the following authoritative gate verdicts:

- `RPH3-T3 := ACCEPTED`
- `RPH3-T2 := ACCEPTED`
- `RPH3-T5 := ACCEPTED`
- `PROM-RPH3 := NOT_AUTHORIZED`
- `ROADMAP_PH3 := INCOMPLETE`

The acceptance covers the Windows/Python correction evidence: CPython 3.12/3.13/3.14 matrix, 755 passed
with one explicit Windows skip, all T3/T2/T5 verifiers, exact migration hashes, fresh
`core.autocrlf=true` checkout, Ruff, strict mypy, and retained coverage thresholds.

**Remaining required work:** Watchdog/WIR, Lane A, final integrated RPH3 verification, final promotion
review, and a separately authorized merge decision.

**Non-blocking promotion debt:** SQLite `ResourceWarning` messages observed during some Python 3.13/3.14
approval coverage runs. They do not reopen T3/T2/T5 acceptance, but must be cleaned up before final
RPH3 promotion.

### RPH3-T1 CMP-WATCH Lane A and internal WIR - 2026-07-30

#### Status: `RPH3-T1_COMPLETE - READY_FOR_CROSS_LANE_INTEGRATION`

- **Delivered:** `src/factory/watchdog/**`; next ordered migration
  `migrations/security/0004_watchdog.sql` (internal intervention journal, SHA-256
  `21ad8fa85055e1e55b703a55865a442b4e1af907c39baf668f7fcf34a4488b80`);
  39 unit/store/security/failure/integration tests; dedicated 8-check T1 verifier; evidence,
  requirement matrix, and failure-path matrix.
- **Behavior:** read-only process-side observation; monotonic authenticated heartbeat/stall
  detection; staged thresholds and hysteresis; deterministic failures; bounded recovery;
  fail-closed Watchdog-loss policy; exact seven-command internal WIR; expected-state, idempotency,
  bounded-target, authentication, and authority gating; Class-2 task transition and Class-3 restart
  audit ordering; crash reconciliation; private WIR journal writer/read-only consumer partition.
- **Windows matrix:** CPython 3.12.13, 3.13.14, and 3.14.6 each passed the dedicated verifier
  (**8/8**) and full repository (**794 passed, 1 classified Windows skip**).
- **Coverage/static:** focused Watchdog = **39 passed**, **95.92%** branch-aware coverage; Ruff
  clean; strict mypy clean.
- **Migration integrity:** prior security SQL files unchanged with exact pins
  `099ae959...`, `a65d227d...`, `0050e74f...`; `0004_watchdog.sql` tested on fresh/existing DB,
  idempotent startup, malformed input, and tampering.
- **Warnings/debt:** no warning emitted by the recorded M1 runs. Previously tracked SQLite
  `ResourceWarning` debt remains assigned to M3.
- **Boundaries held:** Lane A remains CMP-WATCH; WIR remains internal; Lane B remains accepted
  T2/T3/T4/T5; restore/snapshot and non-task quarantine remain inert; no PH-4/PH-5 execution
  subsystem, main/PR 10 modification, merge, or `PROM-RPH3`.
- **Next authorized milestone:** M2 cross-lane integration.

### RPH3 M2 cross-lane integration - 2026-07-30

#### Status: `RPH3_CROSS_LANE_INTEGRATION_COMPLETE - READY_FOR_INTEGRATED_VERIFICATION`

- **Baseline:** committed/pushed/clean-tree-verified M1 SHA
  `0a1479b53e5de200a7c46a5022aac158d8241501`; accepted T2/T3/T4/T5 unchanged.
- **Delivered:** `factory.watchdog.integration.RPH3CrossLaneBridge` (inside CMP-WATCH), typed
  Lane B signals/results, 15 unit/security/failure/concurrency/end-to-end tests, dedicated 7-check
  verifier, evidence report, requirement matrix, and failure-path matrix.
- **Behavior:** real public Permission/Approval/Audit/ToolGateway/FileOp/Safe Mode result wiring;
  explicit deny/card/expiry/replay propagation; audit-break containment; dependency-loss pause;
  Safe Mode read-only escalation; durable WIR replay; conflict/stale/unavailable/missing-target
  fail-closed outcomes; no tool/file/store/host bypass.
- **Exact gates:** focused **15 passed**, integration module **100.00% branch**; cross-lane verifier
  **7/7**; T1 **8/8**; T2 **10/10**; T3 **9/9**; T4 **9/9**; T5 **10/10**; full repository
  **809 passed, 1 classified Windows skip**; Ruff-all and strict mypy clean.
- **Bounded verifier correction:** T1 coverage now enumerates its original T1 modules while the new
  M2 module is independently held to 100% by the M2 verifier. No threshold or test was weakened.
- **Boundaries held:** Lane A=CMP-WATCH; WIR internal; Lane B=T2/T3/T4/T5; no new execution/intake/
  continuation component; no direct host execution; no main/PR 10/PH-4/PH-5/merge/`PROM-RPH3`.
- **Tracked debt:** the T3 verifier reproduced two SQLite `ResourceWarning` instances from unclosed
  one-shot connections in `tests/approval/failure_paths/test_writer_faults.py`; root-cause cleanup
  remains assigned to M3.
- **Next authorized milestone:** M3 integrated RPH3 verification.

### RPH3 M3 integrated security-spine verification - 2026-07-30

#### Status: `RPH3_IMPLEMENTATION_COMPLETE — READY_FOR_OPERATOR_PROMOTION_REVIEW`

- **Baseline:** committed/pushed/clean-tree M1 `0a1479b53e5de200a7c46a5022aac158d8241501`
  and M2 `c95de2a0a9e400135184a67ec27376b43263c88f`.
- **Integrated gate:** dedicated verifier **10/10**; complete RPH3 focused graph **309 passed** under
  warning-as-error on CPython 3.12.13, 3.13.14, and 3.14.6.
- **Component gates per version:** T1 **8/8**, T2 **10/10**, T3 **9/9**, T4 **9/9**, T5 **10/10**,
  cross-lane **7/7**. Full repository **811 passed, 1 classified Windows skip** per version.
- **Coverage:** Watchdog **95.86%**, cross-lane **100.00%**, permission **99.80%**, approval
  **99.80%**, audit **99.03%**, tools **98.55%**, fileops **97.02%**, Safe Mode **98.91%**.
  Every unchanged threshold remains at or above 95%.
- **Static:** repository Ruff PASS; every component verifier and the integrated verifier strict-mypy
  PASS on all required Python versions.
- **Warning debt resolved:** removed two redundant leaked test-fixture SQLite connections; retained
  the explicitly closed connection that constructs the same broken-store condition. No warning
  suppression and no accepted behavior change. Focused and full suites pass with resource warnings
  promoted to errors.
- **Migrations/checkout:** all eight RPH3-related migration SHA-256 values exact; no SQL diff; fresh
  `core.autocrlf=true` checkout produced LF-only migration bytes and exact hashes. The portability
  regression now includes security `0004_watchdog.sql`.
- **Skip:** one Windows symlink-creation case remains explicitly `NOT_TESTABLE`; alternate path
  escape coverage remains active.
- **Boundaries:** Lane A is CMP-WATCH, WIR is internal, Lane B is T2/T3/T4/T5. No PH-4/PH-5,
  direct host execution, new execution/continuation component, main/PR #10 change, merge, or
  `PROM-RPH3`.
- **Next:** operator promotion review only. `PROM_RPH3 := NOT_AUTHORIZED`.

### Operator roadmap PH-3 promotion authorization - 2026-07-30

This section supersedes M3's `READY_FOR_OPERATOR_PROMOTION_REVIEW` status. The operator reviewed the
committed, pushed, clean-tree-verified RPH3 implementation/evidence state at
`7a01b4bc4a35d9346bfb0a34e53113bf67a56c62` and explicitly responded `AUTHORIZED`.

- `RPH3_IMPLEMENTATION := ACCEPTED`
- `PROM-RPH3 := PASS`
- `ROADMAP_PH3 := PROMOTED`
- `MERGE := NOT_AUTHORIZED`
- `STAGE_2_CUTOVER := NOT_AUTHORIZED`
- `PH4 := NOT_STARTED`
- `PH5 := NOT_STARTED`

The authorization accepts the recorded Windows CPython 3.12/3.13/3.14 matrix, integrated and component
verifiers, 811-passed/1-classified-skip full repository runs, retained coverage thresholds, exact migration
hashes, fresh `core.autocrlf=true` checkout, strict mypy, Ruff, and resolved SQLite warning debt. Promotion
changes phase-gate status only: it does not merge or modify `main`/PR #10 and does not begin another phase.

**Next allowed action:** await a separate operator decision for integration/merge or the next roadmap phase.

### PH-4 preinstallation core - 2026-07-30

Operator corrected the working baseline (the initial `main`-based branch had no RPH3 foundation) and
authorized continuing the PH-4/PH-5/PH-6 preinstallation directive from the promoted RPH3 base
`3c979d72abee28776fc361bceb1b1edd55cde0ae`. Controlled branch `claude/ph4-ph5-ph6-preinstall` forked
from that base (merge-base verified; `main` and PR #10 unchanged). RPH3 baseline independently
re-verified on this environment: integrated verifier 10/10, full repo 811 passed / 1 skipped.

#### Status: `PH4_PREINSTALLATION_CORE_COMPLETE — LIVE_RUNTIME_PENDING`

- **Owner paths (section-4 plan):** `src/factory/models/ollama_adapter` (Task 4.1 fake), `src/factory/
  workers/aider_adapter` (Task 4.2 fake), `src/factory/routing` (Task 4.3 router/roster/fingerprint/
  records/health + adapter interface), `src/factory/scheduler` (Task 4.4 scheduler + quota). An
  operator mid-run ownership check moved scheduler/quota/adapters out of `routing/` to these paths; no
  abandoned duplicates remain.
- **Delivered (deterministic fakes, offline):** `ProviderAdapter` interface; `FakeOllamaAdapter` +
  `FakeAiderWorker`; deterministic `ModelRouter` (visible routing + reason, operator override within
  limits, privacy-before-hosted, no silent substitution, disclosed + reverified fallback,
  restart reconciliation); `ApprovedRoster` (CTR-ROUTE-REGISTRY, GLM-4.7 excluded); complete model
  fingerprints (CTR-MODEL-FINGERPRINT); append-only `ExecutionLedger` (CTR-MODEL-EXEC-RECORD);
  `ResourceScheduler` (single-active GPU-heavy, VRAM/RAM/CPU/storage ceilings, cooldown, pressure
  order, reconcile, REDUCED_MONITORING); `QuotaLedger`; `01J §3.4` health-check triggers.
- **Gates (exact):** `scripts/verify_ph4_preinstall.py` **10/10**; `tests/routing` **93 passed**
  (unit 78, security 5, failure-path 7, integration 3); branch coverage **100.00%** across the four
  PH-4 packages (≥95%); Ruff clean; mypy `--strict` clean (31 files); full repository **904 passed,
  1 skipped** (Windows-only; +93 vs the 811 RPH3 baseline, no regression); RPH3 integrated verifier
  still **10/10**; Worker Execution Substrate verifier still **18/18**.
- **Evidence:** `docs/verification/ph4-preinstall-evidence.md`, `ph4-requirement-to-test-matrix.md`,
  `ph4-failure-path-matrix.md`, `ph4-pending-live-gate-register.md`.
- **Boundaries held:** no installation, no live Ollama/Aider execution, no network, no secrets, no
  migrations; `main` (`9bce1ca`) unchanged; PR #10 (`7b1922e`) draft/unmodified; RPH3 spine and the
  substrate unmodified; no merge, no promotion. `PROM-PH4 := NOT_AUTHORIZED`.
- **Next:** PH-5 preinstallation isolation core (Git/worktree/sandbox/secret/network brokers with
  deterministic fake backends), then PH-6 simulated workstream core.

### PH-5 preinstallation core - 2026-07-30

Continued the operator directive from the PH-4 commit `9dd851b` on `claude/ph4-ph5-ph6-preinstall`.
Implemented the PH-5 isolation core: real Git on temporary repositories + deterministic fake
sandbox/secret/network backends + pure-logic cache/staging.

#### Status: `PH5_PREINSTALLATION_CORE_COMPLETE — LIVE_SANDBOX_PENDING`

- **Owner paths (section-5 plan):** `src/factory/git` (5.1 branch/worktree/checkpoint), `src/factory/
  sandbox` (5.2 backend interface + fake WSL/Docker backend + isolation policy), `src/factory/secret`
  + `src/factory/network` (5.3 brokers + fake backends), `src/factory/cache` + `src/factory/staging`
  (5.4 cache isolation + quarantined staging).
- **Delivered:** `GitManager` (approved-baseline task branches, worktree lifecycle, owned-path
  checkpoints, exact change tracking, protected-ref + force-push denial, unexplained-change block,
  CTR-COMMIT-TRAILER validation, CTR-BASELINE-MANIFEST); sandbox `SandboxBackend` + `FakeWslDocker
  Backend` + policy (non-root, prohibited privileges, no writable host-project mount, Decision-C
  Windows-native denial, hard limits, runtime-unavailable results, restart reconcile, boundary-failure
  destroy + clearance); `SecretBroker` + `FakeSecretBackend` (scoped TTL leases, redaction,
  revoke-and-forget, pre-export scan, CTR-SECRET-REF); `NetworkBroker` + `FakeNetworkBackend`
  (default-deny, allowlists, expiry, no inbound, redirect containment, destination validation,
  transfer limits, CTR-NETWORK-APPROVAL); `ContentAddressedCache` (immutable, project/sandbox scoped,
  contamination-preventing, credential-free, invalidation); `QuarantinedStaging` (single exit,
  inventory+hash+provenance, path-escape/secret/executable/archive-bomb/scope inspection, promotion
  denied without clean gate + authorization, complete process-tree termination).
- **Gates (exact):** `scripts/verify_ph5_preinstall.py` **10/10**; PH-5 focused tests **84 passed**
  (git 23, sandbox 19, secret 11, network 11, cache 9, staging 11); branch coverage **100.00%** across
  the six PH-5 packages (≥95%); Ruff clean; mypy `--strict` clean (42 files); full repository
  **988 passed, 1 skipped** (Windows-only; +84 vs the 904 PH-4 state, no regression); PH-4 verifier
  still 10/10; RPH-3 integrated verifier still 10/10; Worker Execution Substrate verifier still 18/18.
- **Evidence:** `docs/verification/ph5-preinstall-evidence.md`, `ph5-requirement-to-test-matrix.md`,
  `ph5-failure-path-matrix.md`, `ph5-pending-live-gate-register.md`.
- **Boundaries held:** no installation, no live WSL2/Docker/network/secrets (Git uses real *local
  temporary* repos only); `main` (`9bce1ca`) unchanged; PR #10 (`7b1922e`) draft/unmodified; RPH-3
  spine, substrate, and PH-4 routing unmodified; no merge, no promotion. `PROM-PH5 := NOT_AUTHORIZED`.
- **Next:** PH-6 simulated workstream core.

### PH-6 simulated core - 2026-07-30

Continued the directive from the PH-5 commit `26f9657` on `claude/ph4-ph5-ph6-preinstall`. Implemented
the PH-6 simulated workstream core, demonstrated end-to-end against the PH-4/PH-5 deterministic fakes.

#### Status: `PH6_SIMULATED_CORE_COMPLETE — LIVE_INTEGRATION_PENDING`

- **Owner paths (section-6 plan):** `src/factory/workstream` (6.1 CTR-WORKSTREAM + admission +
  ownership), `src/factory/workstream/lane` (6.2 lane lifecycle SM + isolated checkouts),
  `src/factory/workstream/conflict` (6.3 conflict-beyond-files + immutable baseline),
  `src/factory/workstream/scheduler` (6.4 priority/interruption + 3-failure quarantine),
  `src/factory/integration` (6.5 coordinator + simulated IP-3).
- **Delivered:** `AdmissionController` (≤3 cap + independence gate, not path-disjointness alone);
  `OwnershipRegistry` (single-writer + shared-contract leases); 12-state `LaneMachine` with
  legal-transition + task-consistency enforcement + audit; `IsolatedCheckoutAssigner`;
  `ConflictDetector` (10 dimensions: file/module/symbol/schema/api/migration/config/dependency/
  generated/logical); `BaselineTracker` (immutable baseline + drift detection); `WorkstreamScheduler`
  (checkpointed interruption, resume order, starvation); `FailureCounter` (normalized signature,
  3-failure quarantine, transient exclusion); `IntegrationCoordinator` (compare/validate/combine/
  assign remediation, `COORDINATOR_EDITS_SOURCE=False` — never edits source); `run_simulated_ip3`.
- **Gates (exact):** `scripts/verify_ph6_preinstall.py` **11/11** (incl. the simulated
  three-workstream gate + coordinator-never-edits-source); PH-6 focused tests **35 passed**
  (workstream 29, integration 6); branch coverage **100.00%** across the PH-6 packages (≥95%); Ruff
  clean; mypy `--strict` clean (27 files); full repository **1023 passed, 1 skipped** (Windows-only;
  +35 vs the 988 PH-5 state, no regression); PH-5 verifier still 10/10; PH-4 verifier still 10/10;
  RPH-3 integrated verifier still 10/10; Worker Execution Substrate verifier still 18/18.
- **Evidence:** `docs/verification/ph6-preinstall-evidence.md`, `ph6-requirement-to-test-matrix.md`,
  `ph6-failure-path-matrix.md`, `ph6-simulated-ip3-report.md`, `ph6-pending-live-gate-register.md`.
- **Boundaries held:** no installation, no live runtime (sandbox/router assignment simulated via the
  PH-4/PH-5 fakes); the integration coordinator never edits source (structural); `main` (`9bce1ca`)
  unchanged; PR #10 (`7b1922e`) draft/unmodified; RPH-3 spine, substrate, PH-4 routing, and PH-5
  isolation unmodified; no merge, no promotion. `PROM-PH6 := NOT_AUTHORIZED`.
- **Next:** await operator decision on installation + live validation (PH-4/PH-5/PH-6 live gates) or
  integration/merge; PREINSTALLATION for PH-4/PH-5/PH-6 is COMPLETE.

### Phase 3B worker verify/promote implementation - 2026-08-02

#### Status: `IMPLEMENTED CANDIDATE — VERIFICATION BLOCKED`

- **Current Linux-tested implementation commit:** `475c528` after milestone commits `0c65b21`,
  `3ebdedd`, `41056d6`, `9eca3db`, `f91bace`, `6f1392e`, validation repair `c25bb4c`, and launcher
  portability repair `475c528`.
- **Delivered:** independent verification; append-only evidence/manifests; explicit approval binding;
  serialized promotion and rollback; restart reconciliation; lifecycle API; Phase 3B dashboard.
- **Current PASS evidence:** Linux collection 1733; restricted suite 1648 passed with 85 explicitly
  classified environment skips; loopback 83/83 outside the restricted socket sandbox; Section 1
  325 tests at 96.86% branch coverage; Ruff format/lint; mypy 305 files; lockfile; frontend
  typecheck/lint/43 tests/build; Section 2 18/18; RPH3 10/10; PH-4 10/10; focused lifecycle and
  failure-path tests.
- **Historical evidence only:** native Windows collection/suite 1730, two junction cases, and
  Windows Ruff/mypy/preinstall results belong to `48e0dd8`, not the current PR head.
- **Environment blocker:** rerun focused native-Windows launcher and junction gates at the exact
  final PR head.
- **Review blockers:** independent review reports untrusted verifier execution without a process
  sandbox, unauthenticated approval authority, incomplete quick-start lifecycle wiring, a
  path-revalidation TOCTOU window, incomplete promotion restart rollback, and launcher cleanup
  weaknesses. These must be resolved and independently re-reviewed.
- **Boundary:** draft PR #18 was pushed; no merge, deploy, release, or protected-ref promotion was
  performed.
