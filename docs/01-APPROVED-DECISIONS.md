# Approved Factory Decisions

**Status:** Approved supplement to `PROJECT_DEFINITION.md`  
**Recorded:** July 22, 2026

This file records decisions made after the original project definition. It supersedes only the specific previously open items named here. All other governing requirements remain unchanged.

## 1. Project boundary

The Factory is a standalone system. It is not Rabbit Hole, VELMA, or any other product it may later build. Project-specific requirements do not enter Factory architecture unless explicitly approved.

## 2. Permanent three-lane structure

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

Section 1 will use small linked contracts rather than one oversized contract or a database-first design.

The contract family will separate:

- project intake and project identity;
- requirements and traceability;
- bounded task execution;
- path ownership and file boundaries;
- permissions and approvals;
- required evidence and completion;
- approved changes and scope revisions.

All contracts will share stable identifiers, version fields, provenance, status, and references to related contracts. Each contract will have one clear responsibility and will be independently schema-validated.