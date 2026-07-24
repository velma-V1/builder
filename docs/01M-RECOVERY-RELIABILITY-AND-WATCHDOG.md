# Approved Recovery, Reliability, and Watchdog Decision

**Status:** Approved architecture supplement  
**Recorded:** July 23, 2026

## 1. Governing reliability boundary

Factory uses a Watchdog that operates independently from the main Orchestrator so it can detect stalls, loops, resource pressure, crashes, and unsafe execution even when the Orchestrator is degraded or unresponsive.

The Watchdog is read-only during normal monitoring. It may pause work, contain immediate danger, restart failed services, restore an approved state, and trigger recovery workflows only through predefined deterministic rules. It cannot redesign Factory, rewrite governing controls, modify its own authority, or silently alter project behavior.

Automatic task continuation is allowed only after Factory reconciles authoritative task state, checkpoints, sandboxes, branches, processes, approvals, locks, journals, and evidence. Unknown or inconsistent state fails closed as `BLOCKED` or `QUARANTINED`.

## 2. Approved Stage 11 decisions

1. **Independent Watchdog:** The Watchdog operates separately from the main Orchestrator.
2. **Read-only normal monitoring:** During normal operation, the Watchdog observes health and state without silently changing project or Factory data.
3. **Service heartbeats:** Core services publish identifiable health heartbeats.
4. **Task-specific stall limits:** Heartbeat, inactivity, and stall limits vary by task and operation type.
5. **Loop detection:** The Watchdog detects repeated actions, equivalent retries, circular execution, and other runaway loops.
6. **Resource and thermal monitoring:** The Watchdog monitors CPU, RAM, GPU, VRAM, disk capacity, storage I/O, process count, and available temperature or thermal-pressure signals.
7. **Automatic checkpointed pause:** The Watchdog may automatically pause unsafe work through a verified checkpoint when thresholds or policy conditions require it.
8. **Critical containment:** Activity presenting immediate danger may be terminated automatically under predefined approved critical triggers.
9. **Proportionate ordinary failure handling:** Ordinary failures do not cause immediate destructive termination. Factory pauses, diagnoses, retries within policy, or requests operator action first.
10. **Bounded service restart:** Failed Factory services may restart automatically only within bounded retry and backoff rules.
11. **No blind task resume:** Task execution does not resume immediately after a service restart.
12. **Reconciled automatic resume:** A task may resume automatically after successful state reconciliation when policy permits and no approval, conflict, hold, or unknown state blocks it.
13. **Failure-class retry limits:** Recovery retry limits depend on the verified failure class and operation risk.
14. **Equivalent-failure counters:** Equivalent failures share one retry counter so superficial changes cannot disguise an infinite retry loop.
15. **Pre-restart evidence capture:** Evidence, logs, checkpoints, and failure context are secured before restart or termination when safely possible.
16. **Containment priority:** During immediate danger, containment overrides graceful evidence preservation.
17. **Transactional state journal:** Important state transitions use a durable transactional journal or equivalent mechanism that can detect incomplete operations after interruption.
18. **Idempotent recovery operations:** Recovery-sensitive operations are designed to be safely replayable without duplicating changes or damage.
19. **Expiring lock leases:** Task, resource, workspace, branch, model, sandbox, and promotion locks use expiring leases with ownership identity and renewal rules.
20. **Startup reconciliation:** Startup reconciles tasks, workstreams, sandboxes, branches, workspaces, processes, models, approvals, locks, journals, checkpoints, and pending promotions.
21. **Unknown-state blocking:** Unexplained or inconsistent state is not resumed automatically and enters `BLOCKED` or `QUARANTINED` review.
22. **Orphan cleanup:** Orphaned processes, containers, sandboxes, mounts, and temporary workspaces may be cleaned automatically only after identity, ownership, checkpoint, evidence, and hold checks pass.
23. **Startup integrity checks:** Factory verifies databases, journals, authoritative records, checkpoints, snapshots, evidence references, indexes, and material integrity links before normal operation.
24. **Degraded operation:** Failure of a noncritical subsystem may permit explicitly bounded degraded operation when unaffected capabilities remain safe and authoritative.
25. **Fail-closed core controls:** Failure of security, permission, identity, state-authority, evidence, audit, isolation, or promotion controls causes Factory to fail closed.
26. **Restricted Safe Mode:** Safe Mode permits inspection, evidence export, recovery, integrity checks, and approved repair, but not normal autonomous task execution or unrestricted writes.
27. **Watchdog audit:** Every Watchdog pause, containment, termination, restart, reconciliation, recovery, quarantine, and release action produces an integrity-protected audit record.
28. **No self-modifying Watchdog policy:** The Watchdog cannot modify its own rules, thresholds, permissions, or governing authority. Changes require the normal explicit architecture and approval process.
29. **Scheduled recovery drills:** Factory performs approved recovery drills during controlled idle testing.
30. **Release failure simulations:** Release verification includes applicable controlled crash, interruption, stalled-service, partial-write, and power-loss simulations.
31. **Restore-tested snapshots:** Recovery snapshots are periodically restored and verified in a controlled environment; successful creation alone is not sufficient proof.
32. **Factory-state-only restoration:** Snapshot restoration never overwrites or replaces GitHub project repositories. Recovery snapshots cover Factory state only.
33. **Low-storage protection:** Critically low storage blocks or pauses new work before databases, evidence, journals, checkpoints, or snapshots become unsafe.
34. **No emergency deletion of protected records:** Factory cannot delete protected evidence, audit records, checkpoints, holds, or authoritative memory merely to free storage. Cleanup remains governed by retention policy.
35. **Watchdog dependency for high-risk work:** Failure or loss of the Watchdog stops or blocks high-risk autonomous work until monitoring is restored and state is reconciled.
36. **Optional Windows auto-launch:** Windows startup launch is optional, user-controlled, and disabled by default.

## 3. Recovery operating boundaries

- The Watchdog may pause, contain, restart services, reconcile state, and restore the last approved state, but it cannot create new behavior or bypass approvals.
- Automatic task resumption occurs only after successful deterministic reconciliation.
- Unknown, corrupt, conflicting, or unexplained state fails closed.
- Recovery drills, failure simulations, and snapshot restore tests are required before release.
- GitHub remains authoritative for committed project source and history; Factory recovery snapshots cover Factory state only.
- Windows auto-launch remains a convenience option rather than a reliability dependency.

## 4. State reconciliation outcome

After restart, crash, interruption, or Watchdog intervention, each affected task receives one explicit state:

```text
RESUMABLE
BLOCKED
FAILED
QUARANTINED
COMPLETED
CANCELLED
```

A task is `RESUMABLE` only when its authoritative task record, last verified checkpoint, repository baseline, sandbox or replacement environment, locks, approvals, artifacts, and evidence agree. Factory must not infer resumability from a surviving process or workspace alone.

## 5. Acceptance criteria

This decision is satisfied only when tests prove that:

1. the Watchdog detects an unresponsive Orchestrator independently;
2. normal monitoring cannot silently alter project or Factory state;
3. missing heartbeats, execution stalls, repeated equivalent actions, and retry loops are detected under task-specific limits;
4. configured resource and thermal thresholds trigger the correct pause or containment action;
5. ordinary failures do not cause destructive termination without a critical trigger;
6. automatic service restarts stop at their bounded retry limit;
7. tasks cannot resume after restart until state reconciliation succeeds;
8. unknown or inconsistent state becomes `BLOCKED` or `QUARANTINED` rather than guessed;
9. transactional journals identify incomplete state transitions after interruption;
10. recovery operations can be replayed without duplicating changes;
11. expired locks cannot permanently deadlock Factory and cannot be stolen without ownership checks;
12. orphan cleanup cannot destroy resources protected by evidence, checkpoint, recovery, or retention holds;
13. startup integrity checks detect damaged databases, journals, records, snapshots, or evidence links before normal work begins;
14. noncritical failure permits only explicitly bounded degraded operation;
15. failure of core security, permission, authority, evidence, audit, isolation, or promotion controls fails closed;
16. Safe Mode cannot perform normal autonomous execution or unrestricted writes;
17. every Watchdog intervention produces a traceable integrity-protected audit record;
18. the Watchdog cannot modify its own governing rules;
19. controlled crash, interruption, and partial-write simulations demonstrate recovery behavior;
20. recovery snapshots are restore-tested and proven readable before release;
21. snapshot restoration cannot overwrite GitHub project repositories;
22. critically low storage pauses or blocks unsafe new work;
23. protected records cannot be automatically deleted for emergency storage recovery;
24. high-risk autonomous work cannot continue without an operational Watchdog;
25. Windows auto-launch remains disabled unless explicitly enabled by the user.