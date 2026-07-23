# Local Section 1 Execution

**Status:** Approved local-first implementation handoff  
**Target branch:** `agent/section-1-local-implementation`

## Governing files

Read and follow these files in order:

1. `PROJECT_DEFINITION.md`
2. `docs/01-APPROVED-DECISIONS.md`
3. `docs/01A-LOCAL-BUILDER-STACK-DECISION.md`
4. `docs/01B-SELF-HOSTING-TRANSITION-DECISION.md`
5. `docs/specifications/2026-07-23-section-1-requirements-contracts-design.md`
6. `docs/superpowers/plans/2026-07-23-section-1-requirements-contracts.md`
7. `docs/06-BUILDER-INTERFACE-AND-LOCAL-TOOLCHAIN.md`

## Required execution stack

- Permanent local runtime: Ollama
- Primary local coding worker: Aider connected to Ollama
- Local models: approved Qwen models from `docs/03-MODEL-ROSTER.md`
- Required repository isolation: task branch/worktree and approved sandbox
- Required verification: deterministic tests and retained evidence

Codex, VS Code, OpenHands, hosted providers, and any other IDE are not required.

## Bootstrap exception

The Builder Dashboard does not exist yet. Section 1 and the minimum Builder workspace shell may therefore be bootstrapped through a controlled local terminal workflow.

This is temporary. After each internal capability passes its acceptance tests, that workflow must move into the Builder:

1. file explorer + Monaco + safe file service → browsing and editing move inside;
2. controlled terminal + test runner + evidence capture → commands and tests move inside;
3. Ollama + Aider bridge → AI coding and repair move inside;
4. Git + worktree + checkpoint + review + rollback controls → repository management moves inside;
5. full integration and recovery verification → Factory continues building and maintaining itself through the Builder.

The bootstrap exception does not permit unrestricted host access or bypass any contract, path, deletion, checkpoint, test, review, or merge rule.

## Execution rules

1. Work only on `agent/section-1-local-implementation` or task-specific branches/worktrees created from it.
2. Execute the five tasks in the approved implementation plan in order.
3. Use test-driven development for each task.
4. Give each task exact owned and forbidden paths.
5. Use Aider with an approved Ollama model for implementation.
6. Use a fresh review context after each task; reviewer conclusions cannot replace deterministic tests.
7. Fix all Critical or Important findings before advancing.
8. Record commands, changed files, tests, results, checkpoints, concerns, and rollback references.
9. Continue automatically through safe fixes and retries.
10. Stop only for a genuine blocker or protected human decision.
11. Do not merge into `main` without explicit user approval.
12. Do not keep an external development workflow as the normal path after its verified Builder replacement is available.

## Required task gates

- [ ] Task 1 — Common envelope and seven JSON Schemas
- [ ] Task 2 — Safe YAML ingestion and canonicalization
- [ ] Task 3 — Semantic, reference, path, ownership, and impact validation
- [ ] Task 4 — Change policy, SQLite activation, rollback, and immutable cache
- [ ] Task 5 — Full verification package and Section 2 handoff
- [ ] Independent review after every task
- [ ] Complete Windows 11 Home-compatible test suite
- [ ] Final whole-branch review
- [ ] Exact completion evidence

## Completion rule

Section 1 is complete only when every acceptance criterion in the approved specification and implementation plan has deterministic evidence. Aider, Qwen, or a reviewer cannot declare completion independently.