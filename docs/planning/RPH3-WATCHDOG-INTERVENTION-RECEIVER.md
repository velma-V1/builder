# Roadmap PH-3 — Watchdog Intervention Receiver (WIR-RPH3)

**Document ID:** WIR-RPH3 · **Repository path:** `docs/planning/RPH3-WATCHDOG-INTERVENTION-RECEIVER.md`
**Status:** Active architecture plan (subordinate to `01M §1/§3.2`, `01R` R1) · **Owner:** RPH3 planning
(repair R4) · **Established:** 2026-07-26. **Namespace:** RPH3. Fixes defect **D3**, satisfies correction #4.

## 0. Problem

`01M §3.2` defines a **narrow control interface** of seven commands, but the Watchdog is **read-only** and
**must not hold a writable authoritative-state connection** (`01M-DEC-01/02`, R1). Something else must
*receive* and *execute* those commands with bounded authority. The prior corpus left this undefined and
implied the frozen PH-2 transition writer could execute all seven — it cannot. This document defines the
receiver.

## 1. Trust separation (who holds what)

| Element | Process | Holds | Never holds |
|---|---|---|---|
| **Watchdog observer** (CMP-WATCH) | separate supervised OS process | read-only reader; heartbeat/threshold logic; issues typed intervention *requests* over the narrow interface | any writer reference; any writable DB connection |
| **Watchdog Intervention Receiver (WIR)** | Orchestrator-side bounded mediator (executor facet of the `01M §3.2` interface) | references to legitimate public methods only: `CMP-ORCH.apply_transition` (task state) and the PH-3 Service Supervisor | a raw writable authoritative-state connection (R1: only CMP-ORCH owns that) |
| **PH-3 Service Supervisor** | Orchestrator-side | OS process/service supervision (start/stop/restart) with bounded retries+backoff+circuit-breaker | any DB write; any authoritative-state authority |

The WIR is **not** a new numbered component — it is the executor facet of CMP-WATCH's `01M §3.2` control
interface, kept in a separate module from the observer loop with **no shared writable connection**. It writes
authoritative state **only** by calling `CMP-ORCH.apply_transition` (the same public path CMP-TASKENG uses);
CMP-ORCH remains the sole runtime-state writer (R1). Frozen PH-2 is unmodified — no new PH-2 method.

## 2. Typed request / result schemas

```
InterventionRequest {
  command:         Command            # exactly one of the 7 (allowlist §3)
  target_ref:      TargetRef          # one task_id | service_id | resource_ref (no wildcard/bulk)
  expected_state:  StateHash          # optimistic-concurrency guard
  reason:          str                # bounded, for audit
  requestor:       WatchdogIdentity   # authenticated supervised-Watchdog id
  idempotency_key: K                  # XSC-RPH3 operation key
  monotonic_ts:    int                # monotonic clock (01M-AC-05)
  auth_token:      Token              # keyed/authenticated channel
}
InterventionResult {
  command, target_ref, idempotency_key,
  outcome:   {APPLIED | REJECTED | INERT | FAILED},
  audit_seq: int | null,             # the durable audit record sequence (present iff APPLIED)
  cause:     str
}
```

## 3. Command allowlist, executor, and phase status

The WIR accepts **exactly** these seven commands and **nothing else** (default-deny). Each maps to a **real**
interface or is explicitly **INERT** until its owning phase exists — **no command is claimed to run on an
interface that does not support it.**

| Command | Executor & real interface | Authoritative write? | Status at PH-3 |
|---|---|---|---|
| `PAUSE_TASK` | WIR → `CMP-ORCH.apply_transition(task, →PAUSED)` | via CMP-ORCH (R1) | **ACTIVE** |
| `CONTAIN_TASK` | WIR → `CMP-ORCH.apply_transition(task, →STOPPING/QUARANTINED)` | via CMP-ORCH | **ACTIVE** |
| `RECONCILE_STATE` | WIR → `CMP-JOURNAL.reconcile_startup` (read) then `apply_transition` for each outcome | via CMP-ORCH | **ACTIVE** (task scope only) |
| `QUARANTINE_RESOURCE` | **task** resource: WIR → `apply_transition(→QUARANTINED)`. **sandbox/worktree/model** resource: no PH-3 interface | task: via CMP-ORCH; resource: none | **PARTIAL** — task=ACTIVE; **non-task resource INERT until PH-5** |
| `RESTART_SERVICE` | **PH-3 Service Supervisor** (OS process/service restart; bounded retries+backoff+circuit-breaker). **NOT a DB write** | **no** authoritative-state write | **ACTIVE** (service supervision) |
| `RESTORE_APPROVED_STATE` | no approved interface exists at PH-3 (needs approved-state/snapshot machinery) | none | **INERT until PH-7** |
| `ACTIVATE_VERIFIED_SNAPSHOT` | `CMP-SNAP` (snapshot manager) | none at PH-3 | **INERT until PH-7** |

**Explicitly rejected claim (defect D3):** `apply_transition` executes **only task-state transitions**. It
does **not** perform service restart, non-task resource quarantine, approved-state restoration, or snapshot
activation. Those are the Service Supervisor (restart) or forward-bound to PH-5/PH-7 — never routed through
the transition writer.

## 4. Validation pipeline (every request)

1. **Authenticate** the requestor is the supervised Watchdog (keyed token / local trusted channel); else REJECT.
2. **Allowlist** check — command ∈ the seven; else REJECT (default-deny).
3. **Phase-status** check — if the command is INERT at the current phase → return INERT (audited), no effect.
4. **Bounded scope** — exactly one `target_ref`; no wildcard, no bulk, no arbitrary path/DB/policy.
5. **Expected-state** check — current state hash == `expected_state`; else REJECT (optimistic concurrency).
6. **Idempotency** — if `K` already applied, return the prior `InterventionResult` (exactly-once effect).
7. **Execute** via the mapped real interface (§3) under the XSC-RPH3 protocol (§5).

## 5. Durability & audit ordering (XSC-RPH3)

Every accepted intervention follows the cross-store protocol (`RPH3-CROSS-STORE-CONSISTENCY.md`):
**durable intent (WIR journal) → execute (apply_transition / supervisor) → audit finalize (CMP-AUDITW, the
commit point) → mark committed → return `APPLIED`.** The result reports `APPLIED` **only after** the audit
record is durable (`01M-AC-21`: every intervention produces a traceable integrity-protected audit record).
Crash between execute and audit reconciles **roll-forward** (W3′): the legal transition is journaled by PH-2,
so the reconciler finalizes the audit rather than undoing a committed transition.

## 6. Authority & authentication

- The Watchdog authenticates to the WIR; unauthenticated or spoofed requests are rejected + audited.
- The **Watchdog cannot modify its own authority** (`01M-AC-22`) and cannot expand the allowlist — the seven
  commands + phase-status policy are **versioned policy** the Watchdog may not edit (`01M-DEC-28`).
- The WIR's authority is bounded to the seven mapped interfaces; it has no arbitrary shell/DB/file/policy path
  (`01M §3.2`).

## 7. Failure behavior

| Condition | Outcome |
|---|---|
| bad auth / spoofed requestor | REJECTED + audited; fail closed |
| command not in allowlist | REJECTED (default-deny) + audited |
| expected-state mismatch | REJECTED (no effect) + audited |
| command INERT at this phase | INERT + audited; no effect |
| execute fails (apply_transition/supervisor error) | FAILED; target left in a safe/consistent state; audited |
| audit finalize fails | fail closed: intervention not reported APPLIED; reconciled per XSC-RPH3 |
| **WIR unavailable** | Watchdog cannot intervene → existing high-risk work pauses, new blocked (`01M-AC-30`) |

## 8. Tests & evidence

- *unit* — allowlist default-deny; expected-state guard; idempotent replay; INERT commands are inert.
- *security/adversarial* — spoofed requestor rejected; attempt to expand allowlist rejected; attempt to route
  RESTART/RESTORE/SNAPSHOT through `apply_transition` is impossible by construction (no such code path).
- *integration* — PAUSE_TASK/CONTAIN_TASK apply the correct transition via CMP-ORCH and produce one audit
  record each (audit-before-APPLIED).
- *failure-path* — WIR-unavailable → high-risk pause; audit-finalize failure → not APPLIED.
- **Evidence:** watchdog-receiver ETM rows → `roadmap-ph3-evidence-report.md`; gates VR-RPH3-04/07/15/19.

## 9. Boundary

`RESTORE_APPROVED_STATE` and `ACTIVATE_VERIFIED_SNAPSHOT` are **INERT until PH-7**; non-task
`QUARANTINE_RESOURCE` is **INERT until PH-5**. RPH3 ships their request typing + INERT handling only, and does
not implement the PH-5/PH-7 executors (no absorption). Frozen PH-2 is unmodified.
