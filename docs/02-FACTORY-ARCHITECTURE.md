# Factory Architecture

**Status:** Approved high-level architecture  
**Recorded:** July 22, 2026

## 1. System shape

```text
User and Dashboard
        |
        v
Deterministic Control Plane
├── Versioned contract loader
├── Queue and state machine
├── Watchdog and permission gates
├── Model and quota router
├── Git, worktree, and sandbox manager
├── Evidence and audit ledger
├── Transactional runtime-state store
└── Serialized integration coordinator
        |
        +------------------+------------------+
        |                  |                  |
        v                  v                  v
     Lane 1             Lane 2             Lane 3
  Worker/Reviewer    Worker/Reviewer    Worker/Reviewer
  branch/worktree    branch/worktree    branch/worktree
  sandbox            sandbox            sandbox
        |                  |                  |
        +------------------+------------------+
                           |
                           v
               Deterministic Integration Gates
                           |
                           v
              Verified package or recovery path
```

## 2. Control plane

The control plane is deterministic Python software. It remains active while approved work exists and owns every authoritative state transition.

It must never depend on a model to remember critical state. Approved intent is loaded from versioned contracts. Live state includes tasks, lanes, queues, dependencies, checkpoints, commands, model calls, quota usage, test results, evidence, approvals, failures, recoveries, and integration records.

The watchdog is the sole authoritative writer to the runtime-state database. Lanes, models, tools, and dashboard processes submit commands or appendable events through controlled interfaces instead of directly modifying shared state.

## 3. Contract system

The Factory uses seven small linked contract families:

1. Project Contract
2. Requirement Contract
3. Task Contract
4. Ownership Contract
5. Permission Contract
6. Evidence Contract
7. Change Contract

Contracts are versioned, Git-tracked repository files treated as code. They remain readable by humans and models, schema-validated, diffable, reviewable, and tied to approval history.

Every lane task must eventually receive linked machine-readable contracts containing at least:

- unique project and task identifiers;
- parent requirement identifiers;
- objective and expected deliverable;
- owned and forbidden paths;
- frozen interfaces and dependencies;
- permitted tools, network access, and environment;
- applicable tests and evidence;
- resource, retry, file, time, and model limits;
- approval requirements;
- recovery and escalation behavior;
- completion conditions.

The exact schemas are designed in Build Section 1.

## 4. Runtime-state database

High-frequency execution state is stored in SQLite using WAL mode, foreign-key enforcement, explicit transactions, migrations, integrity checks, and controlled backups.

The runtime database stores at least:

- project-run and task-instance state;
- lane status, ownership leases, and heartbeats;
- queue order and dependency readiness;
- current Worker and Reviewer assignments;
- provider availability and degradation state;
- request, input-token, output-token, quota, and retry counters;
- approval, checkpoint, rollback, and integration references;
- append-only audit and state-transition events;
- failure, recovery, and escalation records.

A storage abstraction prevents watchdog logic from depending directly on SQLite. This preserves a controlled future path to PostgreSQL without changing approved contracts or state-machine semantics.

Runtime database files, WAL files, and local backups remain local and are never committed. Database schemas and migrations are committed.

## 5. Transaction rule

Every authoritative state transition must be atomic.

A transition transaction must validate the expected current state, apply the new state, update related counters or leases, append its audit event, and commit as one operation. Failure rolls back the entire transition.

Token or request totals may be corrected after a provider returns final usage, but estimated and final values must remain distinguishable and auditable.

## 6. Lane boundary

A lane is a controlled execution unit, not an independent authority.

The Worker implements the bounded task. The Reviewer receives fresh context containing the contract, diff, test results, and evidence. It returns `APPROVE`, `REVISE`, or `STOP` with explicit findings.

The watchdog validates the verdict against deterministic evidence. Reviewer approval cannot bypass failed tests, missing evidence, scope violations, security gates, or permission limits.

A lane cannot directly alter task state, shared token totals, quota state, another lane's ownership, or completion status.

## 7. Parallelism rule

Three lanes may run concurrently only when:

- their owned paths are disjoint;
- shared interfaces are frozen;
- dependency direction is known;
- each task can be independently tested;
- no lane controls a shared migration, global manifest, or protected configuration file.

Tasks that violate these conditions enter the serialized integration queue.

## 8. Model routing

The router selects only approved models. Selection considers task type, demonstrated capability, privacy, context size, tool reliability, provider availability, quota, current local load, and evidence quality.

The routing order is:

1. assign suitable work to the lane Worker;
2. route difficult work and independent review to the lane Reviewer;
3. allow Reviewer takeover when the Worker is unavailable or unsuitable;
4. use local Qwen fallback when hosted capacity is unavailable or privacy requires local execution;
5. pause the task rather than silently selecting an unapproved model.

Provider usage and token counts are written through watchdog transactions before and after each call so routing decisions use current auditable state.

## 9. Git and sandbox boundary

Every task uses an isolated branch and worktree where practical. Execution occurs in a disposable Docker environment through WSL2 unless the approved task requires a restricted Windows-native environment.

No lane receives unrestricted host access. Project mounts, network access, secrets, devices, capabilities, commands, and resource limits are explicitly granted by contract.

## 10. Integration flow

A completed lane produces an integration package containing:

- linked task contracts;
- base and head commit identifiers;
- exact diff and changed-file list;
- Worker and Reviewer records;
- commands executed;
- unit and component test results;
- security and scope checks;
- unresolved limitations;
- checkpoint and rollback references.

The integration coordinator serializes shared changes, runs cross-component tests, and either advances the project or starts recovery.

## 11. Recovery principle

Failure does not erase evidence. Every failed attempt remains traceable. Recovery returns to the last verified safe checkpoint, corrects the contract or implementation, and restarts within bounded limits.

Database recovery must validate transaction integrity, migration version, and checkpoint references before work resumes. Database restoration cannot independently roll repository state forward or backward; repository and runtime checkpoints must be reconciled.

## 12. Completion principle

No task, lane, integration, project, package, or release is complete because a model says it is complete. Completion is a deterministic database state reached only when the linked contracts and applicable evidence gates pass.