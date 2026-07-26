# Planning Authority Ledger

**Document ID:** PAL-000
**Repository path:** `docs/planning/00-PLANNING-AUTHORITY-LEDGER.md`
**Status:** Active — master catalog of the implementation-planning system
**Authority level:** Derived governing index (ranks with `docs/00-DOCUMENTATION-INDEX.md`; it never overrides a source it catalogs)
**Owner:** Planning system (maintained at every planning pass)
**Established:** 2026-07-24 (PH-2 planning, Pass 2)
**Last realigned:** 2026-07-24

## 1. Purpose

This ledger is the single authoritative catalog of every planning document in the Factory
implementation-planning system. It exists to enforce four invariants across the planning corpus:

- **One authoritative purpose per document** — no two documents own the same decision.
- **No duplicate authority / no overlapping ownership** — each concrete artifact below has exactly one owner row.
- **No circular authority dependencies** — the dependency column is acyclic (verified in §5).
- **No undocumented relationships** — every producer/consumer edge is listed.

It does **not** restate the content of the documents it catalogs, and it holds no authority over
`PROJECT_DEFINITION.md`, `docs/00-DOCUMENTATION-INDEX.md`, the `docs/01*` governing corpus, or `docs/01R`.
Where this ledger and a governing document disagree about a technical fact, the governing document wins and
this ledger is corrected.

## 2. Attribute schema (applies to every catalogued document)

Every planning document is defined by these attributes. For concrete documents the values live in the
registry (§4) and, in full, in each document's own header; this section fixes the vocabulary so headers stay
consistent.

| Attribute | Meaning |
|---|---|
| Document ID | Stable identifier, unique in this ledger |
| Repository Path | Canonical location (one path; no second copy) |
| Title | Human-readable name |
| Purpose | The single authoritative purpose |
| Authority Level | Governing / Derived-index / Plan / Registry / Template / Report |
| Owner | The role or pass responsible for its content |
| Inputs | Documents/data it consumes |
| Outputs | What it authoritatively produces |
| Required Sections | Sections the document must contain |
| Dependencies | Documents it depends on (must be acyclic) |
| Dependent Documents | Documents that depend on it |
| Required Reviews | Review gates before it is trusted |
| Required Approvals | Operator approvals it is subject to |
| Version Strategy | How versions/changes are tracked |
| Update Rules | When and how it may change |
| Retirement Rules | When it is superseded/retired |
| Verification Requirements | How its correctness is checked |
| Evidence Requirements | Evidence it must carry or reference |
| Acceptance Criteria | When it is considered complete/valid |
| Future Expansion Rules | How later phases extend it without forking authority |

**Standing values that apply to all planning documents unless a row overrides them:**
Version Strategy = Git history + `Last realigned` header date; Update Rules = change only through a planning
pass with a realignment report, never silently; Retirement Rules = mark `SUPERSEDED` with a pointer, never
delete (Decision B); Required Approvals = operator approval at the phase-exit/promotion gate that consumes
the document; Evidence Requirements = cite repository authority for every technical claim (`01G §3.1` ETM for
verification artifacts).

## 3. Required hierarchy → coverage map

The Pass-2 specification enumerates the implementation hierarchy the planning system must cover. Each required
element maps to exactly one authoritative artifact. **Status legend:** `EXISTS` (authoritative instance
present and adequate), `PARTIAL` (present as a stub/outline needing expansion in a later pass), `MISSING`
(no artifact yet; owner/target defined here for creation).

| # | Required hierarchy element | Authoritative artifact | Status |
|---|---|---|---|
| 1 | Master Implementation Roadmap | `docs/10-IMPLEMENTATION-ROADMAP.md` (+ execution companion `docs/10A-ROADMAP-EXECUTION-MAP.md`) | EXISTS |
| 2 | Implementation Phase Plans | `docs/plans/*.md` (9: shell + section-1…8) | PARTIAL (S1 full; S2 full task-by-task; S3–8+shell stubs, expanded in their phase-planning passes) |
| 3 | Implementation Task Specifications | `docs/templates/task/TASK-SPECIFICATION.template.md` → per-task instances | EXISTS (template); instances per phase |
| 4 | Component Specifications | `docs/templates/component/COMPONENT-SPECIFICATION.template.md`; `docs/specifications/components/00-COMPONENT-MAP.md` (index of 39); per-component `*-spec.md` authored per phase | EXISTS (template+map); PH-2 instances authored (6 specs + `PH2-INTEGRATION.md`); later-phase instances authored in their phases |
| 5 | Interface Specifications | Per-phase plan "Public Interfaces" blocks (precedent: S1 plan) | PARTIAL (defined inside phase plans) |
| 6 | Shared Contract Registry | `docs/planning/CONTRACT-REGISTRY.md` | EXISTS |
| 7 | Schema Registry | `docs/planning/SCHEMA-REGISTRY.md` | EXISTS |
| 8 | Configuration Registry | `docs/planning/CONFIG-REGISTRY.md` | MISSING (gap G-01) |
| 9 | Dependency Map | `docs/planning/DEPENDENCY-MAP.md` | EXISTS |
| 10 | Component Dependency Graph | `docs/planning/DEPENDENCY-MAP.md` (component edges) + roadmap §6 | EXISTS |
| 11 | Task Dependency Graph | per-phase plan task-dependency sections (PH-2: PLAN-S2 "Task execution graph") | PARTIAL (PH-2 complete) |
| 12 | Workstream Map | `docs/planning/WORKSTREAM-MAP.md` | EXISTS |
| 13 | Parallel Execution Map | `docs/planning/WORKSTREAM-MAP.md` + roadmap §9 | EXISTS |
| 14 | Critical Path Map | `docs/10-IMPLEMENTATION-ROADMAP.md §8` | EXISTS |
| 15 | Resource Allocation Plan | `docs/planning/RESOURCE-ALLOCATION-PLAN.md` | EXISTS (RPH3 Pass 7; G-02 resolved) |
| 16 | Repository Layout Map | `docs/00-DOCUMENTATION-INDEX.md` "Required future structure" | EXISTS |
| 17 | Verification Matrix | `docs/planning/VERIFICATION-MATRIX.md` | EXISTS |
| 18 | Acceptance Matrix | `docs/planning/VERIFICATION-MATRIX.md` (acceptance rows) | EXISTS |
| 19 | Evidence Traceability Matrix | `docs/templates/evidence/EVIDENCE-TRACEABILITY-MANIFEST.template.md` → per-phase verification reports; PH-2 architecture in `docs/planning/PH2-VERIFICATION-EVIDENCE-PROMOTION.md` | EXISTS (template); PH-2 architecture authored |
| 20 | Testing Strategy | `docs/planning/TEST-STRATEGY.md` | EXISTS |
| 21 | Risk Register | `docs/planning/RISK-REGISTER.md` | EXISTS |
| 22 | Decision Register | `docs/01-APPROVED-DECISIONS.md` + `docs/01R-PLANNING-RESOLUTIONS-AND-AMENDMENTS.md` | EXISTS |
| 23 | Operator Approval Templates | `docs/templates/approval/APPROVAL-CARD.template.md` | EXISTS |
| 24 | Promotion Package Template | `docs/templates/promotion/PROMOTION-PACKAGE.template.md` | EXISTS |
| 25 | Rollback Package Template | `docs/templates/ROLLBACK-PACKAGE.template.md`; PH-2 rollback architecture in `docs/planning/PH2-FAILURE-RECOVERY-ROLLBACK.md §4` | MISSING template (gap G-03); PH-2 architecture authored |
| 26 | Recovery Package Template | `docs/templates/RECOVERY-PACKAGE.template.md`; PH-2 recovery architecture in `docs/planning/PH2-FAILURE-RECOVERY-ROLLBACK.md §5` | MISSING template (gap G-04); PH-2 architecture authored |
| 41 | Regression Register | `docs/planning/REGRESSION-REGISTER.md` | EXISTS (established Pass 7, seeded) |
| 42 | PH-2 Failure/Recovery/Rollback Plan | `docs/planning/PH2-FAILURE-RECOVERY-ROLLBACK.md` | EXISTS (Pass 7) |
| 27 | Implementation Checklist | `docs/templates/checklist/COMPLETION-CHECKLIST.template.md` | EXISTS |
| 28 | Phase Exit Checklist | `docs/templates/checklist/PHASE-EXIT-CHECKLIST.template.md` | EXISTS (RPH3 Pass 10; G-05 resolved) |
| 29 | Implementation Handoff Template | `docs/templates/handoff/SECTION-HANDOFF.template.md`; `WORKSTREAM-HANDOFF.template.md` | EXISTS |
| 30 | Verification Report Template | `docs/templates/VERIFICATION-REPORT.template.md` (precedent: S1 report) | EXISTS (RPH3 Pass 6; G-06 resolved) |
| 31 | Release Planning Documents | `docs/release/RELEASE-PLAN.md` | EXISTS |
| 32 | Installer Planning | `docs/release/INSTALLER-PLAN.md` | EXISTS |
| 33 | Migration Planning | `docs/release/UPDATE-AND-MIGRATION-PLAN.md` | EXISTS |
| 34 | Update Planning | `docs/release/UPDATE-AND-MIGRATION-PLAN.md` | EXISTS |
| 35 | Maintenance Planning | `docs/release/MAINTENANCE-PLAN.md` | MISSING (gap G-07) |
| 36 | Documentation Planning | `docs/planning/DOCUMENTATION-PLAN.md` | MISSING (gap G-08) |
| 37 | Baseline Manifest Template | `docs/templates/baseline/PROJECT-BASELINE-MANIFEST.template.md` | EXISTS |
| 38 | Evidence Package Template | `docs/templates/evidence/EVIDENCE-PACKAGE.template.md` | EXISTS |
| 39 | Planning Authority Ledger | `docs/planning/00-PLANNING-AUTHORITY-LEDGER.md` (this file) | EXISTS |
| 40 | Continuation Ledger | `docs/planning/00-CONTINUATION-LEDGER.md` | EXISTS |

**Coverage summary:** 32 EXISTS · 5 PARTIAL (phase plans + their interface/task-graph/component instances) ·
8 MISSING gaps (G-01…G-08). All gaps are non-blocking for PH-2 planning; each is owned by the pass named in
§6 and none is a prerequisite of the PH-2 roadmap/phase-plan work.

## 4. Authoritative registry (concrete governing documents)

Single-owner rows for the documents that carry planning authority. Templates and per-instance artifacts
inherit the standing values in §2.

| Document ID | Path | Purpose (single) | Authority | Owner | Key inputs → outputs |
|---|---|---|---|---|---|
| ROADMAP-10 | `docs/10-IMPLEMENTATION-ROADMAP.md` | Phase order, gates, critical path | Plan (governing order) | Roadmap pass (PH-x planning) | `05`,`01*`,`01R` → 9-phase order, gates §15 |
| ROADMAP-10A | `docs/10A-ROADMAP-EXECUTION-MAP.md` | Per-phase execution environment + order-validation record | Plan (companion, subordinate to ROADMAP-10) | Roadmap pass | `10`,`DEPENDENCY-MAP`,`WORKSTREAM-MAP` → per-phase env map |
| GLOSSARY-11 | `docs/11-CONTROLLED-GLOSSARY-AND-CROSSWALKS.md` | Term/state/stage-section crosswalk | Derived index | Planning | `01*` → controlled vocab |
| PLAN-S1 | `docs/plans/section-1-requirements-contracts.md` | PH-1 executable TDD plan | Plan | PH-1 | design → executed plan (done) |
| PLAN-S2 | `docs/plans/section-2-task-queue-and-state-machine.md` | PH-2 executable TDD plan | Plan | PH-2 planning | `01L/01D/01M/02/01F`,`01R` → PH-2 tasks |
| PLAN-Sx | `docs/plans/section-{3..8}-*.md`, `shell-*.md` | Per-phase executable plans | Plan | Each phase's planning | governing supplements → phase tasks |
| REG-CONTRACT | `docs/planning/CONTRACT-REGISTRY.md` | Shared-contract ownership/versions | Registry | Planning | phase plans → contract owners |
| REG-SCHEMA | `docs/planning/SCHEMA-REGISTRY.md` | Schema/migration inventory | Registry | Planning | phase plans → schema inventory |
| MAP-DEP | `docs/planning/DEPENDENCY-MAP.md` | Component/phase dependency edges | Registry | Planning | roadmap → dependency graph |
| MAP-WORKSTREAM | `docs/planning/WORKSTREAM-MAP.md` | Parallel-safety/independence | Registry | Planning | `01D`,roadmap → parallel map |
| MATRIX-VERIF | `docs/planning/VERIFICATION-MATRIX.md` | Criterion→test/acceptance rows | Registry | Planning | `01G`,phase plans → verification rows |
| STRAT-TEST | `docs/planning/TEST-STRATEGY.md` | Test taxonomy & gates | Registry | Planning | `01G` → test strategy |
| VEP-PH2 | `docs/planning/PH2-VERIFICATION-EVIDENCE-PROMOTION.md` | PH-2 verification/evidence/promotion architecture + traceability | Plan (subordinate to `01G`/matrix) | PH-2 planning | PLAN-S2, specs, matrix → PH-2 req/test/evidence/promotion |
| FRR-PH2 | `docs/planning/PH2-FAILURE-RECOVERY-ROLLBACK.md` | PH-2 failure/recovery/rollback/resilience plan + traceability | Plan (subordinate to `01M`/`04`/ROLLBACK-PLAN) | PH-2 planning | `01M`,`04`,ROLLBACK-PLAN,specs → PH-2 failure modes/recovery/rollback |
| SEC-PH2 | `docs/planning/PH2-SECURITY-TRUST-BOUNDARIES.md` | PH-2 security/assets/threats/trust-boundaries + traceability | Plan (subordinate to `01K`/`01E`/`01M`) | PH-2 planning | `01K`,`01E`,`01M`,specs → PH-2 assets/threats/security tests |
| DEP-PH2 | `docs/planning/PH2-DEPLOYMENT-MIGRATION.md` | PH-2 platform footprint + runtime migration architecture | Plan (subordinate to `01O`/`01N`/`docs/release/*`) | PH-2 planning | `01O`,`01N`,release plans,PLAN-S2 → PH-2 migrations 0001-0003 |
| CERT-PH2 | `docs/planning/PH2-IMPLEMENTATION-READINESS-CERTIFICATE.md` | Final PH-2 inventory, audits, handoff, implementation-start package, readiness certificate | Derived certification | PH-2 planning (Pass 10) | all PH-2 artifacts → certificate `PH2_CERTIFIED_WITH_NONBLOCKING_GAPS` |
| REGR-000 | `docs/planning/REGRESSION-REGISTER.md` | Repair + mandatory-regression ledger | Derived index | every repairing pass/task | repairs → regression flags |
| REG-RISK | `docs/planning/RISK-REGISTER.md` | Risk inventory & mitigations | Registry | Planning | all → risks |
| SPEC-COMPONENT-MAP | `docs/specifications/components/00-COMPONENT-MAP.md` | Component inventory & boundaries | Registry | Planning | `02`,`01*` → component map |
| PAL-000 | `docs/planning/00-PLANNING-AUTHORITY-LEDGER.md` | This catalog | Derived index | Planning system | corpus → coverage/authority map |
| CL-000 | `docs/planning/00-CONTINUATION-LEDGER.md` | Cross-session/pass state of record | Derived index | Every pass | passes → current state |

## 5. Authority-relationship verification (this pass)

- **No duplicate ownership:** each row in §4 has one owner; each hierarchy element in §3 maps to exactly one
  artifact. Overlaps that *looked* like duplicates are resolved by designation: Acceptance Matrix is a
  section of MATRIX-VERIF (not a separate file); Parallel Execution Map and Component Dependency Graph are
  views owned by MAP-WORKSTREAM and MAP-DEP respectively; Update Planning and Migration Planning share one
  owner file (`UPDATE-AND-MIGRATION-PLAN.md`) by design.
- **No circular authority:** dependency direction flows governing corpus (`PROJECT_DEFINITION`,`01*`,`01R`) →
  roadmap/glossary → registries/maps → phase plans → task/component/interface instances → verification
  reports. This is a DAG; no registry depends on a document that depends on it. Verified by inspection this
  pass.
- **No undocumented relationships:** every producer/consumer edge used above is either in this ledger or in
  `docs/00-DOCUMENTATION-INDEX.md` authority order.
- **No missing approval path:** every phase plan terminates at an operator phase-exit/promotion gate
  (`docs/10 §15`); templates for approval/promotion exist (rows 23–24).
- **Missing rollback/recovery/maintenance templates (G-03/G-04/G-07)** are the only approval-adjacent gaps;
  they are non-blocking because PH-1 rollback was proven in code/tests and PH-2 rollback boundary is
  journal-authoritative (defined in PLAN-S2), independent of the not-yet-written template.

## 6. Gap ownership (non-blocking; scheduled, not silently deferred)

| Gap | Artifact | Owning pass | Blocking? |
|---|---|---|---|
| G-01 | CONFIG-REGISTRY | Pass covering configuration (PH-4/PH-8 planning) | No |
| G-02 | RESOURCE-ALLOCATION-PLAN | Roadmap/resource pass (PH-3/PH-4 planning) | No |
| G-03 | ROLLBACK-PACKAGE template | PH-7 planning (recovery/promotion) | No |
| G-04 | RECOVERY-PACKAGE template | PH-7 planning | No |
| G-05 | PHASE-EXIT-CHECKLIST template | next planning pass | No |
| G-06 | VERIFICATION-REPORT template | next planning pass (generalize S1 report) | No |
| G-07 | MAINTENANCE-PLAN | PH-8 planning | No |
| G-08 | DOCUMENTATION-PLAN | PH-8 planning | No |

## 7. Update rules for this ledger

Rebuilt at the start of every planning pass (realignment protocol) and updated at the end. Any new planning
document must be added here with a single-owner row before it is relied upon (mirrors the change-control rule
in `docs/00-DOCUMENTATION-INDEX.md §"Change-control rule"`). Retirement marks `SUPERSEDED` with a pointer;
rows are never deleted.

## 8. Worker Execution Substrate documents (out-of-roadmap; registered 2026-07-25)

The **Worker Execution Substrate** (`CMP-WORKER`) is an **out-of-roadmap** component — **prebuilt PH-4/PH-5
execution infrastructure, NOT roadmap PH-3**. Registering its documents here does **not** amend the Master
Implementation Roadmap and does **not** create a duplicate authority with roadmap **PH-3 = Watchdog**
(`docs/plans/section-3-orchestrator-watchdog-and-permissions.md`), which remains the sole owner of the
roadmap-PH-3 security-spine decisions. Authoritative classification: `docs/WORKER-EXECUTION-SUBSTRATE-CLASSIFICATION.md`.

| Document ID | Path | Purpose (single) | Authority | Owner |
|---|---|---|---|---|
| WES-CLASS | `docs/WORKER-EXECUTION-SUBSTRATE-CLASSIFICATION.md` | Reclassification record + label mapping (substrate ≠ roadmap PH-3) | Derived classification | Operator decision 2026-07-25 |
| WES-PLAN | `docs/plans/worker-execution-substrate.md` | Substrate implementation plan (T3.1–T3.5) | Plan (out-of-roadmap) | Substrate build |
| WES-SPEC | `docs/specifications/components/worker-engine-spec.md` | Substrate component spec (`CMP-WORKER`) | Component spec | Substrate build |
| WES-FRR | `docs/planning/WES-FAILURE-RECOVERY-ROLLBACK.md` | Substrate failure/recovery/rollback | Plan (out-of-roadmap) | Substrate build |
| WES-SEC | `docs/planning/WES-SECURITY-TRUST-BOUNDARIES.md` | Substrate security/trust boundaries | Plan (out-of-roadmap) | Substrate build |
| WES-VEP | `docs/planning/WES-VERIFICATION-EVIDENCE-PROMOTION.md` | Substrate verification/evidence/promotion | Plan (out-of-roadmap) | Substrate build |
| WES-CERT | `docs/planning/WES-IMPLEMENTATION-READINESS-CERTIFICATE.md` | Substrate readiness certificate | Derived certification | Substrate build |
| WES-EVID | `docs/verification/worker-execution-substrate-evidence-report.md` | Substrate evidence report (substrate gate 18/18) | Report | Substrate build |
| WES-TESTS | `docs/verification/worker-execution-substrate-test-summary.md` | Substrate test summary (85 tests) | Report | Substrate build |

**Superseded branch:** `claude/ph3-worker-engine-xefzze` — tip `7e023a2`, zero unique commits — **SUPERSEDED**
by `claude/ph3-worker-engine` (no unique required work).

## 9. Roadmap PH-3 planning corpus — identifier namespace + document registry (registered 2026-07-25)

Roadmap **PH-3 = Watchdog, Permissions, Approval, Audit & Tools**
(`docs/plans/section-3-orchestrator-watchdog-and-permissions.md`; roadmap §PH-3) is **UNBUILT**. Its
implementation-planning corpus is authored on branch `claude/roadmap-ph3-security-spine-planning` (forked
from `claude/ph3-worker-engine` @ `7b1922e`). This section registers that corpus with single-owner rows. It
does **not** amend the Master Implementation Roadmap and does **not** create duplicate authority with the
Worker Execution Substrate (§8, `WES-*`, out-of-roadmap). Roadmap PH-3 is the sole owner of the roadmap
security-spine decisions.

### 9.1 Identifier namespace (disjoint from the substrate)

The Worker Execution Substrate's development-track labels are authoritatively mapped in
`docs/WORKER-EXECUTION-SUBSTRATE-CLASSIFICATION.md §3`, and its former `docs/planning/PH3-*.md` planning
filenames were **vacated** (renamed to `WES-*`, WES-CLASS §4). To keep roadmap PH-3 identifiers separate,
roadmap PH-3 planning uses the **`RPH3`** namespace and does **not** reuse any `PH3-*`/`T3.x`/`SEC-PH3-xx`/
`PROM-PH3`/`WES-*` identifier.

| Concept | Roadmap PH-3 (this corpus) | Substrate — do NOT reuse |
|---|---|---|
| Task IDs | `RPH3-T1`…`RPH3-T5` | `T3.1`…`T3.5` |
| Security-test labels | `SEC-RPH3-01`… | `SEC-PH3-01`…`05` |
| Promotion / phase-exit gate | `PROM-RPH3` (roadmap PH-3 exit; VM-2) | `PROM-PH3` |
| Planning doc IDs | `*-RPH3` (§9.2) | `WES-*` |
| Planning doc paths | `docs/planning/RPH3-*.md` | `docs/planning/WES-*.md` |
| Verify script (Pass 10) | `scripts/verify_roadmap_ph3.py` | `scripts/verify_worker_substrate.py` |
| Verification reports | `docs/verification/roadmap-ph3-*.md` | `docs/verification/worker-execution-substrate-*.md` |

Roadmap-PH-3 task-ID mapping (against the section-3 plan's task numbers and the authoritative COMPONENT-MAP):

| RPH3 task | Section-3 task | Component(s) | Owned path (all currently absent) |
|---|---|---|---|
| RPH3-T1 | Task 3.1 | CMP-WATCH | `src/factory/watchdog/**` |
| RPH3-T2 | Task 3.2 | CMP-PERM | `src/factory/permission/**` |
| RPH3-T3 | Task 3.3 | CMP-APPROVAL | `src/factory/approval/**` |
| RPH3-T4 | Task 3.4 | CMP-AUDITW, CMP-AUDITV | `src/factory/audit/**` |
| RPH3-T5 | Task 3.5 | CMP-TOOLREG, CMP-TOOLGW, CMP-DIAG (Safe Mode), file-op | `src/factory/{tools,fileops,diagnostics/safe_mode}/**` |

### 9.2 Planned planning documents (single-owner rows)

Status legend: `PLANNED` (registered here; authored by the named pass). Each inherits the §2 standing values.
`PLAN-S3` is the real roadmap PH-3 plan preserved by WES-CLASS §4; the substrate plan is `WES-PLAN`
(`docs/plans/worker-execution-substrate.md`), a distinct file.

| Document ID | Path | Purpose (single) | Authority | Owning pass | Status |
|---|---|---|---|---|---|
| PLAN-S3 | `docs/plans/section-3-orchestrator-watchdog-and-permissions.md` | Roadmap PH-3 executable task plan (RPH3-T1…T5 + execution/dependency graph + external-blocker register §7) | Plan | RPH3 Pass 5 | **EXISTS** (expanded Pass 5) |
| SPEC-RPH3-set | `docs/specifications/components/{watchdog,permission,approval,audit-writer,audit-validator,tool-registry,tool-gateway,safe-mode,file-op-service}-spec.md` + `RPH3-INTEGRATION.md` | Per-component 18-field specs for CMP-WATCH/PERM/APPROVAL/AUDITW/AUDITV/TOOLREG/TOOLGW/DIAG + CMP-FILEOP | Component spec | RPH3 Pass 4 | **EXISTS** (authored Pass 4; 9 specs + integration) |
| VEP-RPH3 | `docs/planning/RPH3-VERIFICATION-EVIDENCE-PROMOTION.md` | Verification/evidence/promotion architecture; `01M`(32)+`01K`(25) traceability; VM-2; `PROM-RPH3` | Plan (subordinate to `01G`/MATRIX-VERIF) | RPH3 Pass 6 | **EXISTS** (Pass 6; 18 VR rows) |
| FRR-RPH3 | `docs/planning/RPH3-FAILURE-RECOVERY-ROLLBACK.md` | Failure/recovery/rollback (Watchdog-loss, fail-closed, quarantine) | Plan (subordinate to `01M`/`04`) | RPH3 Pass 7 | **EXISTS** (Pass 7; 18 FM rows) |
| RES-ALLOC-000 | `docs/planning/RESOURCE-ALLOCATION-PLAN.md` | Resource envelopes + staged thresholds + reservation policy | Plan (subordinate to `01M §3.3`/`01J §3.3`) | Planning (RPH3 Pass 7; G-02) | **EXISTS** (Pass 7) |
| SEC-RPH3 | `docs/planning/RPH3-SECURITY-TRUST-BOUNDARIES.md` | Security assets/threats/trust boundaries; `SEC-RPH3-xx` tests | Plan (subordinate to `01K`/`01E`/`01M`) | RPH3 Pass 8 | **EXISTS** (Pass 8; 8 assets, 13 threats, 4 zones, SEC-RPH3-01..12) |
| DEP-RPH3 | `docs/planning/RPH3-DEPLOYMENT-MIGRATION.md` | Platform footprint + PH-3 schemas/migrations (permission-grant, approval-record, tool-declaration, audit-record; separate PH-3 stores under freeze); resolves ODI-RPH3-01 | Plan (subordinate to `01O`/`01N`) | RPH3 Pass 9 | **EXISTS** (Pass 9) |
| CERT-RPH3 | `docs/planning/RPH3-IMPLEMENTATION-READINESS-CERTIFICATE.md` | Final inventory, 12 audits, implementation-start package, readiness certificate | Derived certification | RPH3 Pass 10 | **EXISTS** (Pass 10; verdict `RPH3_CERTIFIED_WITH_NONBLOCKING_GAPS`) |

### 9.3 Contracts & schemas owned by roadmap PH-3

Per CONTRACT-REGISTRY (owner PH-3): `CTR-PERMISSION-GRANT` (CMP-PERM), `CTR-APPROVAL-RECORD` (CMP-APPROVAL),
`CTR-TOOL-DECLARATION` (CMP-TOOLREG), `CTR-AUDIT-RECORD` (CMP-AUDITW). Schemas to author (Pass 9):
`permission-grant`, `approval-record`, `tool-declaration`, `audit-chain`. Any structural runtime-DB need is a
new SHA-pinned `0004_*` migration under the schema-freeze rule (SCHEMA-REGISTRY); the substrate added none.

### 9.4 Gap ownership updates

- **G-02 RESOURCE-ALLOCATION-PLAN — RESOLVED (RPH3 Pass 7):** `docs/planning/RESOURCE-ALLOCATION-PLAN.md`
  authored (envelopes + staged thresholds + reservation policy; PH-4 extends it for CMP-RESSCHED).
- **G-06 VERIFICATION-REPORT template — RESOLVED (RPH3 Pass 6):** `docs/templates/VERIFICATION-REPORT.template.md`
  created (generalizes the Section-1 report). **G-05 PHASE-EXIT-CHECKLIST — RESOLVED (RPH3 Pass 10):**
  `docs/templates/checklist/PHASE-EXIT-CHECKLIST.template.md` created.

### 9.5 Authority-relationship verification (this pass)

- **No duplicate ownership:** every RPH3 row owns a distinct artifact; none collides with a `WES-*` (§8),
  PH-2 (`PH2-*`, §4), or PH-1 row. The `CMP-*` IDs are the COMPONENT-MAP's existing single owners; RPH3
  specs instantiate them for roadmap PH-3, not the substrate.
- **No circular authority:** governing corpus (`01K`,`01M`,`01R`) → roadmap §PH-3 → this registry → RPH3
  planning docs → component/task/interface instances → verification reports. DAG; verified by inspection.
- **Namespace disjointness:** the §9.1 table is verified disjoint from WES-CLASS §3 and from the vacated
  `docs/planning/PH3-*.md` filenames (WES-CLASS §4).
- **File-op component note — RESOLVED (RPH3 Pass 4):** `CMP-FILEOP` added as COMPONENT-MAP #40 via
  change-control (count 39→40), correcting a prior omission (roadmap §PH-3 already names "safe file-op"); its
  spec is `docs/specifications/components/file-op-service-spec.md`. Not folded into CMP-TOOLGW — file-op has a
  distinct owned path (`src/factory/fileops/**`) and responsibility (path authority, escape blocking, Dec B
  deletion-gating, archive limits).
