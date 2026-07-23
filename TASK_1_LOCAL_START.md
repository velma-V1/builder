# Section 1 Task 1 — Local Start Packet

**Branch:** `agent/section-1-local-implementation`  
**Task:** Package foundation, common envelope, and seven JSON Schemas

## Authority

Follow the complete Task 1 instructions in:

`docs/superpowers/plans/2026-07-23-section-1-requirements-contracts.md`

Also obey:

- `docs/01A-LOCAL-BUILDER-STACK-DECISION.md`
- `docs/01B-SELF-HOSTING-TRANSITION-DECISION.md`
- `LOCAL_SECTION_1_EXECUTION.md`

## Required worker path

- Coding worker: Aider
- Model runtime: Ollama
- Preferred difficult-task local model: approved `qwen3:14b`
- Fresh review context after implementation
- No Codex, VS Code, OpenHands, or hosted provider required

## Start gate

1. Create an isolated Task 1 branch/worktree from `agent/section-1-local-implementation`.
2. Confirm the workspace is clean.
3. Execute Task 1 test-first, exactly in the approved plan.
4. Do not advance to Task 2 until Task 1 tests, Ruff, strict mypy, changed-path checks, and independent review pass.
5. Record commands, changed files, results, checkpoint commit, concerns, and rollback reference.

## Stop conditions

Stop only for a verified blocker, missing protected permission, conflicting approved requirements, or a proposed architecture/security change. Routine implementation choices and safe test repairs proceed automatically.