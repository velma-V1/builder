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

**Next allowed action**

Await explicit `CONTINUE` to begin **RPH3 Pass 3** (roadmap-execution environment map — the `docs/10A`
PH-3 row + order-validation). Until then: no implementation, no merge, `main` and PR #10 untouched, roadmap
not amended.
