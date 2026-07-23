# Factory

> **If you can dream it, we can build it.**

Factory is a standalone, local-first AI software-production system designed to build, repair, improve, test, document, package, and maintain complete runnable code-based projects.

## Status

**Product definition and high-level architecture recorded. Implementation has not started.**

The system is intentionally planned in locked sections before code is written. This prevents architecture drift, conflicting parallel edits, unverifiable completion claims, and uncontrolled autonomy.

## Core architecture

```text
Deterministic watchdog and state machine
├── Lane 1: Groq Worker + Reviewer
├── Lane 2: Cerebras Worker + Reviewer
└── Lane 3: NVIDIA Worker + Reviewer

Local supervision and fallback
├── qwen3:8b
└── qwen3:14b
```

Each lane receives a bounded task contract, isolated Git worktree and branch, disposable sandbox, deterministic tests, independent review, evidence gates, and recovery checkpoints.

Models perform work. The deterministic control plane owns permissions, task states, routing, evidence, rollback, integration, and completion.

## Documentation

Read the repository in this order:

1. [`PROJECT_DEFINITION.md`](PROJECT_DEFINITION.md) — governing purpose, boundaries, priorities, controls, and success criteria.
2. [`docs/00-DOCUMENTATION-INDEX.md`](docs/00-DOCUMENTATION-INDEX.md) — source hierarchy and repository map.
3. [`docs/01-APPROVED-DECISIONS.md`](docs/01-APPROVED-DECISIONS.md) — approved three-lane, watchdog, model, integration, and drift-recovery decisions.
4. [`docs/02-FACTORY-ARCHITECTURE.md`](docs/02-FACTORY-ARCHITECTURE.md) — high-level component boundaries and execution flow.
5. [`docs/03-MODEL-ROSTER.md`](docs/03-MODEL-ROSTER.md) — exact approved local and hosted models, roles, routing, and fallback rules.
6. [`docs/04-RECOVERY-POLICY.md`](docs/04-RECOVERY-POLICY.md) — safe checkpoints, rollback, restart, failure, and scope-drift behavior.
7. [`docs/05-BUILD-PLAN-MAP.md`](docs/05-BUILD-PLAN-MAP.md) — eight ordered planning and implementation sections.

## Approved build order

1. Requirements and contracts
2. Task queue and state machine
3. Deterministic watchdog
4. Model routing and quotas
5. Git/worktree and sandbox isolation
6. Three Worker–Reviewer lanes
7. Testing, evidence, integration, and recovery
8. Dashboard, packaging, and installation

## Non-negotiable operating rules

- Local operation remains available without cloud providers.
- Private project data cannot leave the local system without task-scoped permission.
- Internet access is disabled by default.
- No model can certify its own work.
- Existing tests cannot be silently weakened to obtain a pass.
- Parallel lanes cannot edit overlapping paths.
- Shared integration work is serialized.
- Scope drift triggers evidence preservation, rollback to the last verified safe point, contract correction, and restart.
- GLM-4.7 is not part of the approved model roster.
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

The next task is to finish the specification for **Section 1: Requirements and contracts** using the fewest necessary user decisions. No implementation should begin until that section is approved and recorded.