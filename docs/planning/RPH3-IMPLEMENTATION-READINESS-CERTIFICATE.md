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
- **Forward-bound:** CMP-WATCH `ACTIVATE_VERIFIED_SNAPSHOT` inert until CMP-SNAP (PH-7);
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

---

## 8. Corrected certification (v2 — authoritative)

Issued after the repair commits R1–R6 and the repository-wide final audit. **Where §2–§7 (v1) and this
section disagree, §8 governs.** Repair provenance: the invalid v1 verdict (commit `1d3b860`) is superseded
(see §0); this v2 supersedes it in place under the never-delete rule.

### 8.1 Repair summary (defects → corrections)

| Defect | Correction | Artifact |
|---|---|---|
| D1 `01M`/`01K` AC/DEC conflation + ambiguous `#NN` | Authoritative `-AC`/`-DEC` mapping; corpus-wide identifier rewrite | TRACE-RPH3; VEP §2; PLAN-S3 §5; all specs |
| D2 no crash-consistent cross-store protocol | Write-ahead-intent + audit-as-commit-point protocol; every crash window; fail-closed | XSC-RPH3 (VR-RPH3-19) |
| D3 undefined Watchdog receiver; false `apply_transition` claim | Receiver ownership, schemas, allowlist, INERT commands, no writable connection | WIR-RPH3; watchdog-spec; PLAN-S3 T1 |
| D4 stale migration/dependency contradictions | Separate PH-3 stores; audit not via CMP-ORCH; CMP-LEASE not consumed | R5 across RPH3-INTEGRATION, audit-writer, PLAN-S3, PAL, 10A |
| D5 PH-5 enforcement falsely certifiable | `EG-PH5-01..10` gates excluded from `PROM-RPH3`; RPH3 keeps request contract + fail-closed-no-executor | TRACE-RPH3 §3; VEP §2a/§6 |
| D6 unenforceable shared-store ownership | Private per-domain writers, SQLite authorizer, isolation tests | DEP-RPH3 §4A |

### 8.2 Final-audit result (repository-wide sweeps)

23 automated checks run (exact-reference, identifier-completeness, decision-vs-acceptance, broken-link/file
existence, schema-path, semantic-consistency, git-state). **22 PASS; 1 audit-filter false positive** (the
namespace check flagged the two *"no `SEC-PH3-*`/`PROM-PH3` reuse"* declaration sentences themselves — manual
check confirms the corpus uses `PROM-RPH3` (9×) and `SEC-RPH3-*` (24×); **zero** actual substrate-identifier
reuse). Implementation files (`src/`, `tests/`, `scripts/`) **untouched** across R1–R6 (docs-only).

Specifically proven by the final audit:
- every `01M-AC-01..32` and `01K-AC-01..25` mapped exactly and semantically in TRACE-RPH3;
- no decision-list number represented as an acceptance criterion (output validation → `01K-DEC-25`, not `01K-AC-25`);
- no nonexistent criterion cited (all AC ids within 32 / 25);
- every store write + audit interaction has a defined crash-consistent protocol (XSC-RPH3), audit-before-success;
- every Watchdog intervention has a real receiver + authority path (WIR-RPH3); no intervention is falsely
  routed through the PH-2 transition writer; unsupported commands are INERT (PH-5/PH-7);
- no PH-5 enforcement is certified by `PROM-RPH3` (`EG-PH5-*` excluded);
- no runtime `0004_*` contradiction; migration layout consistent (`migrations/security/0001`, `migrations/audit/0001`);
- no RPH3 document disagrees about CMP-LEASE consumption (not an RPH3 dependency);
- shared-store ownership is structurally enforceable (DEP-RPH3 §4A);
- roadmap unamended; PH-2 frozen; PR #10 untouched; implementation files untouched; branch clean + synced.

### 8.3 Corrected audits (expanded to catch the v1 defect classes)

| # | Audit | Result |
|---|---|---|
| C1 | Every component in exactly one task (9 comps → T1/T4/T3/T2/T5) | PASS |
| C2 | `01M-AC`/`01K-AC` mapped exactly + semantically (TRACE-RPH3); AC≠DEC | PASS |
| C3 | No decision number cited as an acceptance criterion | PASS |
| C4 | No nonexistent criterion cited | PASS |
| C5 | Cross-store crash-consistency protocol defined; audit-before-success | PASS (XSC-RPH3) |
| C6 | Every Watchdog intervention has a real receiver + authority path | PASS (WIR-RPH3) |
| C7 | No PH-5 enforcement certifiable by `PROM-RPH3` | PASS (EG-PH5 excluded) |
| C8 | No runtime `0004_*` / migration contradiction | PASS |
| C9 | No CMP-LEASE-consumption disagreement | PASS |
| C10 | Shared-store ownership enforceable | PASS (DEP-RPH3 §4A) |
| C11 | Dec A/B mapped; VM-2 path complete incl. cross-store invariant | PASS |
| C12 | RPH3 namespace disjoint from substrate (`PROM-RPH3`/`SEC-RPH3-*`) | PASS |
| C13 | Roadmap unamended; PH-2 frozen; PR #10 + impl files untouched; branch clean+synced | PASS |

### 8.4 Corrected verdict

**`RPH3_CERTIFIED_WITH_NONBLOCKING_GAPS` (v2).** The roadmap PH-3 implementation-planning package is complete,
internally consistent, and free of the D1–D6 defect classes. Non-blocking items unchanged (§6): PR #10
substrate blockers XIB-01..04 (external); PH-7-deferred snapshot criteria; PH-5 enforcement gates
`EG-PH5-01..10` (interface-defined here, enforced/certified in PH-5). **This certifies planning readiness only
— NOT implementation authorization, NOT merge authorization, NOT PH-3 completion.** Required operator action
to proceed remains explicit authorization to begin roadmap PH-3 implementation (first task RPH3-T4).
