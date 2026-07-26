# Roadmap PH-3 — Implementation-Readiness Certificate (CERT-RPH3)

**Document ID:** CERT-RPH3 · **Repository path:** `docs/planning/RPH3-IMPLEMENTATION-READINESS-CERTIFICATE.md`
**Status:** Derived certification (RPH3 planning) · **Established:** 2026-07-26. **Governing:** the full RPH3
planning corpus + `01M`/`01K`/`01R`/`docs/10`. **Namespace:** RPH3.
**Current verdict: `RPH3_CERTIFIED_WITH_NONBLOCKING_GAPS` (v2)** — see §1 for the authoritative body and
§2 for the reproducible audit evidence (`docs/verification/rph3-planning-audit.md`).
**This certifies planning readiness only — NOT implementation authorization, NOT a merge authorization, and
NOT roadmap PH-3 completion.**

## 0. Supersession & correction history

- **v1 — commit `1d3b860` (SUPERSEDED, INVALID):** issued verdict `RPH3_CERTIFIED_WITH_NONBLOCKING_GAPS` for
  an **invalid planning state**; its audits A1–A12 failed to detect defect classes D1–D6. The v1 verdict is
  **withdrawn**. The full v1 body is retained, clearly marked INVALID, in
  `docs/planning/superseded/RPH3-CERT-v1-SUPERSEDED.md` (moved out of the main reading path; never edited in
  place).
- **Defects the v1 audits missed:** (D1) `01M`/`01K` acceptance criteria conflated with the separate approved-
  decision lists + ambiguous `#NN` refs; (D2) no crash-consistent cross-store protocol; (D3) undefined
  Watchdog intervention receiver + false claim that the frozen transition writer executes all interventions;
  (D4) stale migration/dependency contradictions; (D5) PH-5/PH-7 enforcement falsely certifiable by
  `PROM-RPH3`; (D6) no enforceable shared-store ownership. Review round 2 added: (D7) cross-store invariant
  self-contradiction (biconditional); (D8) missing protocol tables in the migration inventory; (D9) residual
  PH-5/PH-7 enforcement assigned to PH-3. Review round 3 added: (D10) `UNIQUE(op_key)` in the audit store made
  Class 3 impossible (it needs both an `INTENT` and a `COMPLETION` audit record); (D11) the audit report did
  not identify the final committed tree and recorded an unclean working tree.
- **v2 — this document (authoritative).** Repairs R1–R12 landed; the reproducible final audit
  (`docs/verification/rph3-planning-audit.md`, re-run against the clean committed tree) passes. There is **no**
  active `RPH3_PLANNING_REPAIR_REQUIRED` verdict — that was the interim state during repair and is now closed.

## 1. Certificate (authoritative)

Issued after the repair commits **R1–R12** and the repository-wide final audit (re-run against the clean
committed tree). Repair provenance: the invalid v1 verdict (commit `1d3b860`) is superseded (see §0; full v1
body in `docs/planning/superseded/RPH3-CERT-v1-SUPERSEDED.md`). This is the authoritative certificate.

### 1.1 Repair summary (defects → corrections)

| Defect | Correction | Artifact |
|---|---|---|
| D1 `01M`/`01K` AC/DEC conflation + ambiguous `#NN` | Authoritative `-AC`/`-DEC` mapping; corpus-wide identifier rewrite | TRACE-RPH3; VEP §2; PLAN-S3 §5; all specs (R2/R3b) |
| D2 no crash-consistent cross-store protocol | Write-ahead-intent + audit-as-commit-point protocol; every crash window; fail-closed | XSC-RPH3 (R3) |
| D3 undefined Watchdog receiver; false `apply_transition` claim | Receiver ownership, schemas, allowlist, INERT commands, no writable connection | WIR-RPH3 (R4); watchdog-spec; PLAN-S3 T1 |
| D4 stale migration/dependency contradictions | Separate PH-3 stores; audit not via CMP-ORCH; CMP-LEASE not consumed | R5 across RPH3-INTEGRATION, audit-writer, PLAN-S3, PAL, 10A |
| D5 PH-5 enforcement falsely certifiable | `EG-PH5-*`/`EG-PH7-*` gates excluded from `PROM-RPH3`; RPH3 keeps request contract + fail-closed-no-executor | TRACE-RPH3 §3; VEP §2a/§6 (R2/R10) |
| D6 unenforceable shared-store ownership | Private per-domain writers, SQLite authorizer, isolation tests | DEP-RPH3 §4A (R6) |
| D7 cross-store invariant self-contradiction (biconditional) | Replaced with 3 operation classes (reversible / frozen-PH-2 / external-irreversible) + INV-1..4; no fabricated rollback; `UNCERTAIN`→`QUARANTINED` | XSC-RPH3 §0/§3/§10a; WIR-RPH3 (R8) |
| D8 missing protocol tables in migration inventory | `*_intents` + `intervention_journal` tables; `op_key`/status/reconciliation/audit_seq columns; `UNIQUE(op_key, record_kind)`; indexes; retention; migration-order | DEP-RPH3 §3/§3.1/§4A (R9) |
| D9 residual PH-5/PH-7 enforcement assigned to PH-3 | Split `01M-AC-19`, `01K-AC-21`, `01M-AC-30` into RPH3 request/containment half + `EG-PH5-11/12`/`EG-PH7-01` enforcement half | TRACE-RPH3 §3; VEP VR-03/07/15 (R10) |
| D10 `UNIQUE(op_key)` made Class 3 impossible | Audit store now `UNIQUE(op_key, record_kind)`: ≤1 `INTENT` + ≤1 `COMPLETION` per op; Class-3 completion cannot precede intent; op-intent tables keep `op_key` unique | XSC-RPH3 §1/§2/§3/§6/§9; DEP-RPH3 §3/§3.1; SCHEMA-REGISTRY; audit-writer-spec (R12) |
| D11 audit report did not identify the final committed tree | Report re-run against the clean committed tree; now literally prints `Reviewed commit: 5a5e103…` (R12); C-check replaced with clean-tree + remote-head verification; totals updated w/ Class-3 audit-record check | `docs/verification/rph3-planning-audit.md` (R12/R13) |

### 1.2 Final-audit result (repository-wide sweeps)

**Reproducible audit report: `docs/verification/rph3-planning-audit.md`** (re-run against the clean committed
R12 tree). **30 automated checks — 30 PASS, 0 FAIL.** Two checks apply a documented context filter (a
"no `SEC-PH3-*`/`PROM-PH3` reuse" declaration; the D10 defect description naming the old `UNIQUE(op_key)`) so
they are not miscounted — the corpus uses `PROM-RPH3`/`SEC-RPH3-*` and `UNIQUE(op_key, record_kind)`.
Implementation files (`src/`,`tests/`,`scripts/`,`migrations/`) **untouched** across R1–R12 (docs-only).

Specifically proven by the final audit:
- every `01M-AC-01..32` and `01K-AC-01..25` mapped exactly and semantically in TRACE-RPH3;
- no decision-list number represented as an acceptance criterion (output validation → `01K-DEC-25`, not `01K-AC-25`);
- no nonexistent criterion cited (all AC ids within 32 / 25);
- every store write + audit interaction has a defined crash-consistent protocol (XSC-RPH3), audit-before-success;
- every Watchdog intervention has a real receiver + authority path (WIR-RPH3); no intervention is falsely
  routed through the PH-2 transition writer; unsupported commands are INERT (PH-5/PH-7);
- no PH-5/PH-7 enforcement is certified by `PROM-RPH3` (`EG-PH5-01..12` + `EG-PH7-01..03` excluded);
- the cross-store protocol defines **3 operation classes** (reversible / frozen-PH-2 / external-irreversible)
  and enforces **INV-1..INV-4**; no fabricated rollback; uncertain external outcomes → `UNCERTAIN`/`QUARANTINED`;
- the migration inventory contains every XSC/WIR structure (`*_intents`, `intervention_journal`, `op_key`,
  `UNIQUE(op_key, record_kind)`, status/reconciliation/audit_seq columns, indexes, retention, migration order);
- `01M-AC-19`, `01K-AC-21`, `01M-AC-30` are split — RPH3 request/containment half + PH-5/PH-7 enforcement half;
- no runtime `0004_*` contradiction; migration layout consistent (`migrations/security/0001`, `migrations/audit/0001`);
- no RPH3 document disagrees about CMP-LEASE consumption (not an RPH3 dependency);
- shared-store ownership is structurally enforceable (DEP-RPH3 §4A);
- roadmap unamended; PH-2 frozen; PR #10 untouched; implementation files untouched; branch clean + synced.

### 1.3 Corrected audits (expanded to catch the v1 defect classes)

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
| C14 | Cross-store protocol has 3 classes + INV-1..4; no fabricated rollback; `UNCERTAIN` state (D7) | PASS |
| C15 | Migration inventory covers `*_intents`/`intervention_journal`/`op_key`/`UNIQUE(op_key,record_kind)`/status+recon columns (D8) | PASS |
| C16 | `01M-AC-19`/`01K-AC-21`/`01M-AC-30` split into RPH3 + PH-5/PH-7 gates, no obligation dropped (D9) | PASS |
| C17 | Certificate header verdict = v2; no active REPAIR_REQUIRED; v1 in superseded doc; audit report exists | PASS |
| C18 | Audit store `UNIQUE(op_key, record_kind)`; Class 3 carries `INTENT`+`COMPLETION`; completion≮intent; no bare `UNIQUE(op_key)` asserted (D10) | PASS |
| C19 | Audit report reviews the clean **committed** tree and literally records `Reviewed commit: 5a5e103…` (R12, parent `971d49e`); clean-tree + remote-head verification replaces the old uncommitted-tree record (D11) | PASS |

Full reproducible evidence: `docs/verification/rph3-planning-audit.md` (**30/30 checks**).

### 1.4 Corrected verdict

**`RPH3_CERTIFIED_WITH_NONBLOCKING_GAPS` (v2).** The roadmap PH-3 implementation-planning package is complete,
internally consistent, and free of the D1–D11 defect classes. Non-blocking items (§6): PR #10 substrate
blockers XIB-01..04 (external); PH-7-deferred criteria `01M-AC-24..29`; PH-5/PH-7 enforcement gates
`EG-PH5-01..12` + `EG-PH7-01..03` (interface-defined here, enforced/certified in PH-5/PH-7). **This certifies
planning readiness only — NOT implementation authorization, NOT merge authorization, NOT PH-3 completion.**
Required operator action to proceed remains explicit authorization to begin roadmap PH-3 implementation
(first task RPH3-T4).
