# Factory

> **If you can dream it, we can build it.**

Factory is a standalone, local-first AI software-production system designed to build, repair, improve, test, document, package, and maintain complete runnable code-based projects.

## Status

**Phase 3B worker verification, explicit approval, promotion/rollback, lifecycle/API integration,
and required dashboard controls are implemented on the Phase 3B branch. The implementation suite
passes, and the three legacy section/roadmap blockers are cleared. The repository release gate
remains `INCOMPLETE` only for the Windows junction rerun and the network/cache-dependent Section 1
bootstrap check. No merge, deployment, or protected-ref promotion occurred.**

Continue to the next phase:

- [`docs/verification/section-2-evidence-report.md`](docs/verification/section-2-evidence-report.md) — Section 2 verification report: PROM-PH2 exit gate results, 93 tests (100% pass), regression prevention gates, and migration integrity.
- [`docs/verification/section-2-test-summary.md`](docs/verification/section-2-test-summary.md) — detailed test execution summary, code coverage analysis, and quality metrics.
- [`HANDOFF-PH2.md`](HANDOFF-PH2.md) — the PH-2 handoff record; what was done, binding decisions, schema-freeze.
- [`docs/01R-PLANNING-RESOLUTIONS-AND-AMENDMENTS.md`](docs/01R-PLANNING-RESOLUTIONS-AND-AMENDMENTS.md) — the resolutions and decisions in force for remaining phases.
- [`docs/10-IMPLEMENTATION-ROADMAP.md`](docs/10-IMPLEMENTATION-ROADMAP.md) — the nine-phase build order, gates, and critical path. **Roadmap PH-3 next: Watchdog, Permissions, Approval, Audit & Tools** (unbuilt).
- [`docs/WORKER-EXECUTION-SUBSTRATE-CLASSIFICATION.md`](docs/WORKER-EXECUTION-SUBSTRATE-CLASSIFICATION.md) — the Worker Execution Substrate (prebuilt PH-4/PH-5 execution infra on `claude/ph3-worker-engine`); **not roadmap PH-3**.

The system is intentionally planned in locked sections before code is written. This prevents architecture drift, conflicting parallel edits, unverifiable completion claims, and uncontrolled autonomy.

## Quick start (Phase 3B — local verification and operator-controlled promotion)

The launcher retains Phase 3A intake. With migrated security and audit databases configured, the
orchestrator additionally exposes Phase 3B evidence/manifest review, explicit bound approval,
approve/reject, and promotion status. Agent Zero and real external services remain disabled unless
separately configured; approval is never inferred.

**From Linux/WSL2 directly:**

```bash
cd /home/xxthatguyxx/builder
uv run python scripts/start_all.py
```

This checks required dependencies (repository path, Python/`uv`, Node/`npm`, free ports),
separately detects Docker/Ollama and reports their status (informational only — Phase 3A
doesn't require either), runs database setup, starts the read-only API, the orchestrator API,
and the Vite dashboard, waits for all three to report healthy, then opens the dashboard in your
browser. Ctrl-C stops all three cleanly, including any child processes they spawned.

**From Windows, via desktop shortcut:**

1. Once, in PowerShell: `powershell -ExecutionPolicy Bypass -File scripts\windows\install-shortcut.ps1`
   (creates a `Builder` shortcut on your Desktop). Remove it later with
   `uninstall-shortcut.ps1` in the same folder.
2. Double-click **Builder** on the Desktop. It resolves the configured WSL distribution
   (`scripts/windows/Builder.ps1`), then hands off to the same `scripts/start_all.py` inside
   WSL2. A missing WSL install, missing distribution, missing repository path, or missing
   Python/Node produces a specific, readable error instead of a silent failure.

## Primary operating experience

The **Builder Dashboard is the primary interface**. Normal development must occur inside the Builder without requiring VS Code, Codex, or another IDE.

The built-in workspace includes:

- a project-aware file explorer;
- a Monaco-based code editor;
- terminal and command views;
- diffs, tests, evidence, checkpoints, approvals, previews, and graphs;
- direct control of the local coding worker through the deterministic control plane.

An IDE adapter/plugin is included as a disabled-by-default extension point. VS Code may be connected later as an optional external tool, but Factory core must never depend on VS Code or any IDE.

Development begins through a controlled local bootstrap only until the matching Builder capabilities are verified. File editing, commands, testing, AI coding, Git, review, evidence, and recovery then move into Factory capability-by-capability. The verified end state is self-hosted local development through the Builder.

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
2. [`docs/00-DOCUMENTATION-INDEX.md`](docs/00-DOCUMENTATION-INDEX.md) — the complete, authoritative source hierarchy (26 levels, including the `01C`–`01Q` architecture supplements and `docs/01R`) and repository map.
3. [`docs/01-APPROVED-DECISIONS.md`](docs/01-APPROVED-DECISIONS.md) — approved architecture, permissions, storage, local toolchain, and interface decisions.
4. [`docs/01R-PLANNING-RESOLUTIONS-AND-AMENDMENTS.md`](docs/01R-PLANNING-RESOLUTIONS-AND-AMENDMENTS.md) — approved resolutions (R1–R5) and decisions (autonomy, deletion, Windows-native isolation) that amend the items below; read this before relying on any clause it supersedes.
5. [`docs/01A-LOCAL-BUILDER-STACK-DECISION.md`](docs/01A-LOCAL-BUILDER-STACK-DECISION.md) — Ollama, Aider, Dashboard, Monaco, file explorer, IDE independence, and OpenHands deferral.
6. [`docs/01B-SELF-HOSTING-TRANSITION-DECISION.md`](docs/01B-SELF-HOSTING-TRANSITION-DECISION.md) — staged migration from bootstrap tools into the local Builder.
7. [`docs/02-FACTORY-ARCHITECTURE.md`](docs/02-FACTORY-ARCHITECTURE.md) — high-level component boundaries and execution flow.
8. [`docs/03-MODEL-ROSTER.md`](docs/03-MODEL-ROSTER.md) — approved local and hosted models, roles, routing, and fallback rules.
9. [`docs/04-RECOVERY-POLICY.md`](docs/04-RECOVERY-POLICY.md) — safe checkpoints, rollback, restart, failure, and scope-drift behavior.
10. [`docs/05-BUILD-PLAN-MAP.md`](docs/05-BUILD-PLAN-MAP.md) — ordered build sections and self-hosting transition gates.
11. [`docs/06-BUILDER-INTERFACE-AND-LOCAL-TOOLCHAIN.md`](docs/06-BUILDER-INTERFACE-AND-LOCAL-TOOLCHAIN.md) — dashboard, Monaco, file explorer, Aider/Ollama, and optional IDE adapter rules.

The full pre-implementation planning system — master roadmap, glossary, contract/schema registries, dependency and workstream maps, verification matrix, risk register, test strategy, release-line plans, reusable templates, the component map, and the nine phase plans — lives under `docs/10-IMPLEMENTATION-ROADMAP.md`, `docs/11-CONTROLLED-GLOSSARY-AND-CROSSWALKS.md`, `docs/planning/`, `docs/release/`, `docs/templates/`, `docs/specifications/components/`, and `docs/plans/`.

## Approved build order

1. Requirements and contracts
2. Task queue and state machine, preceded by the minimum Builder workspace shell
3. Deterministic watchdog
4. Model and coding-tool routing and quotas
5. Git/worktree and sandbox isolation
6. Three parallel major-stage workstreams (Worker–Reviewer lanes are an optional secondary pattern; see `docs/01R` R2)
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

Section 1 (Requirements & Contracts) is implemented and verified — see [`docs/verification/section-1-requirements-contracts.md`](docs/verification/section-1-requirements-contracts.md). Per `HANDOFF-PH1.md` and `docs/10-IMPLEMENTATION-ROADMAP.md §15`, this is the PH-1 exit gate: do not begin PH-2 (the minimum Builder shell, task queue/state machine, and deterministic watchdog) without explicit schema-freeze / phase-exit approval.
