# Roadmap PH-3 (Section 3) — Watchdog, Permissions, Approval, Audit & Tools — Implementation Plan

**Document ID:** PLAN-S3 · **Status:** Executable planning order (L25.1) · **Last expanded:** 2026-07-26
(RPH3 Pass 5). **Governing:** `01M` (32 acceptance criteria), `01K` (25 acceptance criteria), `01 §3/§11`,
`01R` R1 / Dec A / Dec B. Roadmap spec: `docs/10 §PH-3`; execution env: `docs/10A §3/§3A`. Component specs +
integration: `docs/specifications/components/{watchdog,permission,approval,audit-writer,audit-validator,tool-registry,tool-gateway,safe-mode,file-op-service}-spec.md`, `docs/specifications/components/RPH3-INTEGRATION.md`.

**Identifier namespace:** roadmap PH-3 uses **`RPH3`** (PAL §9.1). This plan does **not** reuse the Worker
Execution Substrate labels `T3.x` / `SEC-PH3-*` / `PROM-PH3` / `WES-*` / vacated `PH3-*` names.

**R1:** the Watchdog is a **separate, independently supervised, normally read-only** process — not the state
writer. **Decision A** (autonomy envelope) and **Decision B** (all file deletion approval-required) are
enforced here. This is roadmap PH-3 (the Watchdog security spine); it is **NOT** the Worker Execution
Substrate (`CMP-WORKER`; `docs/WORKER-EXECUTION-SUBSTRATE-CLASSIFICATION.md`).

## 1. Frozen inputs RPH3 consumes (and what it does not)

RPH3 builds **only** on the frozen PH-2 interfaces required by the approved dependency map
(`DEPENDENCY-MAP §2`: `permission/approval/audit ← Orchestrator`; `Watchdog ← Orchestrator (observes;
separate process), journal`) plus the PH-1 contract system:

| Consumed (frozen) | Interface | Consumer |
|---|---|---|
| CMP-ORCH (PH-2, R1) | `_OrchestratorStateWriter.apply_transition(...)` (state-affecting transitions incl. `AWAITING_APPROVAL`) | CMP-PERM, CMP-APPROVAL routing |
| CMP-ORCH (PH-2) | `SQLiteOrchestratorStateReader.get_task/get_events` (`mode=ro`) | CMP-WATCH, CMP-DIAG |
| CMP-JOURNAL (PH-2) | `reconcile_startup(reader, task_ids) -> ReconciliationOutcome` | CMP-WATCH, CMP-DIAG (no blind resume) |
| CMP-SCHEMA (PH-1) | SHA-256-pinned transactional migration runner | audit-chain / security-spine schemas (`0004_*`) |
| PH-1 contracts | validated Task/Permission/Ownership (`CTR-TASK` risk_class R5 + autonomy Dec A; `CTR-PERMISSION`; `CTR-OWNERSHIP`), read-only | CMP-PERM, CMP-APPROVAL |
| CTR-TASK-WS-SM (PH-2) | legal transition table (`AWAITING_APPROVAL`) | CMP-APPROVAL |

**Explicitly NOT consumed (Constraint 2):** the **Worker Execution Substrate** (`CMP-WORKER`,
`src/factory/workers/**`) is **not** an approved roadmap-PH-3 implementation dependency. No RPH3 task imports,
extends, or depends on the substrate. **CMP-LEASE** (PH-2 fenced leases) is an execution-phase dependency
(PH-4/5/6), not an RPH3 dependency. RPH3 does not assume PR #10 is merged, merge-ready, or production-ready
(Constraint 3), and does not repair substrate defects (Constraint 4; see §7).

**Open design item ODI-RPH3-01 (persistence boundary):** PH-3 authoritative records (permission grants,
approval records, tool registry) are persisted under the **single-writer discipline** R1 embodies. Whether
that is (a) an *additive* extension of the Orchestrator writer via a Change Contract (`01D §3.2`; no existing
PH-2 method modified) or (b) a PH-3-owned security-spine store with a dedicated single writer — is resolved in
RPH3 Pass 6/9. **Both preserve R1 and neither modifies frozen PH-2 code.** The **audit chain** is
unambiguously a *separate* append-only store with CMP-AUDITW as sole writer (tamper-evidence requires
independence). No RPH3 component writes the runtime-state DB directly (BASE-X).

## 2. Uniform execution context (applies to every RPH3 task; deltas per task)

From `docs/10A §3/§3A` PH-3 (RPH3) rows: **Plan branch** `claude/roadmap-ph3-security-spine-planning`;
product branch operator-assigned at the PH-3 entry gate. **Sandbox** WSL2+Docker (Dec C) for any executing
proof; pure-enforcement unit logic runs in ENV-DEV. **Models/Tools/GPU** none. **Permissions/Secrets/Network**
none / none / off (pure enforcement over the frozen PH-2 SQLite runtime; the secret broker + network broker
are **PH-5**, not RPH3). **Risk class** (`01M §3.11`): `medium` for T2/T3/T4/T5 (own security-critical
records), `medium` for T1 (supervisor). **Autonomy** (Dec A): enforced by CMP-PERM/CMP-APPROVAL. **Deletion**
(Dec B): approval-required everywhere; no auto-delete in code or tests. **Coverage:** ≥95% branch coverage for
every `src/factory/{watchdog,permission,approval,audit,tools,fileops,diagnostics}` module (PH-1/PH-2
precedent). **Tech stack:** Python 3.12, uv, stdlib `sqlite3`, pytest, hypothesis, mypy, ruff (PH-1 pins).
**Environment:** ENV-DEV; native Windows 11 Home execution of OS-specific Watchdog/process-tree behavior is a
recorded known limitation, re-verified at release (PH-8), as in PH-1/PH-2.

## 3. Locked file map (expected create/modify)

```text
migrations/runtime/0004_security_spine.sql        # permission_grants, approval_records, tool_registry, tool_quarantine (layout finalized Pass 9)
migrations/audit/0001_audit_chain.sql             # separate append-only audit store (CMP-AUDITW sole writer)
src/factory/audit/{__init__,models,errors,writer,validator}.py
src/factory/approval/{__init__,models,engine,cards}.py
src/factory/permission/{__init__,models,engine,path_authority,autonomy}.py
src/factory/tools/{__init__,models,registry,gateway,resource_limits}.py
src/factory/fileops/{__init__,service,paths}.py
src/factory/diagnostics/safe_mode/{__init__,mode}.py
src/factory/watchdog/{__init__,models,process,heartbeat,thresholds,control,interventions}.py
scripts/verify_roadmap_ph3.py
tests/audit/**  tests/approval/**  tests/permission/**  tests/tools/**  tests/fileops/**
tests/diagnostics/**  tests/watchdog/**
docs/verification/roadmap-ph3-evidence-report.md   # authored during implementation (architecture: VEP-RPH3, Pass 6)
```

Public interface signatures are **owned by the component specs** (single authority); this plan owns the build
procedure and does not restate the dataclass field sets or method bodies. Interface change = Change Contract +
consumer-impact (`01D §3.2`).

---

## Task RPH3-T1 — Independent Watchdog process + narrow control interface (CMP-WATCH) · **Lane A**

- **Scope:** `src/factory/watchdog/**` — separately supervised OS process/service; own monotonic heartbeat +
  event loop; staged thresholds (NORMAL/WARNING/PAUSE/CRITICAL_CONTAINMENT/REDUCED_MONITORING); the 7
  predefined interventions (`01M §3.2`). **Exclusions:** does not write authoritative state (R1); builds no
  permission/approval/audit engine (consumes their interfaces); `ACTIVATE_VERIFIED_SNAPSHOT` binds CMP-SNAP
  (**PH-7**) and ships inert here; no sandbox/model/network.
- **Owned components:** CMP-WATCH.
- **Prerequisites:** frozen CMP-ORCH read-only reader + CMP-JOURNAL `reconcile_startup` (PH-2). **Soft:** T4
  (CMP-AUDITW) for intervention-audit wiring — built against the CMP-AUDITW interface contract, integrated
  when T4 lands.
- **Public interfaces:** `WatchdogControl.{PAUSE_TASK,CONTAIN_TASK,RESTART_SERVICE,RECONCILE_STATE,QUARANTINE_RESOURCE,RESTORE_APPROVED_STATE,ACTIVATE_VERIFIED_SNAPSHOT}`, `HeartbeatMonitor.observe` (see `watchdog-spec.md`).
- **Contracts/Schemas:** owns none; consumes CTR-RECOVERY-JOURNAL, CTR-AUDIT-RECORD. No new schema.
- **Files:** `watchdog/{process,heartbeat,thresholds,control,interventions,models,errors}.py`, `tests/watchdog/**`.
- **TDD order:** (1) heartbeat/stall unit tests (monotonic; wall-clock change cannot fabricate a stall) →
  (2) threshold-state machine + hysteresis + REDUCED_MONITORING on missing sensor → (3) separate-process
  detection of an unresponsive Orchestrator → (4) narrow-interface validation (only the 7 commands;
  arbitrary mutation rejected; cannot modify own authority) → (5) Watchdog-loss pauses/blocks high-risk work.
- **Tests:** *unit* heartbeat/threshold/timing; *integration* observes real CMP-ORCH reader + CMP-JOURNAL
  outcomes; *security* interface rejects arbitrary shell/DB/file/policy input, self-authority modification
  rejected (fail closed); *adversarial* forged heartbeat / wall-clock rollback / intervention-flood; *failure
  -path* Watchdog-loss simulation (RM-1), Orchestrator event-loop stall; *regression* none seeded (new).
  Maps **`01M` #1-8, #21, #22, #30, #31, #32**.
- **Evidence:** Watchdog ETM rows (VM-2/RM-1) → `roadmap-ph3-evidence-report.md`.
- **Rollback boundary:** Watchdog holds **no** writable state; `git revert` the task commit; no state to unwind.
- **Stop conditions:** any arbitrary-mutation path accepted; self-authority modification possible; stall
  detection depends on wall-clock; Watchdog-loss does not pause high-risk work → **stop, fix, re-run**.
- **Completion gate:** `01M` Watchdog acceptance subset PASS; ruff/mypy clean; committed.
- **Prior-RPH3 dependency:** none blocking (Lane A); **soft** T4 for audit wiring.
- **Lane:** **A** — independent supervisor process; parallelism proven for observation/detection (needs only
  frozen PH-2 read interfaces). The audit-emitting interventions soft-serialize behind T4.

## Task RPH3-T4 — Tamper-evident audit writer + chain validator (CMP-AUDITW, CMP-AUDITV) · **Lane B (built first)**

- **Scope:** `src/factory/audit/**` — append-only hash-chained audit **writer** (sole audit writer;
  sequence + predecessor identity; optional signing) and independent **validator** (startup/export/recovery/
  release integrity; detects deletion/truncation/reorder/rewrite/invalid-anchor). **Exclusions:** no
  UPDATE/DELETE path; validator never repairs; does not decide permissions/approvals.
- **Owned components:** CMP-AUDITW, CMP-AUDITV.
- **Prerequisites:** CMP-SCHEMA migration-runner pattern (PH-1); durable-append boundary (ODI-RPH3-01, audit
  chain = separate store).
- **Public interfaces:** `AuditWriter.{append,head,export}`, `AuditValidator.{verify_chain,verify_export,classify_break}`.
- **Contracts/Schemas:** owns **CTR-AUDIT-RECORD**; schema `audit-chain` (`migrations/audit/0001_audit_chain.sql`, SHA-pinned).
- **Files:** `audit/{writer,validator,models,errors}.py`, `migrations/audit/0001_audit_chain.sql`, `tests/audit/**`.
- **TDD order:** (1) append-only + hash-chain unit tests (sequence = prev+1; predecessor hash) → (2) durability
  (record flushed before the audited action reports success) → (3) validator detects each break class →
  (4) concurrency (two appends on one head: one wins, other retries; no fork/gap) → (5) forge-resistance
  (caller cannot set sequence/predecessor/hash).
- **Tests:** *unit* chain link + sequence; *integration* writer→validator round-trip + export; *security* no
  UPDATE/DELETE path exists, caller cannot forge identity fields; *adversarial* mid-chain deletion, tail
  truncation, reorder, rewrite, invalid anchor; *failure-path* mid-append rollback leaves chain unchanged,
  audit unavailable → privileged action fails closed; *regression* none seeded. Maps **`01K` #19, #20**.
- **Evidence:** audit-integrity ETM rows → evidence report.
- **Rollback boundary:** append-only chain (rollback = "the append transaction did not commit"); `git revert`;
  the separate audit store is disposable in dev (gitignored) but authoritative in product.
- **Stop conditions:** any update/delete path exists; a break class is undetected; a privileged action can
  proceed unaudited → **stop, fix, re-run**.
- **Completion gate:** `01K` #19/#20 PASS; single-audit-writer invariant proven; committed.
- **Prior-RPH3 dependency:** none (Lane B root). **Lane:** **B**.

## Task RPH3-T3 — Approval engine + central queue + complete cards (CMP-APPROVAL) · **Lane B**

- **Scope:** `src/factory/approval/**` — central queue; bound/expiring/revocable approvals; complete cards
  (full `01L §3.2` scope + autonomy level); separate confirmation for destructive/external actions; security
  violations denied+audited, never offered as approvals. **Exclusions:** does not compute permission decisions
  (CMP-PERM) or execute actions (CMP-TOOLGW/CMP-FILEOP).
- **Owned components:** CMP-APPROVAL.
- **Prerequisites:** T4 (CMP-AUDITW, every decision audited); frozen CMP-ORCH transaction boundary (queue +
  records persisted under single-writer discipline, ODI-RPH3-01); CTR-TASK-WS-SM `AWAITING_APPROVAL`.
- **Public interfaces:** `ApprovalEngine.{enqueue,decide,consume,revoke,is_valid}`.
- **Contracts/Schemas:** owns **CTR-APPROVAL-RECORD**; schema `approval-record`.
- **Files:** `approval/{engine,cards,models}.py`, `tests/approval/**`.
- **TDD order:** (1) card-completeness unit (every `01L §3.2` field + autonomy + consequences) → (2) scope
  binding (task/action/path/scope) → (3) expiry (write/exec auto-expire) → (4) repetition (bounded batch
  consumed ≤ count) → (5) no-reuse (consumed/expired/revoked → invalid) → (6) security-violation request
  denied+audited, never queued.
- **Tests:** *unit* card completeness, is_valid; *integration* enqueue→decide→consume with CMP-AUDITW +
  frozen ORCH persistence; *security* no reusable/permanent/unbounded approval; a security violation is never
  an approvable card (`01K` acceptance); *adversarial* replay outside scope, expired reuse, repetition
  overflow, forged fingerprint; *failure-path* restart leaves pending un-granted, unexpired revalidated;
  *regression* none. Maps **`01K` #3, #4, #5**; **Dec A** (card autonomy-level display); **Dec B** (deletion
  cards carry consequence + separate confirmation).
- **Evidence:** approval ETM rows.
- **Rollback boundary:** approvals reversible/expiring; `git revert`; records via single-writer discipline.
- **Stop conditions:** any reusable/non-expiring approval; a security violation offered as a card; a card
  missing `01L §3.2` scope → **stop, fix, re-run**.
- **Completion gate:** `01K` approval acceptance PASS; Dec A/B card behavior proven; committed.
- **Prior-RPH3 dependency:** **T4**. **Lane:** **B**.

## Task RPH3-T2 — Permission enforcement + path authority + Dec A/B (CMP-PERM) · **Lane B**

- **Scope:** `src/factory/permission/**` — least-privilege decisions; scoped/expiring runtime grants; TOCTOU
  pre-use revalidation; path canonicalization + escape classification (delegated ops in CMP-FILEOP); **Dec B**
  (all deletion approval-required) and **Dec A** (autonomy envelope scoping auto vs card). **Exclusions:** does
  not decide approvals (routes to CMP-APPROVAL), execute tools (CMP-TOOLGW), or perform file I/O (CMP-FILEOP).
- **Owned components:** CMP-PERM.
- **Prerequisites:** T3 (CMP-APPROVAL, deletion/destructive/out-of-envelope routing), T4 (CMP-AUDITW); frozen
  PH-1 Task/Permission/Ownership contracts + CTR-TASK autonomy level.
- **Public interfaces:** `PermissionEngine.{decide,issue_grant,revalidate}`, `PathAuthority.canonicalize`, `AutonomyEnvelope.classify`.
- **Contracts/Schemas:** owns **CTR-PERMISSION-GRANT**; schema `permission-grant`.
- **Files:** `permission/{engine,path_authority,autonomy,models}.py`, `tests/permission/**`.
- **TDD order:** (1) least-privilege decide unit (grant ≤ task approval) → (2) permission-class matrix
  (read/write/execute/network/credential/promotion/privileged/external-action/destructive) → (3) Dec B: every
  deletion → requires-approval (no auto-delete path) → (4) Dec A: autonomy level gates auto vs card →
  (5) TOCTOU revalidation rejects a stale grant → (6) path canonicalization → escape classes rejected.
- **Tests:** *unit* decision + grant scope; *integration* deletion → CMP-APPROVAL card → CMP-FILEOP delete;
  *security* grant cannot exceed task approval (`01K` #2), no permanent unrestricted (`01K` #4), instructions
  cannot widen a grant (`01K` #12); *adversarial* TOCTOU race, autonomy-boundary bypass attempt, symlink/
  junction/reserved/traversal/case/archive escape (`01K` #10); *failure-path* unexpired grant revalidated on
  restart, unknown grant → deny; *regression* none. Maps **`01K` #2, #4, #10, #12**; **Dec A**; **Dec B**.
- **Evidence:** permission ETM rows.
- **Rollback boundary:** grants reversible/expiring; `git revert`.
- **Stop conditions:** a deletion auto-allowed (Dec B breach); an out-of-envelope action auto-run (Dec A
  breach); a grant exceeds task approval; any escape class passes → **stop, fix, re-run**.
- **Completion gate:** `01K` permission + path-safety PASS; Dec A/B proven; committed.
- **Prior-RPH3 dependency:** **T3, T4**. **Lane:** **B**.

## Task RPH3-T5 — Tool registry + gateway + safe file-op + Safe Mode (CMP-TOOLREG, CMP-FILEOP, CMP-TOOLGW, CMP-DIAG) · **Lane B (built last)**

- **Scope:** `src/factory/{tools,fileops,diagnostics/safe_mode}/**` — default-deny **tool registry** + complete
  declarations + provenance + quarantine; single **tool gateway** (schema-validates output; resource +
  process-tree control; no bypass); safe **file-op service** (path authority, escape blocking, Dec B
  deletion-gating, archive limits); restricted **Safe Mode** (no autonomous writes). **Exclusions
  (Constraint 7):** does **not** implement a process spawner or sandbox (that is **PH-5**); does **not** build
  the secret broker / network broker (**PH-5**) or the router (**PH-4**). The gateway enforces the resource/
  process-tree/no-bypass **contract** at the execution seam; the real spawner is PH-5's.
- **Owned components:** CMP-TOOLREG, CMP-FILEOP, CMP-TOOLGW, CMP-DIAG (Safe Mode, PH-3 scope).
- **Prerequisites:** T2 (CMP-PERM grants + path authority), T3 (CMP-APPROVAL for delete/destructive), T4
  (CMP-AUDITW). Internal order: **CMP-TOOLREG → CMP-FILEOP → CMP-TOOLGW → CMP-DIAG**.
- **Public interfaces:** `ToolRegistry.{register,lookup,quarantine,release}`; `FileOpService.{canonicalize,read,write_atomic,delete,extract_archive}`; `ToolGateway.{invoke,validate_output,enforce_limits,terminate_tree}`; `SafeMode.{enter,inspect,export_evidence,approved_repair}`.
- **Contracts/Schemas:** owns **CTR-TOOL-DECLARATION**; schema `tool-declaration`. CMP-FILEOP/TOOLGW/DIAG own none (consume PERMISSION-GRANT/APPROVAL-RECORD/AUDIT-RECORD).
- **Files:** `tools/{registry,gateway,resource_limits,models}.py`, `fileops/{service,paths}.py`, `diagnostics/safe_mode/mode.py`, `tests/{tools,fileops,diagnostics}/**`.
- **TDD order:** (a) registry default-deny + complete-declaration + provenance + version-pin + quarantine →
  (b) file-op canonicalize/escape-block, Dec B delete-requires-approval, archive limits, atomic write →
  (c) gateway no-bypass + output schema-validation + resource limits + complete process-tree termination +
  limit-increase = permission change → (d) Safe Mode: inspection/export read-only, approved_repair requires a
  valid approval, no autonomous write, capability scope enforced.
- **Tests:** *unit* per component; *integration* register→gateway-invoke→(permission revalidate)→file-op→audit,
  full VM-2 spine path; *security* unregistered denied + no bypass (`01K` #1), Safe Mode no autonomous write
  (`01K` #22 / `01M` #20); *adversarial* gateway-bypass attempt, malformed/oversized/out-of-scope tool output,
  archive bomb (`01K` #11), path escape (`01K` #10), unapproved repair; *failure-path* resource-limit/idle/
  timeout breach → complete process-tree kill, no orphan (`01K` #14/#15), evidence preserved before disposal
  (`01K` #17), repeated failure → quarantine (`01K` #18); *regression* none. Maps **`01K` #1, #9, #10, #11,
  #13, #14, #15, #16, #17, #18, #22, #25**; **Dec B** (file-op delete-gating).
- **Evidence:** tool/security + Safe-Mode ETM rows → evidence report.
- **Rollback boundary:** registry/quarantine reversible; file-op atomic (no partial artifact); `git revert`.
- **Stop conditions:** any tool executes unregistered or bypasses the gateway; oversized/invalid output passed
  through; a deletion without approval; an orphan process survives termination; Safe Mode performs an
  autonomous write → **stop, fix, re-run**. (A discovered *substrate* execution defect is recorded as an
  external blocker per §7 — **not** fixed here, Constraint 4.)
- **Completion gate:** `01K` tool/file/Safe-Mode acceptance PASS; no-bypass + Dec B proven; committed.
- **Prior-RPH3 dependency:** **T2, T3, T4**. **Lane:** **B**.

## 4. Task execution graph

```
Lane A:  RPH3-T1 (CMP-WATCH) ─ observe/detect (frozen PH-2 read) ─────┐ soft-dep on T4 for
                                                                       │ intervention-audit wiring
Lane B:  RPH3-T4 ──► RPH3-T3 ──► RPH3-T2 ──► RPH3-T5 ─────────────────►┴──► VM-2 security-spine gate
        (AUDITW,AUDITV) (APPROVAL) (PERM)   (TOOLREG→FILEOP→TOOLGW→DIAG)      (PROM-RPH3)
```

- **Execution order:** Lane B serialized **T4 → T3 → T2 → T5** (dependency-correct build order from
  `RPH3-INTEGRATION §9`; **not** numeric order). Lane A **T1** runs in parallel; its audit-emitting
  interventions soft-serialize behind T4.
- **Critical path:** T4 → T3 → T2 → T5 → VM-2 gate.
- **Circular-call note (Constraint):** CMP-PERM↔CMP-APPROVAL is a *runtime call* pair, not a build cycle —
  build order **APPROVAL (T3) before PERM (T2)** breaks it (APPROVAL build-depends only on ORCH+AUDITW; PERM
  build-depends on APPROVAL+ORCH+AUDITW). A runtime call relationship is **not** treated as a build dependency.
- **Shared components:** CMP-AUDITW underlies T3/T2/T5 (every privileged action audits). **Shared contracts:**
  the four PH-3 contracts (one owner each). **Shared schemas:** `0004_*` + audit store. **Shared rollback:**
  per-task `git revert`; audit append-only; Watchdog stateless. **Shared failure domain:** the security-spine
  store + separate audit store.
- **Parallelism:** Lane A ∥ Lane B (max 2 workstreams, `docs/10A §3A`). Within Lane B, all tasks serialize
  (shared security-spine schema/state, `01D §3.4`).

## 5. Acceptance-criteria coverage map (`01M` 32 / `01K` 25 → task)

| Set | Task(s) | Notes |
|---|---|---|
| `01M` #1-8,#21,#22,#30,#31,#32 (Watchdog core) | **T1** | detection, interface, thresholds, sensors, triggers, audit, self-authority, Watchdog-loss, Windows auto-launch |
| `01M` #9-11 (bounded restart/backoff/circuit-breaker) | **T1** | RESTART_SERVICE intervention |
| `01M` #18,#19,#25 (idempotent recovery, fail-closed core controls) | **T1 + T2 + T4** | cross-cutting fail-closed |
| `01M` #20,#26 (restricted Safe Mode) | **T5 (CMP-DIAG)** | no autonomous execution |
| `01M` #13,#14,#17 (fencing, no-resume-before-reconcile, journal) | **PH-2 (satisfied)** | re-verified at VM-2 via frozen interfaces; **not** re-implemented |
| `01M` #15,#16,#23 (quarantine-first, startup integrity) | **T1** (Watchdog) + PH-2 reconcile | |
| `01M` #24,#27-29,#31 (snapshots, drills) | **PH-7 (deferred)** | `ACTIVATE_VERIFIED_SNAPSHOT` interface defined in T1, inert until CMP-SNAP |
| `01K` #1,#9 (default-deny, provenance) | **T5 (CMP-TOOLREG)** | |
| `01K` #2,#4,#10,#12 (least-priv, no-unrestricted, path, instruction-distrust) | **T2 (CMP-PERM)** | + CMP-FILEOP for path ops |
| `01K` #3,#4,#5 (approval binding/expiry/reuse, destructive confirmation) | **T3 (CMP-APPROVAL)** | |
| `01K` #11 (archive limits), #10 (escape) | **T5 (CMP-FILEOP)** | |
| `01K` #13,#14,#15,#16,#17,#25 (resource limits, process-tree, output validation) | **T5 (CMP-TOOLGW)** | seam contract; real spawner PH-5 |
| `01K` #18 (quarantine) | **T5 (CMP-TOOLREG)** | |
| `01K` #19,#20 (privileged audit, break detection) | **T4** | |
| `01K` #21 (emergency stop) | **T1** | |
| `01K` #22 (Safe Mode no autonomous write) | **T5 (CMP-DIAG)** | |
| `01K` #6 (no host shell/elevated) | **T5 seam** + **XIB-02 (external)** | RPH3 defines the seam contract; the host spawner fix is external |
| `01K` #7,#8,#23,#24 (credentials, network, sandbox-record separation) | **PH-5 (interface-defined only)** | RPH3 defines permission classes; brokers/sandbox are PH-5 — **not absorbed** (Constraint 7) |
| `01K` #25 (no telemetry) | **PH-1 config + cross** | governing default |

**Decisions:** **Dec A** (autonomy envelope) → T2 `AutonomyEnvelope.classify` + T3 card display. **Dec B** (all
deletion approval-required) → T2 decision + T3 card + T5 `FileOpService.delete(approval_ref)`. Both are
explicitly test-mapped in T2/T3/T5.

**VM-2 (security-spine) complete integration path:** register tool (TOOLREG) → gateway denies unregistered +
no bypass (TOOLGW) → permitted action needs a scoped grant (PERM) → deletion/out-of-envelope needs a complete
card (APPROVAL; Dec A/B) → file op canonicalized + delete-gated (FILEOP) → every privileged action appends to
the audit chain (AUDITW) → chain validated (AUDITV) → Watchdog observes + pauses/contains on control loss
(WATCH) → Safe Mode performs no autonomous write (DIAG). Gate = `PROM-RPH3` = `01M`(32)+`01K`(25) PASS + VM-2 +
operator approval to begin `01B` Stage-2 cutover.

## 6. Parallel execution review

| Question | Determination | Reason |
|---|---|---|
| May run in parallel | **Lane A (T1) ∥ Lane B** | T1 needs only frozen PH-2 read interfaces for observe/detect; independence proven for that surface |
| Must serialize | **Lane B: T4→T3→T2→T5** | shared security-spine schema/state + audit dependency (`01D §3.4`) |
| Soft synchronization | T1 intervention-audit ↔ T4 | Watchdog interventions audit via CMP-AUDITW; wire when T4 lands |
| Max concurrent workstreams | **2** | `docs/10A §3A` (Lane A + Lane B) |
| Exclusive execution | every security-spine write task | single-writer discipline (ODI-RPH3-01), R1 preserved |

## 7. External integration blockers (Worker Execution Substrate / PR #10 — NOT roadmap PH-3 work)

Recorded per operator Constraint 5. These are **Worker Execution Substrate defects**, owned by a **later
dedicated correction of PR #10** (the real spawner is **PH-5**). They are **not** assigned to any RPH3
component (Constraint 6), **not** RPH3 acceptance criteria, and RPH3 does **not** repair them (Constraint 4).
RPH3 may only *define the security interface downstream execution must satisfy* (Constraint 7); it never
implements or owns the substrate/PH-4/PH-5 fix. RPH3 does not assume PR #10 is merge-ready (Constraint 3).

| ID | Blocker (substrate) | Owning correction | RPH3 interface that *specifies* (does not fix) |
|---|---|---|---|
| **XIB-01** | Lease/fencing-token validation must be enforced **before** substrate state writes | PR #10 correction (substrate) over frozen **CMP-LEASE** (PH-2) | none — leases are PH-2/execution; RPH3 owns no lease logic. RPH3 audit (CMP-AUDITW) can *record* privileged writes but does not gate them. |
| **XIB-02** | The publicly exported host `SubprocessSpawner` must be removed/disabled/**fail-closed** until **PH-5** provides sandbox-backed execution | **PH-5** (real spawner) + interim PR #10 correction | CMP-TOOLGW defines the no-host-shell / sandbox-only / resource + process-tree **contract** (`01K` #6/#13/#14) any spawner must satisfy — RPH3 provides **no** spawner |
| **XIB-03** | An oversized output chunk must **fail closed**, not be silently clipped while reporting success | PR #10 correction (substrate streaming) | CMP-TOOLGW `validate_output` defines fail-closed on oversized/invalid output (`01K` #25) as the *expected* downstream behavior — the substrate must implement it |
| **XIB-04** | Leases must be released/invalidated on dispatch rollback, worker crash, cancellation, failure, and abnormal termination | PR #10 correction (substrate) over frozen CMP-LEASE | none — lease lifecycle is PH-2/execution; RPH3 owns no dispatch/lease path |

**Consequence for RPH3:** none of these gate any RPH3 task. PLAN-S3 builds only on frozen PH-2 (§1) and does
not import the substrate. If a substrate defect is encountered during RPH3 integration testing, it is logged
against the appropriate XIB and referred to the PR #10 correction — never silently fixed on this branch.

## 8. Pass-5 self-verification

- **Every component in exactly one task:** CMP-WATCH→T1 · CMP-AUDITW,CMP-AUDITV→T4 · CMP-APPROVAL→T3 ·
  CMP-PERM→T2 · CMP-TOOLREG,CMP-FILEOP,CMP-TOOLGW,CMP-DIAG→T5. **9 components, no duplication, no omission.**
- **`01M`(32) + `01K`(25) mapped:** §5 maps every criterion to a task, or marks it PH-2-satisfied /
  PH-5-interface-only / PH-7-deferred (with the RPH3 interface that defines it).
- **Dec A & Dec B explicitly mapped:** §5 (T2 classify + T3 card; T2 decision + T3 card + T5 delete-gate).
- **VM-2 complete integration path:** §5 (nine-component spine path to `PROM-RPH3`).
- **No PH-4/PH-5 responsibility absorbed:** T5 excludes spawner/sandbox/secret/network/router (§Task RPH3-T5,
  §5 `01K` #6/#7/#8/#23/#24); the four substrate blockers are external (§7).
- **Four PR #10 blockers external-only:** §7 (XIB-01..04, owned by a dedicated PR #10 correction / PH-5).
- **RPH3 namespace preserved:** no `T3.x`/`SEC-PH3-*`/`PROM-PH3`/`WES-*`/`PH3-*` reuse.

## 9. Acceptance & handoff

**Acceptance:** `01M`(32) + `01K`(25) PASS (VM-2 security spine) with `01G §3.1` ETM chains; autonomy envelope
(Dec A) and approval-gated deletion (Dec B) proven; audit append-only + break detection proven; Safe Mode
no-autonomous-write proven; ≥95% branch coverage. **Rollback boundary:** Watchdog holds no writable state;
permission/approval reversible; audit append-only; file-op atomic. **Promotion gate:** `PROM-RPH3` = the above
+ operator PH-3 exit approval + authorization to begin `01B` Stage-2 cutover. **Handoff → PH-4/PH-5:** both
consume the **frozen** RPH3 permission-enforcement + tool-gateway + audit interfaces (roadmap §11 ordering:
PH-4 may consume the substrate seam only after these RPH3 interfaces are frozen). The four substrate blockers
(§7) remain external prerequisites for any PR #10 merge, independent of RPH3.
