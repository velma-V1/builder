# Approved Task Engine and Parallel Workstream Decision

**Status:** Approved architecture supplement  
**Recorded:** July 23, 2026

## 1. Approved execution baseline

Factory uses a maximum of three parallel major-stage workstreams by default. Each workstream owns an independent major stage and completes its full internal lifecycle:

```text
design -> implement -> test -> verify -> handoff
```

Parallel execution is allowed only when contracts, dependencies, data boundaries, and integration expectations are stable. Dependent work waits at defined gates rather than inventing unfinished interfaces.

The permanent separation of planning, implementation, and verification into different lanes is not Factory's normal operating model. That split may be used temporarily for one unusually large, complex, or high-risk stage.

## 2. Approved Stage 2 decisions

1. **Default active workstreams:** Factory supports no more than three active major workstreams by default.
2. **Configurable capacity:** The user may lower or raise the configured maximum when hardware and verified resource limits permit it.
3. **Independence check:** Factory must verify that proposed parallel stages are independent enough to run safely before starting them.
4. **Declared workstream contract:** Every workstream must declare its owner, scope, inputs, outputs, dependencies, and completion gate.
5. **Shared-file ownership:** Independent workstreams are not expected to edit the same file. Factory records file ownership and edit scope. When an overlap occurs, only one workstream may hold write ownership at a time; the other workstream must wait, hand off its required change, or resolve the overlap through the integration gate. Factory does not impose extra isolation merely because multiple documented workstreams exist.
6. **Shared changes:** Cross-workstream changes to shared files or contracts must be coordinated through an integration gate.
7. **Git isolation:** The default is one Git branch per major stage, not one branch per lane. A separate lane branch is required only when concurrent lanes operate in the same repository and need independent edit isolation or rollback. When workstreams do not share repository edit scope, Factory's internal ownership, evidence, and lane records are sufficient.
8. **Worktrees:** A Git worktree is used only when concurrent workstreams operate on the same repository and physical workspace isolation is beneficial.
9. **Blocked work:** A blocked workstream may continue unrelated work that remains inside its approved scope.
10. **Temporary mocks:** A temporary mock interface is allowed only with explicit approval, clear labeling, bounded scope, and a mandatory replacement gate before promotion.
11. **Priority changes:** Workstream priorities may be adjusted while work is active.
12. **Resource balancing:** Factory may rebalance CPU, RAM, GPU, storage I/O, and model access using bounded deterministic rules.
13. **GPU-heavy work:** On the current 12 GB GPU, only one GPU-heavy model task runs at a time by default.
14. **CPU concurrency:** CPU-only work may continue while another workstream uses the GPU when verified resource limits permit it.
15. **Local verification gate:** A workstream must pass its own applicable verification gate before entering integration.
16. **Cross-workstream verification:** Factory must run integration tests after combining work from multiple workstreams.
17. **Failed integration ownership:** A failed integration returns the issue to the responsible workstream or an explicitly assigned integration task; the gate must not silently rewrite owned work.
18. **Partial completion:** Verified successful work may be preserved when another workstream fails, but it cannot be promoted as an integrated system until required gates pass.
19. **Early merge:** Independently complete work may merge before other workstreams finish only when it preserves the shared baseline and does not bypass a dependency or integration gate.
20. **Follow-up tasks:** Factory may recommend follow-up tasks, but it must not create or execute them without approval.
21. **Evidence:** Each workstream produces its own evidence package, and combined work produces one integration evidence package.
22. **Recovery:** A failed workstream resumes from its last verified checkpoint rather than restarting from the beginning when safe.
23. **Repeated failures:** Three equivalent unresolved failures trigger quarantine and operator review.
24. **Adaptive parallelism:** Factory automatically reduces parallelism when resource limits, instability, or dependency conditions require it.
25. **Urgent interruption:** A higher-priority task may interrupt lower-priority work only through a verified checkpointed pause, never abrupt destructive termination.

## 3. Selectable real-time model testing

The operator may select a real-time model-testing mode for observing model behavior, routing, latency, resource use, and lane coordination.

This mode must run inside an isolated disposable sandbox. It cannot write to live project files, bypass normal permissions, or promote results without the normal verification and approval gates.

## 4. Acceptance criteria

This decision is satisfied only when tests prove that:

1. Factory does not exceed the configured active-workstream limit;
2. parallel execution is blocked when contracts or dependencies are unstable;
3. every workstream has declared scope, ownership, inputs, outputs, and completion gates;
4. two workstreams cannot hold simultaneous write ownership over the same file;
5. shared-file overlap is resolved by waiting, handoff, or an integration gate rather than silent concurrent editing;
6. Factory does not require a separate Git branch merely because a documented lane exists;
7. separate lane branches are created when same-repository concurrent editing requires isolation or independent rollback;
8. worktrees are conditional rather than mandatory;
9. GPU-heavy concurrency is limited by the verified hardware policy while safe CPU-only work may continue;
10. each participating workstream passes applicable local verification before integration;
11. cross-workstream integration tests run before promotion;
12. integration failures return to an explicitly responsible owner;
13. successful partial work remains preserved but unpromoted until required gates pass;
14. follow-up tasks cannot be created or executed without approval;
15. repeated equivalent failures trigger quarantine after the third failure;
16. urgent work interrupts lower-priority work only through a verified checkpointed pause;
17. real-time model testing remains sandboxed and cannot modify or promote live project state directly.