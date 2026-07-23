# Factory Architecture

**Status:** Approved high-level architecture  
**Recorded:** July 22, 2026

## 1. System shape

```text
User and Dashboard
        |
        v
Deterministic Control Plane
├── Requirements and task contracts
├── Queue and state machine
├── Watchdog and permission gates
├── Model and quota router
├── Git, worktree, and sandbox manager
├── Evidence and audit ledger
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

The control plane is deterministic Python software. It remains active while approved work exists and owns every state transition.

It must never depend on a model to remember critical state. Durable state includes task contracts, ownership, checkpoints, commands, model calls, quota usage, test results, evidence, approvals, failures, recoveries, and integration records.

## 3. Task contract

Every lane task must eventually receive a machine-readable contract containing at least:

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

The exact schema is designed in Build Section 1.

## 4. Lane boundary

A lane is a controlled execution unit, not an independent authority.

The Worker implements the bounded task. The Reviewer receives fresh context containing the contract, diff, test results, and evidence. It returns `APPROVE`, `REVISE`, or `STOP` with explicit findings.

The watchdog validates the verdict against deterministic evidence. Reviewer approval cannot bypass failed tests, missing evidence, scope violations, security gates, or permission limits.

## 5. Parallelism rule

Three lanes may run concurrently only when:

- their owned paths are disjoint;
- shared interfaces are frozen;
- dependency direction is known;
- each task can be independently tested;
- no lane controls a shared migration, global manifest, or protected configuration file.

Tasks that violate these conditions enter the serialized integration queue.

## 6. Model routing

The router selects only approved models. Selection considers task type, demonstrated capability, privacy, context size, tool reliability, provider availability, quota, current local load, and evidence quality.

The routing order is:

1. assign suitable work to the lane Worker;
2. route difficult work and independent review to the lane Reviewer;
3. allow Reviewer takeover when the Worker is unavailable or unsuitable;
4. use local Qwen fallback when hosted capacity is unavailable or privacy requires local execution;
5. pause the task rather than silently selecting an unapproved model.

## 7. Git and sandbox boundary

Every task uses an isolated branch and worktree where practical. Execution occurs in a disposable Docker environment through WSL2 unless the approved task requires a restricted Windows-native environment.

No lane receives unrestricted host access. Project mounts, network access, secrets, devices, capabilities, commands, and resource limits are explicitly granted by contract.

## 8. Integration flow

A completed lane produces an integration package containing:

- task contract;
- base and head commit identifiers;
- exact diff and changed-file list;
- Worker and Reviewer records;
- commands executed;
- unit and component test results;
- security and scope checks;
- unresolved limitations;
- rollback point.

The integration coordinator serializes shared changes, runs cross-component tests, and either advances the project or starts recovery.

## 9. Recovery principle

Failure does not erase evidence. Every failed attempt remains traceable. Recovery returns to the last verified safe checkpoint, corrects the contract or implementation, and restarts within bounded limits.

## 10. Completion principle

No task, lane, integration, project, package, or release is complete because a model says it is complete. Completion is a deterministic state reached only when the applicable contract and evidence gates pass.