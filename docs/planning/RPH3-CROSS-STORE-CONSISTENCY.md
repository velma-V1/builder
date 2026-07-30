# Roadmap PH-3 — Cross-Store Crash-Consistency Protocol (XSC-RPH3)

**Document ID:** XSC-RPH3 · **Repository path:** `docs/planning/RPH3-CROSS-STORE-CONSISTENCY.md`
**Status:** Active architecture plan (subordinate to `01M §3.6/§3.17`, `01K §3.2`, `01R` R1) · **Owner:** RPH3
planning (repair R3 → R8) · **Established:** 2026-07-26. **Namespace:** RPH3. Fixes defect **D2** and review
correction #1. Verifies VR-RPH3-19.

## 0. Enforceable invariants (replaces the earlier `authoritative ⟺ audited` biconditional)

The earlier biconditional was wrong for operations whose effect commits before its audit (a frozen PH-2
transition) or cannot be rolled back at all (a restart, a completed deletion, an external action). It is
replaced by four precise, enforceable invariants:

- **INV-1 (no premature success):** no operation reports success before its **completion audit** record is
  durable in the audit store.
- **INV-2 (no authority from pending):** no `PENDING` security-spine record grants any authority — readers
  honor **only** `COMMITTED` records.
- **INV-3 (reconcile before serving):** no work affected by an incomplete operation is served (resumed,
  authorized, or dispatched) until that operation is reconciled.
- **INV-4 (quarantine on uncertainty):** an external/irreversible operation whose outcome cannot be proven
  enters `UNCERTAIN` → `QUARANTINED`, never a silent success.

There is **no** window in which an operation is *reported successful* without a durable completion audit
(INV-1); and there is no window in which a `PENDING`/unproven effect *grants authority or is served* (INV-2/3).

## 1. The three stores

| Store | Owner / writer | Transaction scope |
|---|---|---|
| Runtime-state DB (frozen PH-2) | CMP-ORCH only (R1); PH-3 read-only + `apply_transition` calls | PH-2 `BEGIN IMMEDIATE`; durable journal (`01M-AC-12`) |
| Security-spine store (PH-3) | per-domain sole writer (CMP-PERM / CMP-APPROVAL / CMP-TOOLREG / WIR) | WAL; single-writer per table set (DEP-RPH3 §4A) |
| Audit store (PH-3) | CMP-AUDITW only | WAL; append-only hash chain; `record_kind ∈ {INTENT, COMPLETION}`; `UNIQUE(op_key, record_kind)` |

## 2. Operation identity & idempotency key

Every operation `OP` carries `op_id = (domain, verb, subject_ref, actor, causal_ref)` and idempotency key
`op_key = K = sha256(canonical(op_id) ‖ epoch)`. `K` is the **primary key of the operation-intent row**
(exactly one intent row per operation). In the **audit store**, an operation may have up to **two** records —
an `INTENT` and a `COMPLETION` — so audit uniqueness is **`UNIQUE(op_key, record_kind)`**, not `UNIQUE(op_key)`.

**Audit-record cardinality (per `op_key`):** **zero or one `INTENT`** record, **zero or one `COMPLETION`**
record. A second `INTENT` (or second `COMPLETION`) for the same `K` is rejected. **For Class 3, `COMPLETION`
cannot precede `INTENT`** (the pre-execution intent audit must be durable first). Class 1/2 write a single
`COMPLETION` audit record (their intent lives in the operation-intent table, not the audit store); **Class 3
writes both** an `INTENT` (before execution) and a `COMPLETION` (after) audit record.

## 3. Protocol classes

Every PH-3 cross-store operation is classified. Its class fixes its ordering and its reconciliation direction.

### Class 1 — Reversible security-store operation
*(grant issue, approval record/consume, tool registration/quarantine — a `PENDING` DB row that can be undone)*

`S1 durable intent (PENDING)` → `S2 domain mutation (still PENDING, non-authoritative)` →
`S3 completion audit (durable — the point after which success may be reported)` → `S4 mark COMMITTED (+audit_seq)`
→ report success. **Reconciliation:** audit **absent** ⇒ roll back the mutation, `ABORTED` (safe: it was never
authoritative, INV-2). Audit **present** ⇒ roll forward to `COMMITTED`.

### Class 2 — Frozen PH-2 task-state transition
*(WIR `PAUSE_TASK`, `CONTAIN_TASK`, task-`RECONCILE_STATE`, task-`QUARANTINE_RESOURCE` — a durable transition
via `apply_transition` that cannot be half-applied)*

`S1 durable intent (WIR journal)` → `S2 apply_transition` *(PH-2 durable via its journal, `01M-AC-12`; targets
are **conservative containment states** — PAUSED/STOPPING/QUARANTINED — so a durable-but-not-yet-audited
transition is **safe**)* → `S3 completion audit (durable)` → `S4 mark COMMITTED`. **The intervention is not
reported `APPLIED` until S3 (INV-1); the affected task is not served/resumed until reconciliation completes
(INV-3).** **Reconciliation is always roll-forward:** the PH-2 transition is legal + journaled, so the
reconciler finalizes the completion audit (it never undoes a committed PH-2 transition). This does **not**
violate any invariant: no success was reported (INV-1) and no affected work is served before reconcile (INV-3).

### Class 3 — External / irreversible effect
*(WIR `RESTART_SERVICE`; a **termination** the executor actually performs; `CMP-FILEOP` delete/atomic-write; any
**communication** or **external side effect**; any future external action — effects that **cannot be rolled
back** and whose completion **cannot be un-done by writing to a store**. Note: process-tree **termination
enforcement** itself is PH-5, not RPH3; when RPH3 *issues* a termination request that reaches an executor, the
request is treated as Class 3.)*

`S1 durable AUDIT INTENT (before execution)` *(CMP-AUDITW appends an audit record with `record_kind = INTENT`
for `K` — a distinct row from the later completion, allowed by `UNIQUE(op_key, record_kind)` — so a record of
the attempt exists even across a crash)* → `S2 execute the external/irreversible effect` →
`S3 completion audit (durable, `record_kind = COMPLETION`, records proven outcome; rejected if no INTENT for
`K` exists)` → `S4 mark COMMITTED`. **Reconciliation:** if an `INTENT` audit exists for `K` but no
`COMPLETION` audit, the outcome is **unproven** → the affected
subject/resource enters `UNCERTAIN` → `QUARANTINED` (INV-4); it is never reported successful (INV-1) and never
silently retried against an unknown side effect. A proven-idempotent Class-3 op (e.g. delete of an
already-absent path) may be safely re-driven; otherwise operator/approval-gated recovery.

## 4. Crash windows (per class)

| Class | Crash point | On restart | Action |
|---|---|---|---|
| 1 | before S3 (no completion audit) | mutation `PENDING`, no audit | **roll back → ABORTED** (never authoritative; INV-2) |
| 1 | after S3, before S4 | completion audit present, `PENDING` | **roll forward → COMMITTED** |
| 2 | after `apply_transition`, before S3 | task in a containment state, no completion audit | **roll forward**: finalize completion audit; task **stays contained**, not served until reconcile (INV-3); success not reported (INV-1) |
| 2 | after S3, before S4 | audit present, `PENDING` marker | roll forward → COMMITTED |
| 3 | after S1 intent, before/mid S2 | audit `intent` present, effect unproven | **UNCERTAIN → QUARANTINED** (INV-4); operator/approval recovery |
| 3 | after S2, before S3 | effect done, no completion audit | **UNCERTAIN → QUARANTINED** unless the op is proven-idempotent (then re-drive) |
| any | after S4 | `COMMITTED` + completion audit | no-op |

## 5. Startup reconciliation

Before serving any request: (1) `CMP-AUDITV` verifies the audit chain (invalid ⇒ audit non-authoritative ⇒
Safe Mode / fail closed — no roll-forward against an invalid chain). (2) For each `PENDING` intent joined by
`K`: **Class 1** → audit-present roll-forward else roll-back; **Class 2** → roll-forward (finalize audit),
keep the task contained until done, no blind resume (`01M-AC-14`); **Class 3** → completion-audit-present
roll-forward, else `QUARANTINED` (INV-4). (3) No affected work is served until its incomplete operation
reconciles (INV-3). (4) Reconciliation uses the PH-2 `reconcile_startup` outcome for task-coupled operations.

## 6. Duplicate replay

All steps idempotent on `K`: the operation-intent insert is unique-on-`K`; audit append is
`UNIQUE(op_key, record_kind)` — at most one `INTENT` and one `COMPLETION` per `K`, so a **second `INTENT`** (or
a **second `COMPLETION`**) for `K` is rejected while the `INTENT`+`COMPLETION` pair is allowed; status set is
monotonic. Result: **exactly-once effect for Class 1/2**; Class 3 gets
**at-most-once execution** guarded by the pre-execution audit intent (a duplicate that finds an `intent` for
`K` without a completion audit does not re-execute — it reconciles to QUARANTINED unless proven idempotent).

## 7. Authoritative status while incomplete

A `PENDING` grant/approval/registration is **not** honored by any reader (CMP-TOOLGW/CMP-FILEOP/CMP-PERM) — a
grant is usable only `COMMITTED`, an approval consumable only `COMMITTED`, a tool callable only `COMMITTED`
(INV-2). A Class-2 contained task is not resumed until reconcile (INV-3). A Class-3 `QUARANTINED` subject is
not used until operator/approval recovery.

## 8. Fail-closed behavior

- Audit store unavailable / append fails → the operation **fails closed**: Class 1 stays `PENDING`→ABORTED;
  Class 2 does not report APPLIED (task remains contained); Class 3 does not execute (S1 intent never durable
  ⇒ no execution) or, if it already executed, → QUARANTINED.
- Audit chain invalid (CMP-AUDITV) → no roll-forward; Safe Mode / fail closed.
- Any core-store write failure → `BLOCKED`/`QUARANTINED`, never silent success.

## 9. Tests & evidence (VR-RPH3-19)

- *integration* — Class 1 happy path: one COMMITTED record + one `COMPLETION` audit joined by `K`; Class 2:
  transition + `COMPLETION` audit, task not served until reconcile; **Class 3: exactly one `INTENT` audit +
  one `COMPLETION` audit for `K` (two rows, `UNIQUE(op_key, record_kind)`), `INTENT` durable before execution
  and before `COMPLETION`**.
- *cardinality* — `UNIQUE(op_key, record_kind)` admits an `INTENT`+`COMPLETION` pair but **rejects a second
  `INTENT`** and **a second `COMPLETION`** for the same `K`; a `COMPLETION` with no prior `INTENT` for a
  Class-3 op is rejected.
- *failure-path (fault injection per window, per class)* — Class 1 pre-audit → ABORTED, no authority granted,
  **no success reported**; Class 2 post-transition/pre-audit → contained + roll-forward, not served, no
  success reported; Class 3 post-execute/pre-`COMPLETION` → **UNCERTAIN → QUARANTINED** (INV-4), `INTENT`
  record present as evidence of the attempt.
- *adversarial* — honor a `PENDING` record (refused); report success with audit store forced unavailable
  (fails closed); duplicate `K` (Class 1/2 single effect; Class 3 no re-execute); forge a second `COMPLETION`.
- *property* — for random crash injection at any instruction: **INV-1..INV-4 all hold** post-reconciliation.
- **Evidence:** `cross-store-consistency` ETM rows; VM-2 gate (VEP §5) + `PROM-RPH3` requirement (VR-RPH3-19).

## 10. Operation → class assignment (authoritative)

| Operation | Class | Store(s) |
|---|---|---|
| permission grant issue / revoke | 1 | security-spine (`permission_grants`, `permission_intents`) + audit |
| approval enqueue / decide / consume / revoke | 1 | security-spine (`approval_records`,`approval_queue`,`approval_intents`) + audit |
| tool register / quarantine / release | 1 | security-spine (`tool_registry`,`tool_quarantine`,`tool_registry_intents`) + audit |
| `PAUSE_TASK` / `CONTAIN_TASK` / task-`RECONCILE` / task-`QUARANTINE` | 2 | runtime DB (`apply_transition`) + `intervention_journal` + audit |
| `RESTART_SERVICE` | 3 | Service Supervisor (external) + `intervention_journal` + audit |
| `CMP-FILEOP` delete / atomic write | 3 | filesystem (irreversible) + audit |
| `RESTORE_APPROVED_STATE` / `ACTIVATE_VERIFIED_SNAPSHOT` / non-task `QUARANTINE_RESOURCE` | — | INERT until PH-7 / PH-5 (WIR-RPH3 §3) |

## 10a. No fabricated rollback

Neither Class 2 nor Class 3 claims a provable rollback. A committed **Class 2** PH-2 transition is **never**
described as rolled back — it is reconciled **roll-forward only** (finalize audit; the task stays in its
conservative containment state until reconcile). A **Class 3** external/irreversible effect has **no rollback
path at all** — an unproven outcome goes to `UNCERTAIN → QUARANTINED` for operator/approval-gated recovery.
Only **Class 1** (a `PENDING` security-store row that was never authoritative) is rolled back, and that is a
plain DB abort of a non-authoritative row, not a compensating action against a real-world effect.

## 11. Boundary

Governs **PH-3** cross-store operations only. The substrate's own lease/audit ordering (XIB-01/XIB-04) is a
separate PR #10 concern. Frozen PH-2 is unmodified — PH-3 uses only the existing `apply_transition` idempotency
+ durable journal; it adds no PH-2 method.
