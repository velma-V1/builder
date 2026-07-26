# Roadmap PH-3 — Verification, Evidence & Promotion Architecture (VEP-RPH3)

**Document ID:** VEP-RPH3 · **Repository path:** `docs/planning/RPH3-VERIFICATION-EVIDENCE-PROMOTION.md`
**Status:** Active plan (subordinate to `01G` + `docs/planning/VERIFICATION-MATRIX.md`) · **Owner:** RPH3
planning (Pass 6) · **Established:** 2026-07-26. **Governing:** `01G` (ETM), `01M` (32), `01K` (25), `01R`
Dec A/B, roadmap `docs/10 §PH-3` (VM-2). **Namespace:** RPH3 (PAL §9.1); no `SEC-PH3-*`/`PROM-PH3`/`WES-*`
reuse — the roadmap-PH-3 promotion gate is **`PROM-RPH3`**, security-test labels are **`SEC-RPH3-*`**.

## 1. Purpose

Defines how roadmap PH-3 (the Watchdog security spine) is verified, what evidence each requirement carries,
and the exact promotion gate (`PROM-RPH3`). It restates no acceptance criterion's authority (those are `01M`/
`01K`); it maps each to a verification requirement, a test category, and an Evidence Traceability Manifest
(ETM) chain, then defines the VM-2 integration gate. It builds only on frozen PH-2 interfaces (PLAN-S3 §1) and
consumes **no** Worker Execution Substrate code.

## 2. Verification requirement register (VR-RPH3)

Each VR maps ≥1 `01M`/`01K` acceptance criterion (or Decision) to a task, component, test category, and
evidence. Categories: U=unit, I=integration, S=security, A=adversarial, F=failure-path, R=regression.

| VR | Requirement | Criteria | Task/Comp | Cats | Evidence (ETM) |
|---|---|---|---|---|---|
| VR-RPH3-01 | Independent, normally read-only Watchdog; separate process; narrow interface only | `01M` #1-4 | T1/CMP-WATCH | U,I,S | watchdog-independence ETM |
| VR-RPH3-02 | Monotonic timing; staged thresholds + hysteresis; REDUCED_MONITORING on missing sensor | `01M` #5-7 | T1/CMP-WATCH | U,A | timing/threshold ETM |
| VR-RPH3-03 | Only enumerated critical triggers; bounded restart+backoff+circuit-breaker; fail-closed core controls | `01M` #8-11,#18,#19,#25 | T1 (+T2,T4 cross) | U,F | containment/recovery ETM |
| VR-RPH3-04 | Every intervention audited; Watchdog cannot modify own authority | `01M` #21,#22 | T1/CMP-WATCH | S,I | watchdog-audit ETM |
| VR-RPH3-05 | Watchdog loss pauses/blocks high-risk work; low-risk read-only continues only while controls healthy | `01M` #30,#31,#35 | T1/CMP-WATCH | F | watchdog-loss ETM (RM-1) |
| VR-RPH3-06 | Restricted Safe Mode: no autonomous execution/writes; capability-scoped | `01M` #20,#26; `01K` #22 | T5/CMP-DIAG | S,U | safe-mode ETM |
| VR-RPH3-07 | Default-deny tool registry + single gateway; models cannot bypass | `01K` #1 | T5/CMP-TOOLREG,TOOLGW | S,A | no-bypass ETM |
| VR-RPH3-08 | Least-privilege grants ≤ task approval; TOCTOU revalidation; no permanent unrestricted authority | `01K` #2,#4 | T2/CMP-PERM | U,S,A | permission ETM |
| VR-RPH3-09 | Approvals bound/expiring/revocable, non-reusable; destructive/external separate confirmation; security violations denied not offered | `01K` #3,#5 | T3/CMP-APPROVAL | U,S,A | approval ETM |
| VR-RPH3-10 | Path canonicalization + escape blocking; archive entry/depth/decompression limits | `01K` #10,#11 | T2/CMP-PERM,T5/CMP-FILEOP | S,A | path-safety ETM |
| VR-RPH3-11 | Mandatory resource controls; complete process-tree termination; no surviving orphan; evidence before disposal | `01K` #13,#14,#15,#17 | T5/CMP-TOOLGW | F,A | resource/termination ETM |
| VR-RPH3-12 | Downloaded-component provenance/integrity; repeated-failure quarantine; sandbox quarantine on abnormal exit | `01K` #9,#16,#18 | T5/CMP-TOOLREG,TOOLGW | U,F | provenance/quarantine ETM |
| VR-RPH3-13 | Tool output untrusted → schema-validated; oversized/invalid fails closed | `01K` #25 | T5/CMP-TOOLGW | S,A | output-validation ETM |
| VR-RPH3-14 | Append-only hash-chained audit (sole writer); deletion/truncation/reorder/rewrite/anchor breaks detected; audit non-authoritative while broken | `01K` #19,#20 | T4/CMP-AUDITW,AUDITV | U,S,A | audit-integrity ETM |
| VR-RPH3-15 | Repository/downloaded instructions cannot override governing policy | `01K` #12 | T2/CMP-PERM (cross) | S,A | instruction-distrust ETM |
| VR-RPH3-16 | Immediate operator emergency stop; containment over graceful completion | `01K` #21; `01M` #16 | T1/CMP-WATCH | F | emergency-stop ETM |
| VR-RPH3-17 | **Decision A** autonomy envelope: level gates auto vs approval-card actions | Dec A | T2 classify + T3 card | U,S,A | autonomy-envelope ETM |
| VR-RPH3-18 | **Decision B** all file deletion approval-required; no auto-delete path | Dec B | T2 decision + T3 card + T5 delete-gate | U,S,A | deletion-gating ETM |

**Interface-defined-only (verified in a later phase — NOT an RPH3 exit criterion, Constraint 7):**
`01K` #6 host-shell/elevated (seam contract in CMP-TOOLGW; real enforcement PH-5 sandbox + XIB-02), `01K` #7
credentials (PH-5 secret broker), `01K` #8 network (PH-5 network broker), `01K` #23/#24 sandbox-record
separation (PH-5/PH-7). RPH3 defines the permission class / gateway contract each must satisfy; RPH3 does not
verify their enforcement. `01M` snapshot/drill criteria (#24,#27-29,#31) are PH-7.

## 3. Test strategy & categories

Per the uniform context (PLAN-S3 §2): pytest + hypothesis; ≥95% branch coverage per PH-3 module; `01G`
verdict enum (`PASS/FAIL/BLOCKED/INCONCLUSIVE/NOT_TESTABLE`). Category obligations:

- **Unit** — pure logic per component (decisions, chain math, threshold state, card completeness).
- **Integration** — cross-component flows over frozen PH-2 (register→invoke→permit→approve→file-op→audit).
- **Security (`SEC-RPH3-01..`)** — the core-control invariants: no-bypass, single-audit-writer, least-priv,
  deletion-gating, Safe-Mode no-write, self-authority-immutability. A failing security test **blocks** promotion.
- **Adversarial** — active attack attempts (gateway bypass, forged audit identity, TOCTOU race, autonomy
  bypass, archive bomb, escape, oversized output, intervention flood).
- **Failure-path** — Watchdog-loss, resource breach + process-tree kill, mid-append rollback, restart w/o
  blind resume, audit-store unavailable → fail closed.
- **Regression** — none seeded at plan time; any repair during implementation seeds a REGR-* row
  (`REGRESSION-REGISTER.md`) with a mandatory guarding test.

## 4. Evidence Traceability Manifest (ETM) architecture

Per `01G §3.1`, each VR-RPH3 produces an ETM chain: `requirement → test(s) → result/verdict → evidence
artifact`. Evidence is emitted by `scripts/verify_roadmap_ph3.py` into a regenerable (gitignored)
`artifacts/verification/roadmap-ph3/manifest.json`, and summarized in
`docs/verification/roadmap-ph3-evidence-report.md` (authored during implementation, using the
`VERIFICATION-REPORT.template.md` created this pass — gap G-06). A broken ETM link blocks promotion (`CTR-ETM`
semantics apply even though the full ETM engine is PH-7: at PH-3 the manifest is a static per-criterion table).

## 5. VM-2 — security-spine integration gate

VM-2 is the single roadmap milestone for PH-3 (`docs/10 §12`). Its complete path (PLAN-S3 §5) exercises all
nine components end to end: unregistered-tool denial → grant-scoped permitted action → Dec A/B approval card →
canonicalized delete-gated file op → every privileged action appended to the audit chain → chain validated →
Watchdog observation + pause-on-control-loss → Safe-Mode no-autonomous-write. VM-2 PASS requires every
VR-RPH3-01..18 at verdict `PASS` with a complete ETM chain and no unresolved critical/high defect.

## 6. Promotion gate — `PROM-RPH3`

`PROM-RPH3` (roadmap PH-3 exit; distinct from the substrate's `PROM-PH3`) is satisfied when **all** hold:

1. Every `01M`(32) and `01K`(25) **RPH3-scoped** criterion at verdict `PASS` (interface-only PH-5/PH-7 items
   excluded per §2, with their interface contracts present).
2. VM-2 security-spine integration path PASS (§5).
3. Decisions A and B proven (VR-RPH3-17/18).
4. Audit append-only + break detection proven (VR-RPH3-14); Safe-Mode no-autonomous-write proven (VR-RPH3-06).
5. ≥95% branch coverage across `src/factory/{watchdog,permission,approval,audit,tools,fileops,diagnostics}`.
6. No unresolved critical/high defect; every REGR-* seeded during implementation cleared.
7. `01G §3.1` ETM chain complete for every VR-RPH3.
8. **Operator PH-3 exit approval** + authorization to begin `01B` Stage-2 cutover (`docs/10 §15`).

**Not required by `PROM-RPH3` (external):** the four PR #10 substrate blockers (XIB-01..04, PLAN-S3 §7) are
prerequisites for any PR #10 *merge*, owned by a dedicated PR #10 correction / PH-5 — independent of this gate.

## 7. Traceability summary

18 VR rows → 9 components → 5 tasks; every RPH3-scoped `01M`/`01K` criterion + Dec A/B covered; VM-2 path
complete; promotion gate closed. Non-blocking: G-02 RESOURCE-ALLOCATION-PLAN (RPH3 Pass 7); the ETM engine
proper (`CTR-ETM`) is PH-7 (here the manifest is a static table).
