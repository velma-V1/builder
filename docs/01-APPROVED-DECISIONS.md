# Approved Factory Decisions

**Status:** Approved supplement to `PROJECT_DEFINITION.md`  
**Recorded:** July 22, 2026

This file records decisions made after the original project definition. It supersedes only the specific previously open items named here. All other governing requirements remain unchanged.

## 1. Project boundary

The Factory is a standalone system. It is not Rabbit Hole, VELMA, or any other product it may later build. Project-specific requirements do not enter Factory architecture unless explicitly approved.

## 2. Permanent three-lane structure

> **Amended by `docs/01R` (R2), 2026-07-24:** superseded — the default execution unit is up to three parallel major-stage *workstreams* (`01D`); permanent Worker/Reviewer lanes are optional secondary capacity and a temporary special case.

The Factory has three permanent parallel execution lanes.

Each lane contains:

- one Worker model;
- one Reviewer model;
- one isolated task branch and worktree;
- one disposable execution environment;
- one bounded task contract;
- deterministic tests and evidence gates.

The lanes work on three separate components at the same time only when file ownership and interfaces do not conflict.

## 3. Deterministic authority

> **Amended by `docs/01R` (R1), 2026-07-24:** the sole authoritative state writer is the **Orchestrator** (deterministic control-plane engine); the **Watchdog** is a separate, normally read-only supervisor (`01M`). Read "watchdog … authority/writer" below as the Orchestrator.

The deterministic watchdog and state machine are the actual authority.

Models may plan, implement, diagnose, review, summarize, and recommend. Models may not independently declare that requirements, tests, security checks, or completion evidence have passed.

The watchdog controls:

- task states;
- lane assignment;
- scope and path ownership;
- permissions;
- model routing;
- quota and availability tracking;
- retry limits;
- checkpoints and rollback;
- test and evidence requirements;
- integration order;
- completion, recovery, escalation, and stop decisions.

## 4. Local supervision

The approved local models are:

- `qwen3:8b` — fast local dispatcher, task-packet preparation, summaries, classification, log compression, and routine fallback work.
- `qwen3:14b` — local judgment supervisor, difficult planning, escalation review, architecture review, and stronger local fallback.

Local operation remains available when hosted providers are unavailable. Local model output remains subject to deterministic verification.

## 5. Hosted model lanes

The hosted providers are Groq, Cerebras, and NVIDIA. Exact approved assignments are recorded in `docs/03-MODEL-ROSTER.md`.

Within each provider lane:

1. the lower-cost or lesser task-fit Worker handles suitable light and medium implementation work;
2. the stronger Reviewer handles difficult work, independent review, and takeover when the Worker is unavailable or unsuitable;
3. provider exhaustion or outage falls back through the approved local path;
4. no new model may be silently substituted for an approved model.

GLM-4.7 is not part of the Factory roster.

## 6. Parallel-work boundaries

Before parallel work starts:

- shared contracts are frozen;
- each lane receives exclusive component paths;
- shared schemas, dependency manifests, database migrations, global configuration, and integration-sensitive files are assigned to serialized integration work;
- a lane may not edit another lane's owned paths without a new task contract.

## 7. Scope-drift recovery

Scope drift is normally a recoverable fault, not a final stop condition.

The Factory must:

1. pause the affected lane;
2. preserve the task log, diff, commands, and evidence;
3. identify the first unsafe or out-of-scope change;
4. return to the last verified safe checkpoint;
5. narrow or correct the task contract;
6. restart from that checkpoint;
7. escalate only when requirements remain ambiguous or drift repeats beyond the approved retry limit.

## 8. Integration authority

Lane approval means only that a lane package is ready for deterministic integration checks. It does not authorize merge to the protected branch or release.

Shared integration work is serialized. A project is complete only after applicable integration, regression, failure-path, security, installation, launch, packaging, documentation, and evidence gates pass.

## 9. Availability and substitution rule

Provider model availability must be checked through the provider's model-list or capability endpoint at runtime.

When an approved model is temporarily unavailable:

1. use the paired approved model when its role and remaining quota permit;
2. use the approved local fallback path;
3. pause only the affected task if no approved path can safely perform it.

The Factory must not silently replace a removed, deprecated, unavailable, or exhausted model with an unapproved model.

## 10. Planning order

The Factory will be planned and built in eight locked sections:

1. Requirements and contracts
2. Task queue and state machine
3. Deterministic watchdog
4. Model routing and quotas
5. Git/worktree and sandbox isolation
6. Three Worker–Reviewer lanes
7. Testing, evidence, integration, and recovery
8. Dashboard, packaging, and installation

Each section must be divided into small, independently testable tasks before implementation begins.

## 11. Automatic sandbox permissions

Inside a disposable sandbox explicitly approved for the current task, the Factory may automatically:

- create files;
- edit files within the task's owned paths;
- install task-required dependencies within the disposable environment.

The Factory must request user approval before deleting files.

These permissions do not authorize edits outside owned paths, host-level dependency installation, persistent system changes, cloud data transfer, publishing, release, merge to a protected branch, architecture changes, or security-policy changes.

## 12. Automatic checkpoint commits

The Factory may automatically create local checkpoint commits on the task's isolated branch when:

- the commit contains only the task's owned paths;
- the exact changed-file list is recorded;
- applicable checkpoint tests and scope checks pass;
- the commit is labeled as an automatic checkpoint;
- the parent checkpoint and rollback path are recorded.

Automatic checkpoint commits do not authorize:

- merging into `main` or another protected branch;
- publishing or releasing;
- pushing to an unapproved remote;
- changing approved architecture or security policy.

The Factory must request user approval before merging into `main` or producing a release.

## 13. Task completion gate

A task may enter `COMPLETE` only when every requirement in its approved task contract and every applicable deterministic evidence gate passes.

The completion decision must confirm at least:

- all required deliverables exist;
- all owned-path and forbidden-path checks pass;
- required tests pass in the approved environment;
- required failure-path, security, regression, visual, installation, or launch evidence passes when applicable;
- Worker and Reviewer records are present;
- unresolved findings are either cleared or accurately classified as permitted limitations;
- the exact changed-file list, commands, test results, checkpoint, and rollback path are recorded;
- no required approval remains outstanding.

Worker approval, Reviewer approval, model agreement, a passing subset of tests, or an apparently working result cannot independently mark a task complete.

When any applicable contract requirement or evidence gate fails, the task must remain active, enter controlled recovery, or be accurately classified as blocked, escalated, or stopped.

## 14. Section 1 contract architecture

Section 1 will use small linked contracts rather than one oversized contract.

The contract family will separate:

- project intake and project identity;
- requirements and traceability;
- bounded task execution;
- path ownership and file boundaries;
- permissions and approvals;
- required evidence and completion;
- approved changes and scope revisions.

All contracts will share stable identifiers, version fields, provenance, status, and references to related contracts. Each contract will have one clear responsibility and will be independently schema-validated.

## 15. Hybrid contract and runtime-state storage

The Factory will use a hybrid architecture:

- approved contracts are versioned, Git-tracked repository files treated as code;
- high-frequency live execution state is stored in a transactional SQLite database running in WAL mode;
- the deterministic watchdog is the sole authoritative database writer;
- lanes, models, tools, and dashboard components submit commands or events and do not directly mutate authoritative shared state.

The repository contracts remain the human- and model-readable source of approved intent, scope, permissions, evidence requirements, and change history.

The runtime database stores at least:

- task, lane, queue, and dependency state;
- current model assignments and provider availability;
- request, token, quota, and retry counters;
- watchdog heartbeats and leases;
- approval and checkpoint references;
- append-only audit events;
- failures, recoveries, and integration state.

State transitions and related counter updates must occur transactionally. Database schemas and migrations are versioned in Git. Runtime database files, WAL files, and local backups are not committed.

A storage interface must isolate the control plane from SQLite-specific calls so a later PostgreSQL migration remains possible without changing contract schemas or watchdog behavior. PostgreSQL is not required for the initial three-lane Factory.

## 16. Contract serialization and validation

Human-authored contracts will use YAML.

Every contract type will have a versioned JSON Schema that defines required fields, allowed values, identifier formats, references, limits, and validation rules.

The Factory must process contracts in this order:

1. parse YAML using a safe loader with aliases and custom executable tags disabled or tightly bounded;
2. reject duplicate keys, unknown fields where the schema forbids them, malformed identifiers, unresolved references, and schema violations;
3. normalize approved defaults and scalar types;
4. convert the validated contract to canonical JSON;
5. compute and record a deterministic content hash from the canonical JSON;
6. provide only the validated canonical representation to the watchdog, runtime database, models, lanes, and tools.

Canonical JSON is the internal comparison, hashing, caching, signing, and runtime-transfer format. YAML formatting, comments, key order, and whitespace cannot change contract meaning or identity.

The original YAML remains the human-readable source file. Canonical JSON may be regenerated and must not become a competing editable source of truth.

Invalid or ambiguous YAML must fail closed before task creation, permission granting, lane assignment, or execution.

## 17. Immutable activation and automatic safe revisions

An activated contract version is immutable. The Factory must not edit an activated version in place.

A requested change must create a Change Contract that records:

- the contract and version being changed;
- the reason and source of the change;
- the exact proposed difference;
- affected requirements, tasks, paths, interfaces, tests, permissions, and components;
- whether the change is backward-compatible;
- required evidence and rollback behavior;
- whether a protected boundary is crossed.

The Watchdog may automatically validate and activate a new contract version when it can deterministically prove that the change is bounded, reversible, non-destructive, compatible with dependent components, inside approved authority, and supported by all required evidence.

Human approval is required only when the change deletes or replaces protected material, changes intended product behavior, crosses ownership or privacy boundaries, introduces an unresolved breaking interface change, alters architecture or security policy, expands authority, requires persistent host changes, sends private material to cloud services, merges to a protected branch, publishes, releases, spends money, or remains materially ambiguous.

Activation assigns the next runtime generation atomically after validation and any required approval. Ordinary parsing, cache rebuilding, restart, or re-ingestion must not increment generation.

The previous activated version, canonical hash, generation, approval record, evidence, and rollback reference remain available for audit and recovery.