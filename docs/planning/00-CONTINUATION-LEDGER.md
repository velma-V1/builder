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
