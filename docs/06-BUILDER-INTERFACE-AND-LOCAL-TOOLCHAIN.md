# Builder Interface and Local Toolchain

**Status:** Approved high-level component boundary  
**Recorded:** July 23, 2026

## 1. Operating rule

The Builder Dashboard is the primary user workspace. Normal development must be possible without opening VS Code, Codex, OpenHands, or another external development application.

## 2. Local stack

```text
Builder Dashboard
├── Project file explorer
├── Monaco code editor
├── Controlled terminal
├── Diff, test, evidence, approval, and checkpoint panels
├── Preview and graph panels
└── Optional IDE-adapter settings — disabled by default
        |
        v
Deterministic Control Plane
├── Contract and ownership enforcement
├── Safe file-operation service
├── Command and sandbox service
├── Evidence and checkpoint service
├── Coding-worker interface
└── Model-routing interface
        |
        +── Aider coding worker
        |       └── Ollama model runtime
        |
        +── Local Qwen dispatcher and supervisor through Ollama
        |
        └── Optional hosted lanes when explicitly allowed
```

## 3. Dashboard boundary

The Dashboard may request operations but cannot directly perform authoritative writes. File edits, commands, task changes, approvals, model calls, checkpoints, rollbacks, and completion transitions pass through deterministic control-plane interfaces.

A broken or compromised panel must not gain authority by being part of the primary interface.

## 4. File explorer

The file explorer presents the project as a controlled workspace rather than raw unrestricted host storage.

Required information includes:

- file and directory names;
- Git state;
- current task ownership;
- protected, forbidden, read-only, generated, and disposable status;
- change and dependency indicators;
- related tests and evidence when available;
- pending approval or conflict status.

Create, rename, move, and delete requests must use the safe file-operation service. Deletion remains governed by the approved deletion policy.

## 5. Monaco editor

Monaco is the built-in normal code editor.

Required v1 capabilities:

- open and edit files selected from the built-in explorer;
- multiple open files or tabs;
- syntax highlighting and basic language services;
- diagnostics display;
- project search and replace;
- unsaved-change protection;
- side-by-side or unified diff display;
- read-only and protected-file enforcement;
- task ownership and approval indicators;
- links to tests, evidence, checkpoints, and rollback;
- controlled handoff of selected context to the Aider worker.

Saving a file submits a controlled write request. Monaco never writes directly around the watchdog.

## 6. Aider worker adapter

Aider + Ollama is the primary local coding worker.

The adapter must provide a bounded interface similar to:

```text
submit_task(task_contract, canonical_context, permitted_paths, model_route, limits)
stream_worker_events(task_id)
request_revision(task_id, findings)
cancel_task(task_id)
collect_worker_package(task_id)
```

The exact implementation signature is defined later. The architectural rule is that Aider receives only the authority and context required by the active task and returns changes and evidence for deterministic inspection.

Aider does not own the repository, task state, model registry, approval state, or completion decision.

## 7. Ollama runtime adapter

Ollama is the permanent local runtime. The runtime adapter must support:

- health and version checks;
- model discovery and exact-ID verification;
- model start, call, cancellation, and failure reporting;
- local context and resource limits;
- request and token accounting when available;
- privacy-preserving local operation;
- deterministic route failure and fallback reporting.

Factory core depends on the Ollama adapter contract, not ad hoc shell commands scattered through the system.

## 8. Optional IDE adapter

The IDE adapter is an outbound integration boundary, disabled by default.

It may later expose approved operations such as:

- open a project or file in VS Code;
- navigate to a line or diagnostic;
- receive a user-authored edit notification;
- request a controlled refresh or diff;
- provide a narrow task/status view.

It must not grant the IDE direct access to authoritative runtime state or permission bypasses. Factory remains fully usable when the adapter is absent or disabled.

## 9. Deferred OpenHands adapter

OpenHands is excluded from v1. Any future integration must use the same bounded coding-worker interface rather than becoming a second control plane.

## 10. Dependency rule

Required v1 dependencies may include Ollama, Aider, the Dashboard runtime, Monaco, Git, Python, WSL2, and Docker-compatible isolation as approved by later section plans.

Required dependencies must not include:

- Codex;
- VS Code;
- another IDE;
- OpenHands;
- a hosted model provider.

## 11. Early workspace milestone

Before later sections rely on the Builder as the normal development environment, a minimum workspace shell must prove:

- Dashboard launch;
- project selection;
- safe file-tree loading;
- Monaco file open, edit, diff, and save through the control boundary;
- controlled terminal output;
- Ollama health and model status;
- one bounded Aider + Ollama coding task;
- task, test, approval, checkpoint, and rollback visibility;
- IDE adapter disabled by default.

This milestone does not require the final visual polish, complete graph system, installer, or every monitoring panel.