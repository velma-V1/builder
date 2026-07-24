# Component Specification — Recovery Journal & Startup Reconciliation (CMP-JOURNAL)

**Instance authority:** L25.1 planning record · **Phase:** PH-2 · **Governing:** `01M §3.6/§3.17/§2.18`,
`01M §5` (reconciliation outcomes), `01M §11` ("no blind task resume"), `01R` R1. Parent index:
`00-COMPONENT-MAP.md` #27. Baselines inherited; only deltas stated.

```yaml
component_id:          CMP-JOURNAL
name:                  Recovery Journal & Startup Reconciliation
implementation_phase:  PH-2
responsibility: >
  The append-only task_state_events table IS the durable journal (written inside the same atomic
  transaction as each state change, so a transition is never reported before it is durably committed).
  At startup, reconstructs each task's state by folding its accepted events and assigns exactly one
  ReconciliationOutcome per task, honoring "no blind task resume".
non_responsibilities:
  - Does not write state or apply transitions (CMP-ORCH does; the journal rows are appended within that tx).
  - Does not reconcile containers, model workers, worktrees, mounts, or pending promotions — none exist in
    PH-2. That fuller 01M §20 reconciliation is PH-3+. This scope limit is a recorded known limitation.
authoritative_state:   co-owns the task_state_events sub-schema (append-only; triggers reject UPDATE/DELETE).
inputs:                [ OrchestratorStateReader, task_ids: Sequence[str] ]
outputs:               [ Mapping[str, ReconciliationOutcome] ]
interfaces:
  - "reconcile_startup(reader, task_ids) -> Mapping[str, ReconciliationOutcome]"
dependencies:          [ CMP-ORCH (reader + shared tx), CMP-WSSM (state vocabulary) ]
owned_contracts:       [ CTR-RECOVERY-JOURNAL ]
permitted_authority:   BASE-P; read-only at reconciliation time.
prohibited_authority:  BASE-X; reconciliation NEVER auto-resumes a task — it only classifies.
trust_boundary:        BASE-T; a stored current_state that disagrees with the replayed event history is
                       treated as corruption.
failure_modes:
  - replayed state != stored current_state -> QUARANTINED (corruption/bug, not resumable)
  - in-flight non-terminal state at crash -> BLOCKED (no worker/Watchdog layer yet to prove safe resume)
degradation_behavior:  BASE-D.
recovery_behavior:     the reconciliation mapping IS the recovery behavior; unknown/inconsistent -> fail closed.
security_requirements: BASE-S; append-only journal is a protected control (triggers + no writable reader path).
resource_requirements: negligible.
required_tests:
  - consistent replay + QUEUED -> RESUMABLE
  - task left RUNNING at simulated crash (row written directly) -> BLOCKED
  - stored state disagreeing with replayed history -> QUARANTINED
  - crash-consistency: hard-kill mid-transition leaves DB fully-applied-or-not (WAL), no silent resume
```

## Reconciliation mapping (verbatim, diffable)

Applied only when event replay is consistent; a replay mismatch overrides to `QUARANTINED`.

| Current state | Outcome | Rationale |
|---|---|---|
| `QUEUED` | `RESUMABLE` | never started |
| `PLANNING`,`RUNNING`,`AWAITING_APPROVAL`,`VERIFYING`,`PAUSED`,`STOPPING`,`QUARANTINED` | `BLOCKED` | no PH-2 layer can prove safe resume; PH-3 may re-classify |
| `BLOCKED` | `BLOCKED` | unchanged |
| `FAILED` | `FAILED` | terminal |
| `CANCELLED` | `CANCELLED` | terminal |
| `COMPLETE`,`ROLLED_BACK` | `COMPLETED` | terminal, resolved |
