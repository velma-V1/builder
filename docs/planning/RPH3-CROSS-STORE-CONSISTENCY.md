# Roadmap PH-3 — Cross-Store Crash-Consistency Protocol (XSC-RPH3)

**Document ID:** XSC-RPH3 · **Repository path:** `docs/planning/RPH3-CROSS-STORE-CONSISTENCY.md`
**Status:** Active architecture plan (subordinate to `01M §3.6/§3.17`, `01K §3.2`, `01R` R1) · **Owner:** RPH3
planning (repair R3) · **Established:** 2026-07-26. **Namespace:** RPH3. Fixes defect **D2** and satisfies
correction #3. Verifies VR-RPH3-19.

## 0. Invariant (the reason this protocol exists)

> **A security decision, approval, privileged action, Watchdog intervention, or tool/file operation MUST NEVER
> report success while its required audit record is absent.** Equivalently: **authoritative ⟺ audited.**

Because the three stores are independent SQLite databases with **no cross-database transaction**, this is
enforced by a write-ahead-intent + **audit-as-commit-point** protocol with idempotent replay.

## 1. The three stores

| Store | Owner / writer | Transaction scope |
|---|---|---|
| Runtime-state DB (frozen PH-2) | CMP-ORCH only (R1); PH-3 read-only + `apply_transition` calls | PH-2 `BEGIN IMMEDIATE`; durable journal (`01M-AC-12`) |
| Security-spine store (PH-3) | per-domain sole writer (CMP-PERM / CMP-APPROVAL / CMP-TOOLREG) | WAL; single-writer per table (see ownership doc) |
| Audit store (PH-3) | CMP-AUDITW only | WAL; append-only hash chain |

## 2. Operation identity & idempotency key

Every protocol operation `OP` carries an **operation identity**:
`op_id = (domain, verb, subject_ref, actor, causal_ref)` and a derived **idempotency key**
`K = sha256(canonical(op_id) ‖ epoch)`. `K` is unique per logical operation and stable across retries.
`K` is the primary key of the intent record and is embedded in the audit record — it is the join that makes
every step idempotent and lets reconciliation correlate the three stores.

## 3. Protocol states & steps

A domain record has a lifecycle: `PENDING → COMMITTED` (or `PENDING → ABORTED`). **Only `COMMITTED` records are
authoritative; readers MUST ignore `PENDING`/`ABORTED`.**

| Step | Store | Action |
|---|---|---|
| **S1 · durable intent** | security-spine | insert intent `{K, op_id, target, expected_state_hash, status=PENDING}`; durable commit |
| **S2 · domain mutation** | security-spine (or runtime DB via `apply_transition`) | apply the change tied to `K`, still non-authoritative (`PENDING`) |
| **S3 · audit finalization** | audit store | `CMP-AUDITW.append({K, op_id, domain_ref, outcome})`; **durable** — this is the **commit point** |
| **S4 · domain commit** | security-spine | set `status=COMMITTED`, store `audit_seq`; durable |
| **S5 · report success** | caller | only now may the operation report success |

**Commit/failure ordering rule:** success is reported **iff** S3 is durable. S3 (audit) precedes S4 (commit)
and S5 (report). The audit record is the linearization point of the whole cross-store operation.

### 3a. Runtime-DB variant

When S2 is a task-state change it goes through the frozen `CMP-ORCH.apply_transition` (its own
`idempotency_key = K`, durable via the PH-2 journal, `01M-AC-12`). Because a committed PH-2 transition cannot
be half-applied, its reconciliation direction is **roll-forward** (see §5, window W3′).

## 4. Crash windows (every window enumerated)

| Window | Crash between | State on restart | Reconciliation (fail-closed) |
|---|---|---|---|
| W0 | before S1 durable | nothing | nothing happened; caller may retry with same `K` |
| W1 | S1 and S2 | intent `PENDING`, no mutation, no audit | **abort**: set `ABORTED`; fail closed |
| W2 | S2 and S3 | domain mutated but `PENDING`, **no audit for `K`** | **roll back** the mutation; set `ABORTED`; fail closed (never authoritative, never reported success) |
| W3 | S3 and S4 | **audit present for `K`**, domain `PENDING` | **roll forward**: finalize S4 (idempotent); operation is authoritative because it is audited |
| W3′ | apply_transition committed, before S3 | PH-2 transition durable, no audit | **roll forward**: finalize S3+S4 (the transition is legal + journaled; record the audit); success not reported until audit durable |
| W4 | after S4 | `COMMITTED` + audit present | no-op |

**Decision boundary:** audit **absent** ⇒ roll back / abort (fail closed). Audit **present** ⇒ roll forward /
complete. This is what guarantees `authoritative ⟺ audited`.

## 5. Startup reconciliation

On startup, before serving any request, each PH-3 domain writer scans its `PENDING` records and, joined by `K`:

1. `CMP-AUDITV` verifies the audit chain (must be valid, else audit is non-authoritative and the system enters
   Safe Mode / fails closed — no roll-forward against an invalid chain).
2. For each `PENDING` domain record: if an audit record for `K` exists → **roll forward** (S4); else → **roll
   back / ABORT** (fail closed).
3. `PENDING` records older than a bounded reconciliation horizon with no audit are `ABORTED` and reported.
4. Runtime-DB-coupled operations use the PH-2 `reconcile_startup` outcome for the task in addition to the audit
   join (W3′ roll-forward only if the PH-2 transition is durably present).

No task or operation resumes before reconciliation completes (`01M-AC-14`, no blind resume).

## 6. Duplicate replay behavior

All steps are idempotent on `K`: S1 insert is unique-on-`K` (duplicate → no-op returning the existing intent);
S3 append is unique-on-`K` (CMP-AUDITW rejects a second append for the same `K`); S4 is a monotonic status set.
A retried `OP` with the same `K` therefore converges to a single committed effect and a single audit record —
**exactly-once effect, at-least-once attempts.** A different logical operation gets a different `K`.

## 7. Authoritative status while incomplete

A `PENDING` grant/approval/registry record is **not** honored by any reader (CMP-TOOLGW, CMP-FILEOP,
CMP-PERM): a permission grant is usable only when `COMMITTED`; an approval is consumable only when `COMMITTED`;
a tool is callable only when its registration is `COMMITTED`. Thus a partially-applied (unaudited) operation
can never authorize anything.

## 8. Fail-closed behavior

- Audit store unavailable / append fails at S3 → the operation **fails closed** (S4/S5 never run; domain stays
  `PENDING` → reconciled to `ABORTED`).
- Audit chain invalid (CMP-AUDITV) → audit non-authoritative → no roll-forward; system fails closed / Safe Mode.
- Any core-store write failure → `BLOCKED`/`QUARANTINED`, never a silent success.

## 9. Tests & evidence (VR-RPH3-19)

- *integration* — happy path S1→S5 produces exactly one committed record + one audit record joined by `K`.
- *failure-path (fault injection at each window)* — W1/W2 → ABORTED + no authoritative effect + **no success
  reported**; W3/W3′ → roll-forward → committed + audited; W4 → no-op.
- *adversarial* — attempt to read/honor a `PENDING` record (must be refused); attempt to report success with
  the audit store forced unavailable (must fail closed); duplicate `K` replay (single effect).
- *property* — for random crash injection at any instruction, the post-reconciliation state satisfies
  `authoritative ⟺ audited`.
- **Evidence:** `cross-store-consistency ETM` rows → `roadmap-ph3-evidence-report.md`; the invariant is a VM-2
  gate (VEP-RPH3 §5) and a `PROM-RPH3` requirement (VR-RPH3-19).

## 10. Boundary notes

This protocol governs **PH-3** cross-store operations only. The Worker Execution Substrate's own lease/audit
ordering (XIB-01/XIB-04) is a separate substrate concern owned by the PR #10 correction — this protocol does
not fix or depend on it. Frozen PH-2 is unmodified: PH-3 uses only the existing `apply_transition` idempotency
+ durable journal; it adds no PH-2 method.
