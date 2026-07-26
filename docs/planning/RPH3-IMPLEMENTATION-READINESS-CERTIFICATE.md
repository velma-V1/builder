# Roadmap PH-3 — Implementation-Readiness Certificate (CERT-RPH3)

**Document ID:** CERT-RPH3 · **Repository path:** `docs/planning/RPH3-IMPLEMENTATION-READINESS-CERTIFICATE.md`
**Status:** Derived certification (RPH3 planning) · **Established:** 2026-07-26. **Governing:** the full RPH3
planning corpus + `01M`/`01K`/`01R`/`docs/10`. **Namespace:** RPH3. **Current verdict:**
`RPH3_PLANNING_REPAIR_REQUIRED` (repair in progress) → superseded by a corrected certificate at §8 once the
final audit passes. **This certifies planning readiness only — NOT implementation authorization, NOT a merge
authorization, and NOT roadmap PH-3 completion.**

## 0. Supersession & correction history

- **v1 — commit `1d3b860` (SUPERSEDED, INVALID):** issued verdict `RPH3_CERTIFIED_WITH_NONBLOCKING_GAPS`. This
  certified an **invalid planning state**: its 12 audits (A1–A12) failed to detect the defect classes below.
  The verdict is **withdrawn**; the historical record is retained here per the never-delete rule (not edited
  in place).
- **Defects the v1 audits missed:** (D1) `01M`/`01K` acceptance criteria conflated with the separate approved-
  decision lists; ambiguous `01M #NN`/`01K #NN` references. (D2) no crash-consistent protocol across the
  runtime-state DB / security-spine store / audit store. (D3) the seven Watchdog interventions had no defined
  receiver; the frozen PH-2 transition writer was implied to execute service-restart/quarantine/restore/
  snapshot commands it does not support. (D4) stale migration/dependency contradictions (`migrations/runtime/
  0004_*`, audit-append-via-CMP-ORCH, a `10A` CMP-LEASE-consumption claim). (D5) PH-5 enforcement (process-
  tree termination, orphan prevention, sandbox quarantine/recording/evidence) falsely certifiable by
  `PROM-RPH3`. (D6) shared security-spine store had no enforceable per-domain ownership.
- **v2 — corrected certification (§8):** issued only after every repair below lands and the full final audit
  (§3, rebuilt) passes. Until then the verdict is `RPH3_PLANNING_REPAIR_REQUIRED`.

> The §2–§7 body below is the v1 content retained for provenance; the §3 audits and §7 verdict were the
> **defective** ones. The authoritative corrected audits, evidence, and verdict are in **§8** (added after
> repairs). Where §2–§7 and §8 disagree, **§8 governs.**

## 1. Purpose

The single entry point for a future implementer of roadmap PH-3. It inventories the planning corpus, records
the readiness audits, states the implementation-start package (branch, task order, first task), and fixes the
promotion gate. It carries no new technical authority — it points at the governing sources and the RPH3 plans.

## 2. Planning-corpus inventory (all authored on `claude/roadmap-ph3-security-spine-planning`)

| Artifact | Path | Pass |
|---|---|---|
| PLAN-S3 (executable task plan, RPH3-T1…T5, XIB-01..04) | `docs/plans/section-3-orchestrator-watchdog-and-permissions.md` | 5 |
| 9 component specs + integration review | `docs/specifications/components/{watchdog,permission,approval,audit-writer,audit-validator,tool-registry,tool-gateway,safe-mode,file-op-service}-spec.md`, `RPH3-INTEGRATION.md` | 4 |
| COMPONENT-MAP #40 CMP-FILEOP | `docs/specifications/components/00-COMPONENT-MAP.md` | 4 |
| VEP-RPH3 (verification/evidence/promotion) | `docs/planning/RPH3-VERIFICATION-EVIDENCE-PROMOTION.md` | 6 |
| FRR-RPH3 (failure/recovery/rollback) | `docs/planning/RPH3-FAILURE-RECOVERY-ROLLBACK.md` | 7 |
| RESOURCE-ALLOCATION-PLAN (G-02) | `docs/planning/RESOURCE-ALLOCATION-PLAN.md` | 7 |
| SEC-RPH3 (security/trust-boundaries) | `docs/planning/RPH3-SECURITY-TRUST-BOUNDARIES.md` | 8 |
| DEP-RPH3 (deployment/migration; ODI-RPH3-01 resolved) | `docs/planning/RPH3-DEPLOYMENT-MIGRATION.md` | 9 |
| Templates: VERIFICATION-REPORT (G-06), PHASE-EXIT-CHECKLIST (G-05) | `docs/templates/{VERIFICATION-REPORT,checklist/PHASE-EXIT-CHECKLIST}.template.md` | 6, 10 |
| Ledgers: PAL §9, CL §10, execution map 10A §3A | `docs/planning/00-*`, `docs/10A-…` | 2–10 |
| CERT-RPH3 (this) | `docs/planning/RPH3-IMPLEMENTATION-READINESS-CERTIFICATE.md` | 10 |

## 3. Readiness audits (this pass)

| # | Audit | Result |
|---|---|---|
| A1 | Every RPH3 component appears in exactly one task (9 comps → T1/T4/T3/T2/T5) | PASS (PLAN-S3 §8) |
| A2 | Every RPH3-scoped `01M`(32)/`01K`(25) criterion mapped to a task, or PH-2-satisfied/PH-5-interface/PH-7-deferred | PASS (PLAN-S3 §5, VEP-RPH3 §2) |
| A3 | Decisions A & B explicitly mapped to tasks + tests | PASS (VR-RPH3-17/18; SEC-RPH3-05/06) |
| A4 | VM-2 security-spine complete integration path defined → `PROM-RPH3` | PASS (VEP-RPH3 §5) |
| A5 | No PH-4/PH-5 responsibility absorbed (spawner/sandbox/secret/network/router excluded) | PASS (PLAN-S3 RPH3-T5 exclusions, §5) |
| A6 | Four PR #10 substrate blockers recorded as **external** prerequisites only (XIB-01..04) | PASS (PLAN-S3 §7) |
| A7 | Builds only on frozen PH-2; substrate not a dependency; PH-2 not modified | PASS (PLAN-S3 §1, DEP-RPH3 §2) |
| A8 | Single-owner authority; no duplicate with WES/PH-2 rows; acyclic | PASS (PAL §9.5, RPH3-INTEGRATION §3/§4) |
| A9 | RPH3 namespace disjoint from substrate (`T3.x`/`SEC-PH3-*`/`PROM-PH3`/`WES-*`/`PH3-*`) | PASS (PAL §9.1; guard on every commit) |
| A10 | Schema-freeze respected (new PH-3 stores, SHA-pinned; no PH-2 migration altered) | PASS (DEP-RPH3 §3, SCHEMA-REGISTRY) |
| A11 | Roadmap not amended; CMP-FILEOP added via change-control only | PASS (COMPONENT-MAP note; WES-CLASS unaffected) |
| A12 | All registered gaps for RPH3 resolved or scheduled (G-02/G-06 resolved; G-05 this pass) | PASS (PAL §9.4) |

## 4. Implementation-start package

- **Branch:** operator assigns the PH-3 **product** branch at the entry gate (planning branch is
  `claude/roadmap-ph3-security-spine-planning`; base = PH-2 tip `7b1922e`).
- **First action:** Lane B **RPH3-T4** (CMP-AUDITW → CMP-AUDITV) — the audit foundation everything else
  records to; then **T3** (Approval) → **T2** (Permission) → **T5** (Tools/FileOp/Gateway/SafeMode). Lane A
  **T1** (Watchdog) runs in parallel, soft-serialized behind T4 for intervention audit.
- **TDD:** per PLAN-S3 per-task procedures; ≥95% branch coverage; `scripts/verify_roadmap_ph3.py` emits the
  ETM manifest; evidence report uses `VERIFICATION-REPORT.template.md`.
- **Stores:** `migrations/security/0001_security_spine.sql` + `migrations/audit/0001_audit_chain.sql`
  (separate PH-3 stores; runtime-state DB untouched, R1).

## 5. Promotion gate — `PROM-RPH3` (restated)

`01M`(32)+`01K`(25) RPH3-scoped PASS · VM-2 path PASS · Dec A/B proven · audit append-only + break detection ·
Safe-Mode no-autonomous-write · ≥95% coverage · zero critical/high defect · complete ETM · **operator PH-3
exit approval + authorization to begin `01B` Stage-2 cutover**. (VEP-RPH3 §6.)

## 6. Non-blocking items carried into implementation

- **External (not RPH3):** PR #10 substrate blockers XIB-01..04 (owned by a dedicated PR #10 correction /
  PH-5) — prerequisites for any PR #10 *merge*, independent of `PROM-RPH3`.
- **Forward-bound:** CMP-WATCH `ACTIVATE_VERIFIED_SNAPSHOT` inert until CMP-SNAP (PH-7); `01K`
  `01K-AC-07/08/23/24` credential/network/sandbox enforcement is PH-5 (RPH3 defines the interfaces only).
- **Regression register:** none seeded at plan time; implementation seeds REGR-* per repair.

## 7. Certificate

The roadmap PH-3 (Watchdog security spine) **implementation-planning package is complete and internally
consistent**, builds only on frozen PH-2, keeps identifiers disjoint from the Worker Execution Substrate,
absorbs no PH-4/PH-5 ownership, and records the four PR #10 substrate blockers as external prerequisites.

**Verdict: `RPH3_CERTIFIED_WITH_NONBLOCKING_GAPS`.**

**Required operator action to proceed:** explicit authorization to begin **roadmap PH-3 product
implementation** (first task RPH3-T4). Until then: no implementation, no merge, `main` and PR #10 untouched,
roadmap not amended.
