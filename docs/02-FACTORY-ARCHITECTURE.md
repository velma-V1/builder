# Factory Architecture

**Status:** Approved high-level architecture  
**Recorded:** July 23, 2026

## 1. System shape

```text
Builder Dashboard — primary interface
├── Built-in project file explorer
├── Built-in Monaco code editor
├── Controlled terminal and preview
├── Tasks, diffs, tests, evidence, approvals, checkpoints, rollback, and graphs
└── Optional IDE adapter — disabled by default
        |
        v
Deterministic Control Plane
├── Versioned contract loader
├── Queue and state machine
├── Watchdog and permission gates
├── Model and coding-worker router
├── Safe file-operation service
├── Git, worktree, and sandbox manager
├── Evidence and audit ledger
├── Transactional runtime-state store
└── Serialized integration coordinator
        |
        +---------------- Primary local path ----------------+
        |                                                    |
        v                                                    v
Aider coding-worker adapter                          Ollama runtime adapter
        |                                            ├── qwen3:8b
        +-------------------- Ollama -----------------└── qwen3:14b
        |
        +---------------- Optional secondary capacity ----------------+
        |                         |                                    |
        v                         v                                    v
     Lane 1                    Lane 2                               Lane 3
 Worker/Reviewer            Worker/Reviewer                     Worker/Reviewer
 branch/worktree            branch/worktree                     branch/worktree
 sandbox                    sandbox                             sandbox
        |                         |                                    |
        +-------------------------+------------------------------------+
                                  |
                                  v
                      Deterministic Integration Gates
                                  |
                                  v
                     Verified package or recovery path
```

## 2. Primary interface

The Builder Dashboard is the normal Factory development environment.

The built-in file explorer and Monaco editor must provide enough functionality for routine repository inspection, editing, coding-worker interaction, testing, review, and recovery without requiring an external IDE.

Dashboard components are clients of the control plane. They cannot directly grant authority, modify authoritative runtime state, bypass file protections, or certify completion.

## 3. IDE independence

Factory core must not depend on VS Code, Codex, OpenHands, or another IDE or agent application.

A disabled-by-default IDE adapter may later connect VS Code or another external editor through a narrow permission-controlled interface. Removing or disabling the adapter must not affect normal Factory operation.

OpenHands is deferred beyond v1. Codex is not a required dependency.

## 4. Control plane

The control plane is deterministic Python software. It remains active while approved work exists and owns every authoritative state transition.

It must never depend on a model or coding worker to remember critical state. Approved intent is loaded from versioned contracts. Live state includes tasks, lanes, queues, dependencies, checkpoints, commands, model calls, coding-worker calls, quota usage, test results, evidence, approvals, failures, recoveries, and integration records.

The watchdog is the sole authoritative writer to the runtime-state database. The Dashboard, Aider, models, lanes, tools, and IDE adapters submit commands or appendable events through controlled interfaces instead of directly modifying shared state.

> **Amended by `docs/01R` (R1), 2026-07-24:** the sole authoritative writer is the **Orchestrator**; the Watchdog is the separate, normally read-only supervisor (`01M`).

## 5. Contract system

The Factory uses seven small linked contract families:

1. Project Contract
2. Requirement Contract
3. Task Contract
4. Ownership Contract
5. Permission Contract
6. Evidence Contract
7. Change Contract

Contracts are versioned, Git-tracked repository files treated as code. They remain readable by humans and models, schema-validated, diffable, reviewable, and tied to approval history.

Every coding task receives linked machine-readable contracts containing at least:

- unique project and task identifiers;
- parent requirement identifiers;
- objective and expected deliverable;
- owned and forbidden paths;
- frozen interfaces and dependencies;
- permitted tools, coding workers, model routes, network access, and environment;
- applicable tests and evidence;
- resource, retry, file, time, and model limits;
- approval requirements;
- recovery and escalation behavior;
- completion conditions.

## 6. Runtime-state database

High-frequency execution state is stored in SQLite using WAL mode, foreign-key enforcement, explicit transactions, migrations, integrity checks, and controlled backups.

The runtime database stores at least:

- project-run and task-instance state;
- lane and local-worker status, ownership leases, and heartbeats;
- queue order and dependency readiness;
- current Worker, Reviewer, Aider, and model-route assignments;
- provider and Ollama availability and degradation state;
- request, input-token, output-token, quota, and retry counters;
- approval, checkpoint, rollback, and integration references;
- append-only audit and state-transition events;
- failure, recovery, and escalation records.

A storage abstraction prevents watchdog logic from depending directly on SQLite. Runtime database files, WAL files, and local backups remain local and are never committed. Database schemas and migrations are committed.

## 7. Transaction rule

Every authoritative state transition must be atomic.

A transition transaction must validate the expected current state, apply the new state, update related counters or leases, append its audit event, and commit as one operation. Failure rolls back the entire transition.

Token or request totals may be corrected after a runtime or provider returns final usage, but estimated and final values must remain distinguishable and auditable.

## 8. Primary local coding path

Ollama is the permanent local model runtime. Aider connected to Ollama is the primary local coding worker for v1.

Aider must operate through a coding-worker adapter and receive only:

- validated task contracts;
- bounded repository context;
- owned paths;
- approved commands and environment;
- abstract model route resolved to an approved Ollama model;
- resource, retry, and time limits;
- required tests and evidence.

Aider may propose and implement changes inside its task boundary. It cannot assign itself work, expand scope, alter protected state, approve deletions, weaken evidence, merge protected branches, publish, release, or mark work complete.

The coding-worker adapter must be replaceable so a future approved worker, including a possible OpenHands adapter, can use the same control boundary without becoming a second authority.

## 9. Ollama runtime boundary

The Ollama adapter is responsible for health checks, exact-model discovery, local request execution, cancellation, error reporting, resource-aware routing, and usage records.

The Factory must remain capable of basic operation when every hosted provider is unavailable. A second local runtime is not required for v1.

## 10. Lane boundary

A lane is a controlled execution unit, not an independent authority.

The Worker implements the bounded task. The Reviewer receives fresh context containing the contract, diff, test results, and evidence. It returns `APPROVE`, `REVISE`, or `STOP` with explicit findings.

The watchdog validates the verdict against deterministic evidence. Reviewer approval cannot bypass failed tests, missing evidence, scope violations, security gates, or permission limits.

The three approved hosted lanes remain optional secondary capacity. Their unavailability cannot prevent normal Aider + Ollama local work.

## 11. Parallelism rule

Three lanes or local worker instances may run concurrently only when:

- their owned paths are disjoint;
- shared interfaces are frozen;
- dependency direction is known;
- each task can be independently tested;
- no worker controls a shared migration, global manifest, or protected configuration file.

Tasks that violate these conditions enter the serialized integration queue.

## 12. Model and worker routing

The router selects only approved coding workers and model routes. Selection considers task type, demonstrated capability, privacy, context size, tool reliability, Ollama and provider availability, quota, current local load, and evidence quality.

The default routing order is:

1. use Aider with an approved Ollama model for suitable local coding work;
2. use local Qwen supervision, planning, review, or recovery as assigned;
3. use an approved hosted Worker or Reviewer only when permitted and beneficial;
4. fall back to the approved local path when hosted capacity is unavailable or privacy requires local execution;
5. pause only the affected task rather than silently selecting an unapproved worker, model, runtime, or IDE.

Provider, Ollama, Aider, and token/request state are written through watchdog transactions so routing decisions use current auditable information.

## 13. File and editor boundary

The Dashboard file explorer and Monaco editor use the safe file-operation service.

Every read or write must respect project root, ownership, read-only, forbidden, protected, generated, disposable, symlink, junction, reparse-point, case, and Windows path rules.

Monaco save actions and Aider edits enter the same policy, checkpoint, diff, evidence, and rollback pipeline. Neither interface receives a bypass path.

## 14. Git and sandbox boundary

Every task uses an isolated branch and worktree where practical. Execution occurs in a disposable Docker environment through WSL2 unless the approved task requires a restricted Windows-native environment.

> **Amended by `docs/01R` (Decision C), 2026-07-24:** for v1 the Windows-native exception does not apply — execution is WSL2 + Docker only.

No worker, model, Dashboard panel, or IDE adapter receives unrestricted host access. Project mounts, network access, secrets, devices, capabilities, commands, and resource limits are explicitly granted by contract.

## 15. Integration flow

A completed worker or lane produces an integration package containing:

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

## 16. Recovery principle

Failure does not erase evidence. Every failed attempt remains traceable. Recovery returns to the last verified safe checkpoint, corrects the contract or implementation, and restarts within bounded limits.

Database recovery must validate transaction integrity, migration version, and checkpoint references before work resumes. Repository and runtime checkpoints must be reconciled.

## 17. Completion principle

No task, worker, lane, integration, project, package, or release is complete because Aider, a model, an IDE, or a reviewer says it is complete. Completion is a deterministic database state reached only when the linked contracts and applicable evidence gates pass.