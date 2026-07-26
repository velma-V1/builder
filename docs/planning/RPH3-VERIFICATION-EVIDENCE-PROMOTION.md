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

Each VR maps ≥1 **acceptance criterion** (`01M-AC-*` / `01K-AC-*`) or `01R` Decision to a task, component,
test category, and evidence. **Acceptance IDs are authoritative in `docs/planning/RPH3-TRACEABILITY.md`**
(TRACE-RPH3); this register never uses ambiguous `#NN` references and never cites a decision-list number
(`01M-DEC-*`/`01K-DEC-*`) as an acceptance criterion. Categories: U=unit, I=integration, S=security,
A=adversarial, F=failure-path, R=regression.

| VR | Requirement | Acceptance IDs | Task/Comp | Cats | Evidence (ETM) |
|---|---|---|---|---|---|
| VR-RPH3-01 | Independent, normally read-only Watchdog; separate process; narrow interface only | `01M-AC-01,02,03,04` | T1/CMP-WATCH | U,I,S | watchdog-independence ETM |
| VR-RPH3-02 | Monotonic timing; staged thresholds + hysteresis; REDUCED_MONITORING; Windows auto-launch off by default | `01M-AC-05,06,07,32` | T1/CMP-WATCH | U,A | timing/threshold ETM |
| VR-RPH3-03 | Only enumerated critical triggers; bounded restart+backoff+circuit-breaker; failure normalization; fail-closed core controls | `01M-AC-08,09,10,11,19` | T1 (+T2,T4 cross) | U,F | containment/recovery ETM |
| VR-RPH3-04 | Narrow-interface validation; every intervention audited; Watchdog cannot modify own authority | `01M-AC-04,21,22` | T1/CMP-WATCH | S,I | watchdog-audit ETM |
| VR-RPH3-05 | No blind resume; recovery simulations (Watchdog-loss) | `01M-AC-14,23` | T1/CMP-WATCH | F | watchdog-loss ETM (RM-1) |
| VR-RPH3-06 | Restricted Safe Mode: no autonomous execution/writes; capability-scoped degradation | `01M-AC-18,20`; `01K-AC-22` | T5/CMP-DIAG | S,U | safe-mode ETM |
| VR-RPH3-07 | Watchdog loss pauses/blocks high-risk work; low-risk read-only continues only while controls healthy | `01M-AC-30,31` | T1/CMP-WATCH | F | watchdog-loss ETM |
| VR-RPH3-08 | Default-deny tool registry + single gateway; models cannot bypass | `01K-AC-01` | T5/CMP-TOOLREG,TOOLGW | S,A | no-bypass ETM |
| VR-RPH3-09 | Least-privilege grants ≤ task approval; TOCTOU revalidation; no permanent unrestricted authority | `01K-AC-02,04` | T2/CMP-PERM | U,S,A | permission ETM |
| VR-RPH3-10 | Approvals bound/expiring/revocable, non-reusable; destructive/external separate confirmation | `01K-AC-03,05` | T3/CMP-APPROVAL | U,S,A | approval ETM |
| VR-RPH3-11 | Path canonicalization + escape blocking; archive entry/depth/decompression limits | `01K-AC-10,11` | T2/CMP-PERM, T5/CMP-FILEOP | S,A | path-safety ETM |
| VR-RPH3-12 | No telemetry leaves without explicit approval | `01K-AC-25` | cross (RPH3 emits none) + PH-1 config | S | no-telemetry ETM |
| VR-RPH3-13 | Downloaded-component provenance/integrity; repeated-failure **tool** quarantine | `01K-AC-09,18` | T5/CMP-TOOLREG | U,F | provenance/quarantine ETM |
| VR-RPH3-14 | Append-only hash-chained audit (sole writer); deletion/truncation/reorder/rewrite/anchor breaks detected; non-authoritative while broken | `01K-AC-19,20` | T4/CMP-AUDITW,AUDITV | U,S,A | audit-integrity ETM |
| VR-RPH3-15 | Immediate operator emergency stop; containment over graceful completion | `01K-AC-21` (rationale `01M-DEC-16`) | T1/CMP-WATCH | F | emergency-stop ETM |
| VR-RPH3-16 | Repository/downloaded instructions cannot override governing policy | `01K-AC-12` | T2/CMP-PERM (cross) | S,A | instruction-distrust ETM |
| VR-RPH3-17 | **Decision A** autonomy envelope: level gates auto vs approval-card actions | `01R` Dec A | T2 classify + T3 card | U,S,A | autonomy-envelope ETM |
| VR-RPH3-18 | **Decision B** all file deletion approval-required; no auto-delete path | `01R` Dec B | T2 decision + T3 card + T5 delete-gate | U,S,A | deletion-gating ETM |
| VR-RPH3-19 | Security decision/approval/privileged action/intervention/tool-file op never reports success while its required audit record is absent (cross-store) | `01M-AC-12` (rationale `01M-DEC-17`); `01K-DEC-29` | cross-store protocol (all writing comps) | I,F,A | cross-store-consistency ETM |
| VR-RPH3-20 | Tool output untrusted → schema-validated; oversized/invalid **fails closed**; resource/termination **request contract** defined; **fail-closed when no valid sandbox executor exists** | `01K-DEC-25`; `01K-AC-13`(request contract) | T5/CMP-TOOLGW (interface) | S,A | output-validation + fail-closed-no-executor ETM |

**Decision-vs-acceptance guard:** VR-RPH3-20 traces tool-output validation to **`01K-DEC-25`** (the decision
"tool output is untrusted"), **not** `01K-AC-25` (which is "no telemetry", covered by VR-RPH3-12) — this
corrects the prior conflation. VR-RPH3-19 traces the audit-before-success invariant to `01M-AC-12` +
`01K-DEC-29`.

### 2a. PH-5 enforcement gates (moved OUT of `PROM-RPH3`)

The following acceptance criteria require a real sandbox/executor and are **certified by PH-5** (or PH-5/PH-7),
**never by `PROM-RPH3`**. RPH3's only obligation is the **request/decision contract** + **fail-closed when no
valid sandbox executor exists** (XIB-02). Enforcement gate IDs `EG-PH5-*`:

| PH-5 gate | Acceptance | RPH3 interface obligation (verified here) |
|---|---|---|
| EG-PH5-01 | `01K-AC-06` no host shell/elevated | seam contract; fail-closed when no sandbox executor |
| EG-PH5-02 | `01K-AC-07` credential lifecycle | credential permission class defined (broker = PH-5) |
| EG-PH5-03 | `01K-AC-08` network denial | network permission class defined (broker = PH-5) |
| EG-PH5-04 | `01K-AC-13` **OS enforcement** of resource limits | limit **request contract** + fail-closed |
| EG-PH5-05 | `01K-AC-14` complete process-tree termination | termination **request contract**; RPH3 proves no direct host execution occurs |
| EG-PH5-06 | `01K-AC-15` no surviving orphan | (PH-5 sandbox) |
| EG-PH5-07 | `01K-AC-16` sandbox quarantine on abnormal exit | (PH-5 sandbox) |
| EG-PH5-08 | `01K-AC-17` evidence before sandbox disposal | (PH-5/PH-7) |
| EG-PH5-09 | `01K-AC-23,24` sandbox-record separation / disposal-safety | (PH-5/PH-7) |
| EG-PH5-10 | sandbox parts of `01M-AC-15,17` | task/tool quarantine is RPH3; sandbox/worktree is PH-5/6 |

**RPH3 must not claim proof** of process-tree termination, orphan prevention, sandbox quarantine, sandbox
recording separation, or evidence-before-disposal. `01M` snapshot/reserve criteria `01M-AC-24..29` are PH-7.
Full disposition table: TRACE-RPH3 §1–§3.

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
Watchdog observation + pause-on-control-loss → Safe-Mode no-autonomous-write → **every privileged action's
audit record is finalized before success is reported** (cross-store protocol, VR-RPH3-19). VM-2 PASS requires
every **VR-RPH3-01..20** at verdict `PASS` with a complete ETM chain and no unresolved critical/high defect.

## 6. Promotion gate — `PROM-RPH3`

`PROM-RPH3` (roadmap PH-3 exit; distinct from the substrate's `PROM-PH3`) is defined over **acceptance
criteria only** (`-AC-`), never decision-list numbers. It is satisfied when **all** hold:

1. Every **RPH3-scoped acceptance criterion** at verdict `PASS` — the `01M-AC-*` and `01K-AC-*` rows marked
   RPH3 in TRACE-RPH3 §1–§2 (the RPH3-scoped `01M-AC` set and the RPH3-verifiable `01K-AC` set). **The PH-5
   enforcement gates `EG-PH5-01..10` (VEP §2a) are explicitly EXCLUDED** — RPH3 proves only their request
   contract + fail-closed-when-no-executor, never their enforcement.
2. VM-2 security-spine integration path PASS (§5), including the cross-store audit-before-success invariant
   (VR-RPH3-19).
3. Decisions A and B proven (VR-RPH3-17 / VR-RPH3-18).
4. Audit append-only + break detection proven (VR-RPH3-14); Safe-Mode no-autonomous-write proven (VR-RPH3-06).
5. ≥95% branch coverage across `src/factory/{watchdog,permission,approval,audit,tools,fileops,diagnostics}`.
6. No unresolved critical/high defect; every REGR-* seeded during implementation cleared.
7. `01G §3.1` ETM chain complete for every VR-RPH3-01..20.
8. **Operator PH-3 exit approval** + authorization to begin `01B` Stage-2 cutover (`docs/10 §15`).

**`PROM-RPH3` does NOT certify** any `EG-PH5-*` enforcement property (process-tree termination, orphan
prevention, sandbox quarantine/recording/evidence, credential/network enforcement) — those are PH-5/PH-7
gates. Falsely certifying them was defect **D5**; this gate now excludes them by construction.

**Not required by `PROM-RPH3` (external):** the four PR #10 substrate blockers (XIB-01..04, PLAN-S3 §7) are
prerequisites for any PR #10 *merge*, owned by a dedicated PR #10 correction / PH-5 — independent of this gate.

## 7. Traceability summary

**20 VR rows** → 9 components → 5 tasks; every RPH3-scoped `01M-AC-*`/`01K-AC-*` acceptance criterion + Dec A/B
covered with authoritative identifiers (TRACE-RPH3); PH-5 enforcement gates `EG-PH5-01..10` excluded from
`PROM-RPH3`; cross-store audit-before-success is VR-RPH3-19; VM-2 path complete. Non-blocking: the ETM engine
proper (`CTR-ETM`) is PH-7 (here the manifest is a static table).
