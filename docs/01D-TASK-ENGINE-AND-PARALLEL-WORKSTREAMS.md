# Approved Task Engine and Parallel Workstream Decision

**Status:** Approved architecture supplement  
**Recorded:** July 23, 2026  
**Clarified:** July 23, 2026

## 1. Approved execution baseline

Factory uses a maximum of three parallel major-stage workstreams by default. Each workstream owns an independent major stage and completes its full internal lifecycle:

```text
design -> implement -> test -> verify -> handoff
```

Parallel execution is allowed only when contracts, dependencies, data boundaries, ownership, resource reservations, and integration expectations are stable. Dependent work waits at defined gates rather than inventing unfinished interfaces.

Every executable task receives its own controlled task branch from an approved baseline. Every concurrently active lane modifying the same repository receives an isolated checkout: a Git worktree is preferred, while a separate clone is permitted when worktrees are unavailable or inappropriate.

The permanent separation of planning, implementation, and verification into different lanes is not Factory's normal operating model. That split may be used temporarily for one unusually large, complex, or high-risk stage.

## 2. Approved Stage 2 decisions

1. **Default active workstreams:** Factory supports no more than three active major workstreams by default.
2. **Configurable capacity:** The user may lower or raise the configured maximum when hardware and verified resource limits permit it.
3. **Independence check:** Factory must verify that proposed parallel stages are independent enough to run safely before starting them.
4. **Declared workstream contract:** Every workstream must declare its owner, scope, inputs, outputs, dependencies, owned contracts, and completion gate.
5. **Shared-file ownership:** Independent workstreams are not expected to edit the same file. Factory records file ownership and edit scope. When an overlap occurs, only one workstream may hold write ownership at a time; the other workstream must wait, hand off its required change, or resolve the overlap through the integration gate.
6. **Shared changes:** Cross-workstream changes to shared files, modules, schemas, APIs, migrations, configuration, or contracts must be coordinated through an integration gate.
7. **Git isolation:** Every executable task receives a controlled task branch. A stage integration branch is optional and is used only when multiple independently verified task branches must be combined. Separate lane branches exist only for approved parallel work.
8. **Isolated lane checkouts:** Every concurrently active lane modifying the same repository uses its own isolated checkout. Git worktrees are preferred; separate clones are permitted. A branch alone is not sufficient physical workspace isolation.
9. **Blocked work:** A blocked workstream may continue unrelated work that remains inside its approved scope and does not consume a blocked shared contract or dependency.
10. **Temporary mocks:** A temporary mock interface is allowed only with explicit approval, clear labeling, bounded scope, and a mandatory replacement gate. Every mock is marked `NON_PRODUCTION` and `NON_PROMOTABLE` and is excluded from integration, packaging, release artifacts, and production configuration until replaced and verified.
11. **Priority changes:** Workstream priorities may be adjusted while work is active through the deterministic scheduler policy.
12. **Deterministic resource balancing:** Factory uses configured resource ceilings, admission control, priority rules, starvation prevention, and checkpointed pause. Active work is never evicted without first preserving a verified checkpoint unless immediate containment is required.
13. **GPU-heavy work:** On the current 12 GB GPU, only one GPU-heavy model task runs at a time by default.
14. **CPU concurrency:** CPU-only work may continue while another workstream uses the GPU when configured Resource Scheduler limits permit it.
15. **Local verification gate:** A workstream must pass its own applicable verification gate before entering integration.
16. **Cross-workstream verification:** Factory must run integration tests after combining work from multiple workstreams.
17. **Evidence-backed integration remediation:** An integration failure creates a remediation task assigned to one or more owning lanes according to evidence. The integration gate may diagnose, block, and assign work but must never modify source code directly.
18. **Partial completion:** Verified successful work may be preserved when another workstream fails, but it cannot be promoted as an integrated system until required gates pass.
19. **Early merge:** Independently complete work may merge before other workstreams finish only when it preserves the shared baseline and does not bypass a dependency or integration gate.
20. **Follow-up tasks:** Factory may recommend follow-up tasks, but it must not create or execute them without approval.
21. **Evidence:** Each workstream produces its own evidence package, and combined work produces one integration evidence package.
22. **Recovery:** A failed workstream resumes from its last verified checkpoint rather than restarting from the beginning when safe.
23. **Repeated equivalent failures:** Quarantine occurs after three consecutive unresolved failures with the same normalized failure signature and probable root cause. Unrelated infrastructure failures and verified transient failures do not count toward that sequence.
24. **Adaptive parallelism:** Factory automatically reduces parallelism when resource limits, instability, or dependency conditions require it, using the deterministic interruption and admission rules below.
25. **Urgent interruption:** A higher-priority task may interrupt lower-priority work only through a verified checkpointed pause, never abrupt destructive termination except for immediate containment.

## 3. Binding lane and integration controls

### 3.1 Lane lifecycle

Each lane has a lane-specific lifecycle state:

```text
PROPOSED
APPROVED
READY
ACTIVE
BLOCKED
PAUSED
VERIFICATION
HANDOFF
INTEGRATED
CLOSED
FAILED
QUARANTINED
```

The minimum legal transitions are:

```text
PROPOSED -> APPROVED
APPROVED -> READY
READY -> ACTIVE | BLOCKED | FAILED | QUARANTINED
ACTIVE -> BLOCKED | PAUSED | VERIFICATION | FAILED | QUARANTINED
BLOCKED -> READY | ACTIVE | FAILED | QUARANTINED
PAUSED -> READY | ACTIVE | FAILED | QUARANTINED
VERIFICATION -> ACTIVE | HANDOFF | FAILED | QUARANTINED
HANDOFF -> ACTIVE | INTEGRATED | FAILED | QUARANTINED
INTEGRATED -> CLOSED | FAILED | QUARANTINED
FAILED -> READY | QUARANTINED | CLOSED
QUARANTINED -> BLOCKED | FAILED | CLOSED
```

Invalid transitions fail closed and create an audit event. Every transition records the prior state, new state, cause, actor or authoritative service, monotonic ordering, display timestamp, checkpoint, evidence, and applicable approval.

This lane lifecycle is a separate execution dimension that must remain consistent with the authoritative Stage 10 task and workstream state machine. A lane cannot be `ACTIVE` when its owning task is paused, cancelled, failed, quarantined, or rolled back.

### 3.2 Contract ownership

Every shared interface, schema, API, database migration, configuration contract, file format, and cross-lane dependency contract records:

- named owner;
- stable contract identifier and version;
- compatibility and deprecation rules;
- approved producers and consumers;
- frozen and mutable portions;
- approved change procedure;
- required local, integration, migration, compatibility, and regression tests;
- rollout and rollback behavior.

A lane cannot change a shared contract outside the approved change procedure. Consumers must not adopt an unpublished or unverified contract version.

### 3.3 Integration baseline

Every stage records one immutable integration baseline identity. It is either:

- the approved commit from which all participating task branches begin; or
- a protected stage integration branch plus its exact approved commit when multiple verified branches are being combined.

A lane cannot silently rebase, merge, or change its baseline during execution. A baseline change requires a recorded dependency update, impact analysis, affected-lane approval, and re-verification of invalidated work.

### 3.4 Conflict detection beyond files

Before parallel admission and again before integration, Factory detects and blocks unresolved conflicts involving:

- overlapping module or component ownership;
- shared symbol or logical behavior changes across different files;
- schema and serialization changes;
- API or interface incompatibility;
- database migration ordering or identifier conflicts;
- configuration-key, default, or environment conflicts;
- dependency-version conflicts;
- shared generated outputs;
- cross-file invariants and logical conflicts.

File-path disjointness alone is not proof of independence.

### 3.5 Priority and interruption policy

The versioned scheduler policy uses these launch defaults:

- Critical atomic operations, journal commits, promotion commits, migration commits, and recovery transitions are non-preemptible once their commit boundary begins.
- A normal preemptible lane must reach and verify a checkpoint within **5 minutes** of an interruption request.
- A task contract may authorize up to **15 minutes** for a declared long-running safe-boundary operation. Longer uncheckpointable work requires separate approval before start.
- Waiting work receives one starvation-priority increase after **15 minutes** and guaranteed admission to the next eligible resource slot after **30 minutes**, unless blocked by safety, dependency, approval, or hard resource constraints.
- Priority inversion is resolved by temporarily raising the priority of the lane holding the required bounded resource or contract, without expanding its scope.
- Resume order is: containment and recovery work; interrupted critical or higher-priority work; the oldest verified checkpoint at the same priority; then normal FIFO admission.

Failure to produce a checkpoint within the permitted duration moves the lane to `BLOCKED` or `QUARANTINED` according to integrity status rather than forcing unsafe eviction.

### 3.6 Verified checkpoint contents

A verified lane checkpoint contains at least:

- Project, Task, stage, workstream, and lane IDs;
- source repository identity and exact source commit;
- task branch and isolated checkout identity;
- complete working diff or deterministic workspace-state identity;
- dependency, contract, model, tool, and environment versions;
- completed tests and results;
- pending tests, commands, approvals, integrations, and external actions;
- produced artifact identities and hashes;
- resource and lease state;
- unresolved failures and blockers;
- exact resume instructions and next valid operation;
- checkpoint evidence and integrity hash.

A checkpoint is not verified merely because files were saved.

### 3.7 Normalized failure identity

Equivalent-failure classification uses normalized fields including component, operation, phase, stable error code, affected resource, causal signature, and probable root cause. Volatile timestamps, worker IDs, retry numbers, and regenerated wording are excluded.

The three-failure quarantine sequence resets only when deterministic evidence proves a materially different cause or an excluded transient or infrastructure failure. The normalization and exclusion decision are recorded.

### 3.8 Integration-gate authority

The integration gate may:

- compare baselines and manifests;
- validate ownership and contracts;
- combine already approved commits through the Promotion or Integration Service;
- run integration verification;
- identify conflicts and probable owners;
- create an evidence-backed remediation proposal.

It cannot edit source, resolve conflicts by writing code, change tests, weaken contracts, or silently assign blame. Remediation work returns to one or more named owning lanes through an approved task.

## 4. Selectable real-time model testing

The operator may select a real-time model-testing mode for observing model behavior, routing, latency, resource use, and lane coordination.

This mode must run inside an isolated disposable sandbox. It cannot write to live project files, bypass normal permissions, or promote results without the normal verification and approval gates.

## 5. Operating boundaries

- Three major workstreams remain the default maximum.
- Every executable task has a controlled task branch; every concurrent same-repository lane has an isolated checkout.
- Shared contracts have explicit ownership, versions, compatibility rules, consumers, change procedures, and regression tests.
- Mocks remain non-production and non-promotable until replaced and verified.
- Resource balancing is deterministic, checkpointed, starvation-aware, and evidence-backed.
- The integration gate never writes source code.
- File disjointness alone does not prove lane independence.

## 6. Acceptance criteria

This decision is satisfied only when tests prove that:

1. Factory does not exceed the configured active-workstream limit;
2. parallel execution is blocked when contracts, dependencies, ownership, baselines, or resources are unstable;
3. every workstream has declared scope, ownership, inputs, outputs, contracts, and completion gates;
4. every executable task receives a controlled task branch from an approved baseline;
5. concurrent lanes modifying the same repository cannot share one writable checkout;
6. worktree or separate-clone isolation prevents cross-lane workspace contamination;
7. two workstreams cannot hold simultaneous write ownership over the same file or incompatible logical scope;
8. module, schema, API, migration, configuration, dependency, and cross-file logical conflicts are detected before integration;
9. shared-contract changes cannot bypass owner, version, compatibility, consumer, procedure, and regression requirements;
10. lanes cannot silently change their recorded integration baseline;
11. only legal lane lifecycle transitions occur and every transition is auditable;
12. temporary mocks cannot enter integration, packaging, release, or production output before replacement and verification;
13. configured resource ceilings and admission controls prevent overcommit;
14. interruption preserves a verified checkpoint before eviction unless immediate containment applies;
15. checkpoint deadlines, starvation controls, priority inversion handling, and resume order follow the versioned scheduler policy;
16. verified checkpoints contain the required source, diff, dependency, test, environment, artifact, pending-operation, and resume evidence;
17. GPU-heavy concurrency is limited by the verified hardware policy while safe CPU-only work may continue;
18. each participating workstream passes applicable local verification before integration;
19. cross-workstream integration tests run before promotion;
20. integration failures create evidence-backed remediation assigned to named owning lanes;
21. the integration gate cannot modify source code directly;
22. successful partial work remains preserved but unpromoted until required gates pass;
23. follow-up and remediation tasks cannot execute without approval;
24. three consecutive failures with the same normalized signature and probable root cause trigger quarantine;
25. unrelated infrastructure and verified transient failures do not incorrectly advance the equivalent-failure counter;
26. urgent work interrupts lower-priority work only through a verified checkpointed pause;
27. real-time model testing remains sandboxed and cannot modify or promote live project state directly.