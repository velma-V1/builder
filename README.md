# Factory

> **If you can dream it, we can build it.**

Factory is a standalone, local-first AI software-production system designed to build, repair, improve, test, document, package, and maintain complete runnable code-based projects.

## Status

**Product definition, high-level architecture, and Section 1 design and implementation plan are recorded. Implementation has not started.**

The system is intentionally planned in locked sections before code is written. This prevents architecture drift, conflicting parallel edits, unverifiable completion claims, and uncontrolled autonomy.

## Primary operating experience

The **Builder Dashboard is the primary interface**. Normal development must occur inside the Builder without requiring VS Code, Codex, or another IDE.

The built-in workspace includes:

- a project-aware file explorer;
- a Monaco-based code editor;
- terminal and command views;
- diffs, tests, evidence, checkpoints, approvals, previews, and graphs;
- direct control of the local coding worker through the deterministic control plane.

An IDE adapter/plugin is included as a disabled-by-default extension point. VS Code may be connected later as an optional external tool, but Factory core must never depend on VS Code or any IDE.

## Core architecture

```text
Builder Dashboard — primary interface
├── Built-in file explorer
├── Built-in Monaco code editor
├── Terminal, preview, tests, evidence, graphs, and approvals
└── Disabled-by-default IDE adapter
        |
        v
Deterministic watchdog and state machine
├── Primary local coding worker: Aider + Ollama
├── Permanent local model runtime: Ollama
├── Local models: qwen3:8b and qwen3:14b
├── Optional hosted Worker–Reviewer lanes
└── Git/worktree, sandbox, verification, rollback, and integration controls
```

Aider is a bounded coding worker, not system authority. The deterministic control plane owns permissions, task states, routing, file boundaries, evidence, rollback, integration, and completion.

OpenHands is reserved as a possible future addition after v1 evaluation. Codex is not a required Factory dependency.

## Documentation

Read the repository in this order:

1. [`PROJECT_DEFINITION.md`](PROJECT_DEFINITION.md) — governing purpose, boundaries, priorities, controls, and success criteria.
2. [`docs/00-DOCUMENTATION-INDEX.md`](docs/00-DOCUMENTATION-INDEX.md) — source hierarchy and repository map.
3. [`docs/01-APPROVED-DECISIONS.md`](docs/01-APPROVED-DECISIONS.md) — approved architecture, permissions, storage, local toolchain, and interface decisions.
4. [`docs/02-FACTORY-ARCHITECTURE.md`](docs/02-FACTORY-ARCHITECTURE.md) — high-level component boundaries and execution flow.
5. [`docs/03-MODEL-ROSTER.md`](docs/03-MODEL-ROSTER.md) — approved local and hosted models, roles, routing, and fallback rules.
6. [`docs/04-RECOVERY-POLICY.md`](docs/04-RECOVERY-POLICY.md) — safe checkpoints, rollback, restart, failure, and scope-drift behavior.
7. [`docs/05-BUILD-PLAN-MAP.md`](docs/05-BUILD-PLAN-MAP.md) — eight ordered planning and implementation sections.
8. [`docs/06-BUILDER-INTERFACE-AND-LOCAL-TOOLCHAIN.md`](docs/06-BUILDER-INTERFACE-AND-LOCAL-TOOLCHAIN.md) — dashboard, Monaco, file explorer, Aider/Ollama, and optional IDE adapter rules.

## Approved build order

1. Requirements and contracts
2. Task queue and state machine, preceded by the minimum Builder workspace shell
3. Deterministic watchdog
4. Model and coding-tool routing and quotas
5. Git/worktree and sandbox isolation
6. Three Worker–Reviewer lanes
7. Testing, evidence, integration, and recovery
8. Complete dashboard, packaging, and installation

## Non-negotiable operating rules

- Ollama is the permanent local model runtime.
- Aider + Ollama is the primary local coding worker for v1.
- The Builder Dashboard is the normal development environment.
- Factory core cannot depend on Codex, VS Code, or another IDE.
- Private project data cannot leave the local system without task-scoped permission.
- Internet access is disabled by default.
- No model or coding worker can certify its own work.
- Existing tests cannot be silently weakened to obtain a pass.
- Parallel lanes cannot edit overlapping paths.
- Shared integration work is serialized.
- Scope drift triggers evidence preservation, rollback to the last verified safe point, contract correction, and restart.
- No unavailable model may be silently replaced.
- Merge, release, publishing, protected architecture changes, and protected security changes remain approval-gated.

## Initial operating target

- Windows 11 Home, including the current unactivated development environment
- WSL2 and Docker-compatible isolation
- Ryzen 7 7800X3D
- RTX 4070 Super with 12 GB VRAM
- 32 GB RAM
- Guided setup and one-installer final experience

## Next work

Implement Section 1 from the approved plan using the local-first development path. The minimum Builder workspace shell must be available before normal later-section development moves fully inside the Dashboard.