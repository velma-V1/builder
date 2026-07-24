# Approved Recovery, Reliability, and Watchdog Decision

**Status:** Approved architecture supplement  
**Recorded:** July 23, 2026  
**Clarified:** July 23, 2026

## 1. Governing reliability boundary

Factory uses an independently supervised Watchdog running as a separate operating-system process or service from the main Orchestrator. It has its own heartbeat, failure handling, bounded resource allocation, and supervision path. It must not share the Orchestrator's event loop, worker pool, or writable authoritative-state connection.

The Watchdog is normally read-only. Intervention is permitted only through a narrow predefined control interface for checkpointed pause, critical containment, bounded service restart, state reconciliation, quarantine, and approved-state restoration. It cannot perform arbitrary file, database, repository, source-code, architecture, policy, retention-rule, or configuration edits and cannot modify its own governing authority.

All automatic recovery is bounded, durably journaled, integrity-protected, auditable, and conditional on successful deterministic reconciliation. Unknown, inconsistent, corrupted, or security-sensitive state fails closed as `BLOCKED` or `QUARANTINED`.

Factory maintains one active rolling recovery snapshot. A newly created snapshot remains a candidate and cannot replace the active snapshot until integrity verification and isolated restoration testing succeed.

## 2. Approved Stage 11 decisions

1. **Independent Watchdog:** The Watchdog runs as a separately supervised operating-system process or service with its own heartbeat and failure handling. It does not share the Orchestrator's event loop, worker pool, or writable authoritative-state connection.
2. **Read-only normal monitoring:** During normal operation, the Watchdog observes health and state without silently changing project or Factory data. All interventions use a narrow predefined control interface; arbitrary file, database, repository, policy, retention, architecture, or configuration edits are prohibited.
3. **Service heartbeats:** Core services publish identifiable heartbeats using monotonic time for timeout and stall calculations. Wall-clock changes cannot create false failures.
4. **Task-specific stall limits:** Heartbeat, inactivity, and stall limits vary by task and operation type and use approved sustained-duration windows and hysteresis.
5. **Loop detection:** The Watchdog detects repeated actions, deterministically equivalent failures, circular execution, uncontrolled process multiplication, and other runaway loops.
6. **Resource and thermal monitoring:** The Watchdog monitors CPU, RAM, GPU, VRAM, disk capacity, storage I/O, process count, and available thermal-pressure signals through staged `WARNING`, `PAUSE`, and `CRITICAL_CONTAINMENT` thresholds. Missing sensors produce a visible reduced-monitoring state and never fabricated readings.
7. **Automatic checkpointed pause:** The Watchdog may automatically pause unsafe work through a verified checkpoint when sustained thresholds or policy conditions require it.
8. **Critical containment:** Automatic termination or containment is limited to enumerated approved triggers, including sustained critical temperature, critically exhausted storage or emergency reserve, uncontrolled process multiplication, failed containment, loss of mandatory security controls, or another explicitly approved equivalent condition.
9. **Proportionate ordinary failure handling:** Ordinary failures do not cause immediate destructive termination. Factory pauses, diagnoses, retries within policy, or requests operator action first.
10. **Bounded service restart:** Failed Factory services may restart automatically only with bounded retries, exponential backoff, and a circuit breaker. Exhaustion moves the affected service or task to `BLOCKED` or `QUARANTINED`.
11. **No blind task resume:** Task execution does not resume immediately after a service restart.
12. **Reconciled automatic resume:** A task may resume automatically after successful state reconciliation when policy permits and no approval, conflict, hold, fencing-token conflict, or unknown state blocks it.
13. **Failure-class retry limits:** Recovery retry limits depend on the verified failure class and operation risk.
14. **Equivalent-failure counters:** Equivalent-failure classification is deterministic, recorded, and based on normalized failure identity. Timestamps, worker IDs, regenerated wording, retry numbers, or other superficial differences cannot reset the counter.
15. **Pre-restart evidence capture:** Evidence, logs, checkpoints, and failure context are secured before restart or termination when safely possible.
16. **Containment priority:** During immediate danger, containment overrides graceful evidence preservation.
17. **Authoritative transactional journal:** The durable transactional journal is authoritative for detecting and resolving incomplete state transitions. Critical transitions are durably flushed before success is reported.
18. **Idempotent recovery operations:** Recovery-sensitive operations are designed to be safely replayable without duplicating changes or damage.
19. **Fenced expiring leases:** Task, resource, workspace, branch, model, sandbox, and promotion locks use expiring leases with owner identity, monotonic lease timing, renewal rules, and fencing tokens. A delayed former owner cannot modify state after its lease is superseded.
20. **Startup reconciliation:** Startup reconciles tasks, workstreams, model workers, inference processes, services, containers, sandboxes, branches, temporary worktrees, workspaces, mounted volumes, processes, models, approvals, locks, fencing tokens, journals, checkpoints, and pending promotion operations.
21. **Unknown-state blocking:** Unexplained or inconsistent state is not resumed automatically and enters `BLOCKED` or `QUARANTINED` review.
22. **Quarantine-first orphan handling:** Unknown resources are quarantined first. Automatic cleanup occurs only after ownership, identity, inactivity, checkpoint status, evidence preservation, fencing, and hold checks confirm deletion is safe.
23. **Startup integrity checks:** Factory verifies databases, journals, authoritative records, checkpoints, snapshots, evidence references, indexes, permissions, and material integrity links before normal operation.
24. **Capability-scoped degraded operation:** Failure of an optional noncritical subsystem may permit explicitly bounded degraded operation only for unaffected capabilities. Degradation cannot silently weaken verification, permissions, logging, evidence, audit, isolation, or state-authority guarantees.
25. **Fail-closed core controls:** Failure of security, permission, identity, state-authority, evidence, audit, isolation, or promotion controls causes Factory to fail closed.
26. **Restricted Safe Mode:** Safe Mode permits inspection, evidence export, recovery, integrity checks, and approved repair, but not normal autonomous task execution or unrestricted writes.
27. **Watchdog audit:** Every Watchdog pause, containment, termination, restart, reconciliation, recovery, quarantine, cleanup, snapshot activation, and release action produces an integrity-protected audit record.
28. **No self-modifying Watchdog policy:** The Watchdog cannot modify its own rules, thresholds, permissions, configuration, or governing authority. Changes require the normal explicit architecture and approval process.
29. **Scheduled recovery drills:** Factory performs approved recovery drills during controlled idle testing.
30. **Release failure simulations:** Release verification includes applicable controlled crash, interruption, stalled-service, partial-write, power-loss, lease-fencing, restart-exhaustion, and Watchdog-loss simulations.
31. **Candidate-tested snapshot activation:** Recovery snapshots are integrity-checked and restored in an isolated temporary environment. A candidate snapshot replaces the active rolling snapshot only after checksums, schema compatibility, journal replay, references, permissions, and successful Factory startup are verified.
32. **Factory-state-only restoration:** Snapshot restoration never overwrites or replaces GitHub project repositories. Recovery snapshots cover Factory state only.
33. **Emergency storage reserve:** Factory maintains reserved storage for journal commits, evidence finalization, shutdown records, audit events, and recovery metadata. New work pauses before that reserve is consumed.
34. **No emergency deletion of protected records:** Factory cannot delete protected evidence, audit records, checkpoints, holds, or authoritative memory merely to free storage. Cleanup remains governed by retention policy.
35. **Watchdog dependency for high-risk work:** High-risk work includes privileged, credentialed, network-enabled, write-capable, destructive, promotion, release, migration, security-sensitive, or externally consequential operations. Watchdog failure safely pauses existing high-risk tasks and blocks new ones. Low-risk read-only inspection may continue only while state authority, permissions, evidence, and audit systems remain healthy.
36. **Optional Windows auto-launch:** Windows startup launch is optional, user-controlled, and disabled by default.

## 3. Binding reliability clarifications

### 3.1 Independent process and supervision

The Watchdog must be independently observable and restartable even when the Orchestrator is deadlocked or resource-starved. Shared code libraries are permitted, but runtime scheduling, heartbeat handling, and authoritative-state write authority remain separated.

### 3.2 Narrow intervention interface

The intervention interface permits only predefined commands with validated inputs, expected-state checks, bounded scope, audit identity, and deterministic outcomes:

```text
PAUSE_TASK
CONTAIN_TASK
RESTART_SERVICE
RECONCILE_STATE
QUARANTINE_RESOURCE
RESTORE_APPROVED_STATE
ACTIVATE_VERIFIED_SNAPSHOT
```

The interface cannot expose arbitrary shell execution, general database writes, unrestricted file mutation, policy edits, or repository changes.

### 3.3 Staged thresholds and sensor honesty

Resource policies use:

```text
NORMAL
WARNING
PAUSE
CRITICAL_CONTAINMENT
REDUCED_MONITORING
```

Thresholds include sustained-duration windows and separate recovery thresholds to provide hysteresis. A missing or unreliable sensor changes monitoring status to `REDUCED_MONITORING`; it does not generate estimated or invented measurements.

### 3.4 Enumerated critical triggers

Critical containment triggers are versioned approved policy entries. At minimum, policy covers sustained critical thermal conditions, critically exhausted storage or emergency reserve, uncontrolled process multiplication, repeated failed containment, mandatory security-control loss, and an operation continuing after authority revocation.

A model cannot create or expand a critical trigger dynamically.

### 3.5 Deterministic failure identity

Equivalent-failure identity uses normalized fields such as component, operation, error class, stable error code, affected resource, phase, and causal signature. Volatile fields are excluded. The normalization result and retry-counter linkage are recorded in evidence.

### 3.6 Durable journals and fencing

A critical transition is successful only after its authoritative journal record and related state transaction are durably committed. Lease fencing tokens increase monotonically or use an equivalent non-reusable ordering mechanism. Every protected write validates the current fencing token.

### 3.7 Quarantine-first reconciliation

Startup and orphan reconciliation include all execution, model, container, worktree, volume, mount, branch, lock, approval, and promotion resources. Unknown ownership or inconsistent identity causes quarantine, not deletion or resumption.

### 3.8 Capability-scoped degradation

Every degraded mode declares exactly which capabilities remain available and which are blocked. No degraded mode may reduce the strength of permissions, audit, evidence, verification, state authority, or isolation.

### 3.9 Snapshot candidate lifecycle

Factory maintains:

```text
ACTIVE_SNAPSHOT
CANDIDATE_SNAPSHOT
```

The active snapshot remains trusted and available while the candidate is created and tested. Candidate testing occurs in isolated temporary storage and must validate:

- content and manifest checksums;
- schema and migration compatibility;
- journal replay and incomplete-transition handling;
- database and record integrity;
- evidence, checkpoint, permission, and reference consistency;
- successful isolated Factory startup;
- absence of GitHub project-repository restoration.

Only a passing candidate atomically replaces the active snapshot. A failed candidate is quarantined and cannot invalidate or replace the active snapshot.

### 3.10 Emergency reserve

The emergency reserve is sized by versioned policy and protected from ordinary tasks, caches, models, indexing, and downloads. Crossing the pre-reserve threshold pauses admission of new work. Reserve use is limited to controlled finalization, containment, shutdown, audit, and recovery actions.

### 3.11 High-risk task boundary

A task is high-risk when it can modify protected or persistent state, use elevated permissions or credentials, access approved networks, perform migrations, alter security-sensitive behavior, promote or release artifacts, delete data, or cause external consequences. Task contracts record the risk class before execution.

### 3.12 Monotonic timing

Heartbeat, lease, timeout, backoff, stall, and sustained-threshold calculations use monotonic clocks. Wall-clock timestamps remain available for audit display but cannot determine safety-critical elapsed time.

## 4. Recovery operating boundaries

- The Watchdog is an independently supervised, normally read-only service.
- It acts only through predefined pause, containment, service-restart, reconciliation, quarantine, and approved-state-restoration controls.
- It cannot alter source code, repositories, architecture, policies, retention rules, or its own configuration.
- Automatic recovery is bounded, backoff-controlled, circuit-broken, journaled, fenced, and auditable.
- Automatic task resumption occurs only after successful deterministic reconciliation.
- Unknown, corrupt, conflicting, security-sensitive, or unexplained state fails closed.
- Recovery drills, failure simulations, and isolated snapshot restore tests are required before release.
- One active rolling snapshot remains available until a candidate passes integrity and isolated restoration verification.
- GitHub remains authoritative for committed project source and history; Factory recovery snapshots cover Factory state only.
- Windows auto-launch remains a convenience option rather than a reliability dependency.

## 5. State reconciliation outcome

After restart, crash, interruption, or Watchdog intervention, each affected task receives one explicit state:

```text
RESUMABLE
BLOCKED
FAILED
QUARANTINED
COMPLETED
CANCELLED
```

A task is `RESUMABLE` only when its authoritative task record, last verified checkpoint, repository baseline, sandbox or replacement environment, model and inference state, mounts, fencing tokens, locks, approvals, artifacts, journals, and evidence agree. Factory must not infer resumability from a surviving process, container, or workspace alone.

## 6. Acceptance criteria

This decision is satisfied only when tests prove that:

1. the Watchdog detects an unresponsive Orchestrator from a separate process or service;
2. the Watchdog remains operational when the Orchestrator event loop or worker pool stalls;
3. normal monitoring cannot silently alter project or Factory state;
4. intervention is limited to the predefined control interface and arbitrary mutation is rejected;
5. heartbeat, lease, stall, and timeout calculations remain correct across Windows wall-clock changes;
6. staged resource thresholds use sustained windows and hysteresis;
7. missing sensors produce `REDUCED_MONITORING` without fabricated readings;
8. only enumerated critical triggers can cause automatic termination or containment;
9. bounded restart attempts use exponential backoff and open a circuit breaker on exhaustion;
10. restart exhaustion moves affected work to `BLOCKED` or `QUARANTINED`;
11. deterministic failure normalization prevents superficial changes from resetting retry counters;
12. critical transition success is not reported before durable journal and state commitment;
13. stale lease owners cannot write after a newer fencing token is issued;
14. tasks cannot resume after restart until complete state reconciliation succeeds;
15. unknown resources are quarantined before cleanup decisions;
16. orphan cleanup cannot destroy resources protected by evidence, checkpoint, recovery, or retention holds;
17. startup reconciliation includes model workers, inference processes, containers, temporary worktrees, mounted volumes, and pending promotions;
18. degraded operation is capability-scoped and cannot weaken mandatory controls;
19. failure of core security, permission, authority, evidence, audit, isolation, or promotion controls fails closed;
20. Safe Mode cannot perform normal autonomous execution or unrestricted writes;
21. every Watchdog intervention produces a traceable integrity-protected audit record;
22. the Watchdog cannot modify its own governing rules or configuration;
23. controlled crash, interruption, partial-write, lease-fencing, restart-exhaustion, and Watchdog-loss simulations demonstrate correct recovery behavior;
24. candidate snapshots are restore-tested in isolation and cannot replace the active snapshot before passing;
25. snapshot restoration validates checksums, schema compatibility, journal replay, references, permissions, and isolated startup;
26. failed candidate snapshots leave the active snapshot unchanged and enter quarantine;
27. snapshot restoration cannot overwrite GitHub project repositories;
28. emergency reserve protection pauses new work before reserve consumption;
29. protected records cannot be automatically deleted for emergency storage recovery;
30. existing high-risk work pauses and new high-risk work is blocked when Watchdog supervision fails;
31. low-risk read-only inspection continues only while authority and audit systems remain healthy;
32. Windows auto-launch remains disabled unless explicitly enabled by the user.