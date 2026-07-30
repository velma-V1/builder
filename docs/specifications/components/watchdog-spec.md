# Component Specification — Watchdog (CMP-WATCH)

**Instance authority:** L25.1 planning record · **Phase:** roadmap PH-3 (RPH3-T1) · **Governing:** `01M`
(§1/§2/§3.1-3.5/§3.12; 32 acceptance criteria), `01R` R1, `docs/10 §PH-3`. Parent index:
`docs/specifications/components/00-COMPONENT-MAP.md` #26. Baselines BASE-P/X/T/S/D/R/RES inherited from the
component-map header; only deltas stated. **This is roadmap PH-3 (Watchdog security spine), NOT the Worker
Execution Substrate (`CMP-WORKER`, out-of-roadmap); see `docs/WORKER-EXECUTION-SUBSTRATE-CLASSIFICATION.md`.**

```yaml
component_id:          CMP-WATCH
name:                  Watchdog
implementation_phase:  PH-3 (RPH3-T1)
responsibility: >
  An independently supervised operating-system process/service — separate from the Orchestrator —
  that observes Factory and project health and, during normal operation, is READ-ONLY (R1: the
  Watchdog is never the authoritative-state writer). It has its own heartbeat, event loop, failure
  handling, and bounded resources, and does NOT share the Orchestrator's event loop, worker pool,
  or writable authoritative-state connection. Intervention is permitted only through a narrow,
  predefined control interface with validated inputs, expected-state checks, bounded scope, audit
  identity, and deterministic outcomes.
non_responsibilities:
  - Not the state writer; performs no arbitrary file/DB/repo/source/policy/retention/config edits (01M §2.2).
  - Cannot modify its own rules, thresholds, permissions, configuration, or governing authority (01M §2.28/§3.4).
  - Does not run models/tools/sandboxes/lanes; does not build permission/approval/audit engines (those are
    sibling PH-3 components it observes).
  - Does not fabricate sensor readings; a missing sensor yields REDUCED_MONITORING (01M §3.3).
authoritative_state:   none (read-only observer; interventions are journaled+audited via CMP-ORCH/CMP-AUDITW).
inputs:
  - monotonic service heartbeats (Orchestrator + core services)
  - resource/thermal telemetry (CPU/RAM/GPU/VRAM/disk/IO/process-count; sensors may be absent)
  - read-only runtime-state + journal (via CMP-ORCH read-only reader, mode=ro)
outputs:
  - narrow intervention commands (7, below) with audit identity
  - health/threshold state transitions (NORMAL/WARNING/PAUSE/CRITICAL_CONTAINMENT/REDUCED_MONITORING)
  - integrity-protected Watchdog audit records (every intervention; via CMP-AUDITW)
interfaces:
  - "WatchdogControl.PAUSE_TASK(task_id, expected_state, reason) -> InterventionResult"
  - "WatchdogControl.CONTAIN_TASK(task_id, trigger) -> InterventionResult"
  - "WatchdogControl.RESTART_SERVICE(service_id, backoff_state) -> InterventionResult"
  - "WatchdogControl.RECONCILE_STATE(scope) -> InterventionResult"
  - "WatchdogControl.QUARANTINE_RESOURCE(resource_ref, reason) -> InterventionResult"
  - "WatchdogControl.RESTORE_APPROVED_STATE(target, approval_ref) -> InterventionResult"
  - "WatchdogControl.ACTIVATE_VERIFIED_SNAPSHOT(snapshot_ref) -> InterventionResult   # binds CMP-SNAP (PH-7)"
  - "HeartbeatMonitor.observe(service_id, monotonic_ts) -> StallVerdict"
dependencies:
  - CMP-ORCH (read-only reader; the interface through which any journaled intervention is applied — R1)
  - CMP-JOURNAL (startup/state reconciliation outcomes, read-only)
  - CMP-AUDITW (every intervention produces an integrity-protected audit record, 01M §2.27)
  - CMP-SNAP (PH-7) — forward-bound: ACTIVATE_VERIFIED_SNAPSHOT is inert until the snapshot manager exists
owned_contracts:       [ ] (defines no new contract; consumes CTR-RECOVERY-JOURNAL, CTR-AUDIT-RECORD)
permitted_authority:   BASE-P minus write; may act ONLY through the 7 predefined interventions with validated
                       inputs + expected-state checks + bounded scope (01M §3.2).
prohibited_authority:  BASE-X + no arbitrary shell/DB-write/file-mutation/policy/repo edit; cannot expand or
                       modify its own authority (fail closed if attempted).
trust_boundary:        BASE-T; heartbeats/telemetry are untrusted inputs; safety-critical elapsed time uses
                       monotonic clocks only (wall-clock cannot create false failures, 01M §3.12).
failure_modes:
  - Orchestrator stall/deadlock -> detected from the separate process; staged thresholds escalate
  - missing/unreliable sensor -> REDUCED_MONITORING (never fabricated readings)
  - Watchdog loss -> existing high-risk work pauses, new high-risk work blocked (01M §2.35)
  - attempted self-authority modification -> rejected, fail closed, audited
degradation_behavior:  BASE-D; REDUCED_MONITORING declares exactly which capabilities are degraded; never
                       weakens permission/audit/evidence/state-authority.
recovery_behavior:     BASE-R; interventions are bounded, journaled, idempotent, and conditional on
                       deterministic reconciliation; unknown/inconsistent state -> BLOCKED/QUARANTINED.
security_requirements: BASE-S; loss of mandatory security controls is an enumerated CRITICAL_CONTAINMENT
                       trigger; the Watchdog is itself a core control (its loss fails high-risk work closed).
resource_requirements: BASE-RES; small, bounded, independently restartable even when the Orchestrator is
                       resource-starved (01M §3.1); no GPU.
required_tests:
  - 01M(32) acceptance set — esp. #1 detects unresponsive Orchestrator from a separate process; #2 survives
    Orchestrator event-loop/worker-pool stall; #3 normal monitoring cannot silently alter state; #4 only the
    predefined interface is accepted (arbitrary mutation rejected); #5 monotonic timing correct across
    wall-clock change; #6 staged thresholds w/ hysteresis; #7 missing sensor -> REDUCED_MONITORING; #8 only
    enumerated triggers cause containment; #21 every intervention audited; #22 cannot modify own authority;
    #30 Watchdog-loss pauses/blocks high-risk work
  - security: intervention interface rejects arbitrary shell/DB/file/policy input (fail closed)
  - failure-path: Watchdog-loss simulation (RM-1)
```

## Lifecycle

- **Initialization:** launch as a separately supervised OS process/service with its own heartbeat and bounded
  resources; open a read-only (`mode=ro`) runtime-state reader; load versioned threshold policy (immutable to
  the Watchdog itself).
- **Runtime:** observe monotonic heartbeats + telemetry; compute staged threshold state with sustained-duration
  windows + hysteresis; intervene only via the 7 predefined commands, each producing an audit record.
- **Shutdown/loss:** loss is itself a monitored condition — existing high-risk work pauses and new high-risk
  work is blocked until supervision is restored (01M §2.35).
- **Recovery:** interventions replay idempotently; no blind resume — reconciled resume only via CMP-JOURNAL.

## Authority separation note

CMP-WATCH observes but never writes authoritative state (R1) and **holds no writable authoritative
connection**. The seven `WatchdogControl.*` calls above are **typed requests issued to the Watchdog
Intervention Receiver (WIR)**, not executions performed by the observer — see
`docs/planning/RPH3-WATCHDOG-INTERVENTION-RECEIVER.md` (WIR-RPH3). The WIR (executor facet of the `01M §3.2`
interface) validates each request (allowlist, expected-state, bounded scope, idempotency, auth), then executes
it through a **real** interface: `PAUSE_TASK`/`CONTAIN_TASK`/task-`RECONCILE_STATE`/task-`QUARANTINE_RESOURCE`
via the frozen `CMP-ORCH.apply_transition` (task state only); `RESTART_SERVICE` via a PH-3 Service Supervisor
(OS process supervision, **not** a DB write). **`RESTORE_APPROVED_STATE` and `ACTIVATE_VERIFIED_SNAPSHOT` are
INERT until PH-7; non-task `QUARANTINE_RESOURCE` is INERT until PH-5.** `apply_transition` performs **only**
task-state transitions — it does not execute service-restart, resource-quarantine, restore, or snapshot
commands. Every applied intervention is audited before it reports `APPLIED` (XSC-RPH3). Recorded here and in
`RPH3-INTEGRATION.md` §Ownership.
