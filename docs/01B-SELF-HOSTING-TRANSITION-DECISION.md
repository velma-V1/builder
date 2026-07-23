# Approved Self-Hosting Transition Decision

**Status:** Approved architecture supplement  
**Recorded:** July 23, 2026

## 1. Goal

Factory development begins with a controlled local bootstrap workflow only because the Builder Dashboard and its internal tools do not yet exist.

As soon as Factory can safely and reliably perform a workflow itself, that workflow must move into Factory. External development tools then become optional emergency or diagnostic fallbacks rather than the normal operating path.

## 2. Transition principle

Migration is capability-by-capability, not an unsafe all-at-once switch.

A capability moves into Factory only after deterministic evidence proves that the local replacement:

- performs the required workflow;
- respects contracts, ownership, permissions, deletion rules, and protected boundaries;
- records commands, changes, tests, evidence, checkpoints, and rollback information;
- survives restart and recovery where applicable;
- does not require Codex, VS Code, OpenHands, hosted models, or another IDE;
- has a tested fallback or recovery path.

Once those conditions pass, the external workflow is removed from the normal required process.

## 3. Required migration stages

### Stage 0 — Controlled local bootstrap

Use local terminal, Git, Ollama, and Aider only as needed to build Section 1 and the minimum Builder workspace shell.

### Stage 1 — Files and editing move inside

After the safe file-operation service, built-in file explorer, and Monaco editor pass their tests:

- normal file browsing moves into the Builder;
- normal manual code editing moves into Monaco;
- external editors become optional fallback tools.

### Stage 2 — Commands and tests move inside

After the controlled terminal, command runner, test runner, and evidence capture pass:

- normal commands, builds, tests, and logs run through the Builder;
- direct terminal use becomes an exceptional diagnostic path.

### Stage 3 — AI coding moves inside

After the Ollama runtime adapter and bounded Aider worker bridge pass:

- normal AI implementation and repair work launches from the Builder;
- task contracts, owned paths, model routes, limits, diffs, and results are controlled and displayed inside the Builder.

### Stage 4 — Git, review, and recovery move inside

After branch, worktree, checkpoint, diff, review, evidence, rollback, and recovery controls pass:

- normal Git and task-review workflows move into the Builder;
- external Git clients and repository interfaces become optional;
- protected remote push, merge, publish, and release remain approval-gated.

### Stage 5 — Factory becomes self-hosting

After the complete local workflow passes integration, failure-path, restart, security, and regression testing:

- Factory performs its own normal planning, coding, testing, review, documentation, recovery, and maintenance inside the Builder;
- the Builder becomes the primary environment used to continue building Factory itself;
- external AI builders, IDEs, and hosted services are not required.

## 4. Local-first end state

The normal self-hosted Factory workflow must operate locally with:

- Builder Dashboard;
- built-in file explorer;
- Monaco editor;
- deterministic control plane and watchdog;
- local Git repositories and worktrees;
- approved local sandboxes;
- SQLite runtime state;
- Ollama;
- Aider connected to Ollama;
- local tests, evidence, audit, checkpoints, and rollback.

Hosted models may remain optional task-scoped acceleration or specialist capacity only. Their absence cannot disable normal Factory operation.

Remote Git hosting may remain optional for backup, collaboration, or publishing, but local Git is the operational source required for normal work.

## 5. No premature cutover

Factory must not move a workflow inside merely because a user interface exists. The replacement must pass the applicable deterministic acceptance tests first.

If the internal replacement fails after cutover, Factory must preserve evidence, return to the last verified safe checkpoint, and use the approved temporary fallback until the local capability is repaired and reverified.

## 6. Completion evidence

The self-hosting transition is complete only when Factory can develop and maintain itself through the Builder with external IDEs, Codex, OpenHands, hosted models, and remote Git hosting unavailable, except for actions explicitly requiring an external destination such as publishing.