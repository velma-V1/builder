# Roadmap PH-3 (RPH3) Component Integration Review

**Instance authority:** L25.1 planning record · **Phase:** roadmap PH-3 (Watchdog security spine) · **Scope:**
the nine roadmap-PH-3 components (CMP-WATCH, CMP-PERM, CMP-APPROVAL, CMP-AUDITW, CMP-AUDITV, CMP-TOOLREG,
CMP-TOOLGW, CMP-DIAG[Safe Mode], CMP-FILEOP). **This is roadmap PH-3, NOT the Worker Execution Substrate**
(`CMP-WORKER`, out-of-roadmap; `docs/WORKER-EXECUTION-SUBSTRATE-CLASSIFICATION.md`). System-wide graphs remain
owned by `docs/planning/DEPENDENCY-MAP.md` / `WORKSTREAM-MAP.md`; this holds only the intra-RPH3 matrices.

## 1. Component interaction map

```
        CMP-WATCH (Lane A: independent read-only OS process, R1) ── observes ──► CMP-ORCH (read-only reader)
             │ 7 narrow interventions (journaled via ORCH, audited via AUDITW)      │
             ▼                                                                       │
        ┌──────────────────────────── Lane B: security spine ────────────────────────────┐
        │  CMP-AUDITW (sole audit-chain writer) ◄── every privileged action appends here  │
        │        ▲            ▲            ▲              ▲               ▲                 │
        │        │            │            │              │               │                │
        │   CMP-PERM ──► CMP-APPROVAL   CMP-TOOLREG   CMP-TOOLGW      CMP-FILEOP           │
        │   (grants,      (cards for    (default-     (single tool-   (safe paths,         │
        │    Dec A/B)      delete/dest.) deny reg.)    call path)      delete=Dec B)        │
        │        └────── deletion/destructive/external route to CMP-APPROVAL ──────┘        │
        │   CMP-AUDITV verifies CMP-AUDITW chain ──► raises break events ──► CMP-WATCH       │
        │   CMP-DIAG (Safe Mode) uses PERM+APPROVAL+AUDITW for approved repair only          │
        └───────────────────────────────────────────────────────────────────────────────────┘
```

## 2. Interface matrix

| Consumer → Provider | Interface used |
|---|---|
| CMP-WATCH → CMP-ORCH | read-only reader (`get_task`/`get_events`); interventions applied via ORCH tx |
| CMP-WATCH → CMP-AUDITW | `AuditWriter.append` (every intervention) |
| CMP-PERM → CMP-APPROVAL | `ApprovalEngine.enqueue` (deletion/destructive/external/out-of-envelope) |
| CMP-PERM → CMP-AUDITW | `AuditWriter.append` (decisions/grants/denials) |
| CMP-APPROVAL → CMP-ORCH | read-only reader for task context (records persist in the PH-3 security-spine store, ODI-RPH3-01) |
| CMP-TOOLGW → CMP-TOOLREG | `ToolRegistry.lookup` (default-deny on miss) |
| CMP-TOOLGW → CMP-PERM | `PermissionEngine.revalidate` (TOCTOU at call time) |
| CMP-TOOLGW → CMP-FILEOP | file-touching actions routed to the safe file-op service |
| CMP-FILEOP → CMP-PERM / CMP-APPROVAL | path authority + grant; delete requires approval (Dec B) |
| CMP-AUDITV → CMP-AUDITW | reads chain/exports; verifies integrity |
| CMP-AUDITV → CMP-WATCH | integrity/security event on a detected break |
| CMP-DIAG → CMP-PERM/APPROVAL/AUDITW | permission + approval + audit for every repair |

## 3. Dependency matrix (intra-RPH3, acyclic)

| Component | Depends on |
|---|---|
| CMP-AUDITW | CMP-SCHEMA (migration runner for `migrations/audit/0001_audit_chain.sql`) — separate audit store; CMP-AUDITW is its **sole** writer (durable append in the audit store, **not** via CMP-ORCH) |
| CMP-AUDITV | CMP-AUDITW |
| CMP-PERM | CMP-ORCH, CMP-APPROVAL, CMP-AUDITW |
| CMP-APPROVAL | CMP-ORCH, CMP-AUDITW |
| CMP-TOOLREG | CMP-SCHEMA, CMP-PERM, CMP-AUDITW |
| CMP-FILEOP | CMP-PERM, CMP-APPROVAL, CMP-AUDITW |
| CMP-TOOLGW | CMP-TOOLREG, CMP-PERM, CMP-FILEOP, CMP-AUDITW |
| CMP-DIAG (Safe Mode) | CMP-PERM, CMP-APPROVAL, CMP-AUDITW, CMP-AUDITV, CMP-JOURNAL |
| CMP-WATCH | CMP-ORCH (ro), CMP-JOURNAL, CMP-AUDITW; CMP-SNAP (PH-7, forward-bound) |

Cycle check: CMP-PERM ↔ CMP-APPROVAL is a *runtime call* pair, not a build cycle — build order breaks it
(AUDITW → APPROVAL → PERM). Topological build order below is **acyclic**. The only forward reference is
CMP-WATCH → CMP-SNAP (PH-7), inert until PH-7 exists (bounded, not a cycle).

## 4. Ownership matrix (single owner per responsibility)

| Responsibility | Single owner | Note |
|---|---|---|
| Tamper-evident audit chain (sole audit writer) | CMP-AUDITW | single-audit-writer (R1-analogue for audit) |
| Audit-chain integrity verification | CMP-AUDITV | read-only; never repairs |
| Least-privilege decisions + path authority + Dec A/B enforcement | CMP-PERM | owns CTR-PERMISSION-GRANT |
| Approval queue + cards (bound/expiring/revocable) | CMP-APPROVAL | owns CTR-APPROVAL-RECORD |
| Approved-tool registry (default-deny) + quarantine | CMP-TOOLREG | owns CTR-TOOL-DECLARATION |
| Single tool-call path + output validation + resource/process-tree control | CMP-TOOLGW | no-bypass invariant |
| Safe file operations + escape blocking + deletion approval-gating | CMP-FILEOP | added #40 this pass |
| Restricted Safe Mode (no autonomous writes) | CMP-DIAG (PH-3 scope) | full diagnostics = PH-8 |
| Independent read-only supervision + 7 interventions | CMP-WATCH | holds no writable authoritative connection |

**No duplicate ownership:** the audit *chain* is owned by CMP-AUDITW; its *verification* by CMP-AUDITV;
neither writes runtime state (that stays CMP-ORCH, R1). CMP-DIAG here is the PH-3 Safe Mode slice only.

## 5. State / store-ownership matrix

Per ODI-RPH3-01 (resolved DEP-RPH3 §): PH-3 records live in **PH-3-owned stores separate from the
runtime-state DB** (which stays Orchestrator-only, R1). Each store has a single writer per domain.

| Store | Written by (sole) | Read by |
|---|---|---|
| audit store (`migrations/audit/0001_audit_chain.sql`) | CMP-AUDITW | CMP-AUDITV, exporters, operator |
| security-spine store: permission grants (`migrations/security/0001_*`) | CMP-PERM | CMP-TOOLGW, CMP-FILEOP |
| security-spine store: approval queue + records | CMP-APPROVAL | CMP-PERM, CMP-TOOLGW, CMP-DIAG |
| security-spine store: tool registry + quarantine | CMP-TOOLREG | CMP-TOOLGW |
| runtime-state DB (PH-2) | CMP-ORCH only (R1; unmodified) | CMP-WATCH/CMP-DIAG read-only |
| (none) — Watchdog | — (read-only) | CMP-WATCH observes ORCH/journal |

## 6. Contract & schema usage matrix

| Component | Contracts | Schemas / migrations (authored RPH3 Pass 9) |
|---|---|---|
| CMP-PERM | CTR-PERMISSION-GRANT | `permission-grant` |
| CMP-APPROVAL | CTR-APPROVAL-RECORD | `approval-record` |
| CMP-TOOLREG | CTR-TOOL-DECLARATION | `tool-declaration` |
| CMP-AUDITW | CTR-AUDIT-RECORD | `audit-chain` (`migrations/audit/0001_audit_chain.sql`, **separate audit store**, SHA-pinned) |
| CMP-AUDITV / CMP-TOOLGW / CMP-FILEOP / CMP-DIAG / CMP-WATCH | (consume the above) | (none new) |

Security-spine tables (permission/approval/tool) live in `migrations/security/0001_security_spine.sql`. All
new schemas follow the PH-1 SHA-256-pinned transactional runner (`CTR-MIGRATION`) in **separate PH-3 stores**;
the frozen PH-2 runtime migrations (`0001–0003`) are unchanged and no runtime `0004_*` is added (DEP-RPH3 §2–3).

## 7. Failure / recovery / rollback dependency map

- **Fail-closed core controls:** failure of permission, approval, audit, or state-authority fails the affected
  action closed (`01M §2.25`) — never degrades to allow/unaudited.
- **Recovery dependency:** audit-chain integrity (CMP-AUDITV) must verify before audit is trusted; CMP-WATCH
  reconciled-resume depends on CMP-JOURNAL; no blind resume.
- **Rollback boundary (roadmap §PH-3):** the Watchdog holds no writable state; permission/approval decisions
  are reversible/expiring; the audit chain is append-only (rollback = "the append transaction did not commit").

## 8. Security / trust boundary map

- **Trust boundary:** tool output, submitted declarations, requested actions, and every raw path are untrusted
  until validated; repository/downloaded instructions are data, not commands (`01K §2.28`).
- **Security boundary (core controls):** default-deny tool gateway, single audit writer + break detection,
  least-privilege + TOCTOU, deletion approval-gating (Dec B), autonomy envelope (Dec A), Safe-Mode
  no-autonomous-write. Violating any fails closed. VM-2 (security spine) is the integration gate.

## 9. Integration order (build/verify sequence within roadmap PH-3)

Lane B (serialized, shared spine): CMP-AUDITW → CMP-AUDITV → CMP-APPROVAL → CMP-PERM → CMP-TOOLREG →
CMP-FILEOP → CMP-TOOLGW → CMP-DIAG(Safe Mode). Lane A (parallel, independent process): CMP-WATCH. This
dependency-correct order refines the section-3 stub's numeric task order (3.1 Watchdog…3.5 tools); the
authoritative task-execution graph is finalized in PLAN-S3 (RPH3 Pass 5). Phase-exit gate: `PROM-RPH3` =
`01M`(32)+`01K`(25) PASS + VM-2 + operator approval to begin `01B` Stage-2 cutover.

## 10. Implementation validation (this pass)

Every RPH3 component is buildable (all dependencies resolve to PH-1/PH-2 implemented components or earlier
RPH3 tasks; the sole forward reference CMP-WATCH → CMP-SNAP is PH-7 and inert until then); every interface is
defined in a component spec; every owned contract exists in `CONTRACT-REGISTRY` (v1); every new schema is
scheduled in PLAN-S3/RPH3 Pass 9; every verification path is a named acceptance set (`01M` 32 / `01K` 25);
every rollback path is defined (Watchdog stateless / permission-approval reversible / audit append-only); no
orphan/unreachable component; no undocumented interaction; identifiers are disjoint from the substrate
(PAL §9.1; WES-CLASS §3/§4). **Result: PASS (with the non-blocking CMP-FILEOP map addition recorded).**
