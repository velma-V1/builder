# Component Specification — Orchestrator (CMP-ORCH)

**Instance authority:** L25.1 planning record · **Phase:** PH-2 · **Governing:** `02 §4/§6/§7`, `01L §3.1`,
`01M §3.6/§3.17/§3.19`, `01R` R1. Parent index: `docs/specifications/components/00-COMPONENT-MAP.md` #2.
Baselines BASE-P/X/T/S/D/R/RES inherited from the component-map header; only deltas stated.

```yaml
component_id:          CMP-ORCH
name:                  Orchestrator
implementation_phase:  PH-2
responsibility: >
  The deterministic control-plane engine and the SOLE authoritative writer to the runtime-state
  database (R1). Owns the runtime-state DB as a whole and the single atomic write transaction
  through which every authoritative state change is applied. Coordinates its sub-components
  (workstream state machine, task engine, recovery journal, lease system, core memory) which
  perform their writes ONLY inside the Orchestrator's transaction — they are not independent writers.
non_responsibilities:
  - Does not run models, tools, sandboxes, worktrees, or lanes (PH-4/PH-5/PH-6).
  - Is not the Watchdog and does not supervise itself; the Watchdog (PH-3) observes from a separate process.
  - Does not build the permission/approval/audit engines (PH-3) — it only exposes the transaction they call.
  - Does not decide policy on contracts (that is PH-1's PolicyEngine, already implemented).
authoritative_state:   OWNS the runtime-state DB (all tables in migrations/runtime/*).
inputs:
  - validated CanonicalContract task set (from PH-1 ContractService, read-only)
  - transition requests (expected_current_state, new_state, cause, actor, idempotency_key)
  - lease acquire/renew/release requests
outputs:
  - committed StateTransitionEvent rows (append-only)
  - updated tasks.current_state / sequence
  - ReconciliationOutcome map at startup
interfaces:
  - "_OrchestratorStateWriter.apply_transition(*, task_id, expected_current_state, new_state, cause, actor, linked_reference=None, idempotency_key=None) -> StateTransitionEvent"
  - "SQLiteOrchestratorStateReader.get_task / .get_events   # read-only, mode=ro + authorizer"
dependencies:
  - CMP-SCHEMA (PH-1 migration runner pattern; SHA-verified transactional migrations)
  - PH-1 contract system (consumes validated task contracts; does not write them)
owned_contracts:       [ CTR-RUNTIME-STATE-DB, CTR-ACTIVATION-STORE (shared w/ PH-1 activation) ]
permitted_authority:   BASE-P + the ONLY component permitted to write authoritative runtime state (R1).
prohibited_authority:  BASE-X + must never expose a second write path; readers get mode=ro connections only.
trust_boundary:        BASE-T; treats every transition request as untrusted until the expected-state and
                       legal-transition checks pass.
failure_modes:
  - illegal transition requested -> append accepted=0 audit event, leave state unchanged (fail closed)
  - expected_current_state mismatch (optimistic-concurrency) -> reject, no write
  - mid-transaction failure -> full rollback; no partial state observable
degradation_behavior:  BASE-D; if the DB is unavailable the Orchestrator refuses writes rather than
                       degrading to an unlogged path (never weakens state authority).
recovery_behavior:     BASE-R; on startup, delegates to CMP-JOURNAL reconciliation; unknown/inconsistent
                       state -> BLOCKED/QUARANTINED, never silent resume.
security_requirements: BASE-S; single-writer invariant is a core control (fail closed if violated).
resource_requirements: BASE-RES; negligible (SQLite, offline, no GPU).
required_tests:
  - legal transition applies + appends exactly one accepted=1 event, sequence monotonic +1
  - illegal transition leaves state unchanged + appends accepted=0 audit event
  - expected-state mismatch rejected
  - atomic rollback: forced pre-commit failure leaves state + sequence unchanged, no event row
  - read-only reader cannot INSERT/UPDATE/DELETE/CREATE/DROP/ALTER (security)
  - idempotent restart: same idempotency_key returns identical event, one row only
```

## Lifecycle

- **Initialization:** open/create the runtime DB, run `apply_migrations` (SHA-256-pinned, one transaction,
  version recorded only on success — mirrors PH-1 `activation/store.py`); generate a fresh `ProcessEpoch`.
- **Runtime:** serve `apply_transition` under `BEGIN IMMEDIATE`; each call is one atomic
  validate→check-legal→apply→append-event→commit unit (`02 §7`).
- **Shutdown:** no special action; the journal (append-only events) is authoritative and crash-consistent.
- **Recovery:** delegate to CMP-JOURNAL `reconcile_startup` before serving new transitions.

## Layering clarification (resolves apparent CMP-ORCH ↔ CMP-JOURNAL/CMP-LEASE overlap)

The component map lists CMP-ORCH as owning "journal, leases" while CMP-JOURNAL/CMP-LEASE also "own" those.
Deterministic resolution under R1: **CMP-ORCH owns the write authority and the DB as a whole; CMP-JOURNAL
and CMP-LEASE own their respective sub-schemas and domain logic but execute all writes inside the
Orchestrator's transaction.** No sub-component holds an independent writable connection. This is a layering,
not a contradiction — recorded here and in `PH2-INTEGRATION.md` §Ownership.
