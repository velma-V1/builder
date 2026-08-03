# Phase 3B Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete Builder Phase 3B from the current tracked and untracked baseline through independently verified execution, explicit approval, safe promotion/rollback, lifecycle/API/UI integration, and evidence-backed documentation.

**Architecture:** Preserve the Orchestrator as the sole authoritative task-state writer. Keep worker output untrusted until a deterministic Verification Engine persists digest-checked evidence and an immutable promotion manifest; a separate Promotion Service then consumes an explicitly bound approval, revalidates the frozen manifest, serializes target updates, records promotion/rollback outcomes, and alone advances a task to `COMPLETE`.

**Tech Stack:** Python 3.12–3.14, SQLite, Starlette, pytest, mypy, Ruff, React 19, TypeScript, Vite/Vitest, XState, TanStack Query.

## Global Constraints

- Work only under `/home/xxthatguyxx/builder`; never access `/mnt/*`.
- Preserve LF endings and existing approved public interfaces and architecture.
- Do not connect real external services, alter global configuration, push, merge, rebase, rewrite history, deploy, promote protected branches, or release.
- Treat current tracked and untracked Phase 3B work as the intended baseline.
- Follow red-green-refactor for every behavioral change; do not weaken or broadly skip valid tests.
- Missing evidence or required verification fails closed; worker self-reports never certify output.
- Every milestone receives focused checks, relevant regressions, diff review, code review, and a coherent local commit only after verification.

---

### Task 1: Baseline repair

**Files:** `src/factory/verification/{models,store,engine}.py`, `src/factory/py.typed`, `pyproject.toml`, `tests/workers/support.py`, affected worker tests, `tests/worker_engine/test_agent_zero_process_client.py`, and focused regression tests.

**Interfaces:** Preserve existing evidence models and worker fixture behavior; add an explicit loopback capability marker/probe that skips only after socket creation is denied.

- [ ] Add failing regressions for slotted deterministic serialization, importable worker support, repository mypy invocation, Ruff findings, and loopback classification.
- [ ] Reproduce each failure and record its root cause.
- [ ] Implement the smallest schema-aware serialization, fixture relocation, typing marker/config correction, formatting repair, and capability classification.
- [ ] Run focused tests, full collection, Ruff format/lint, repository mypy, and `git diff --check`.
- [ ] Review and commit the internally consistent baseline repair.

### Task 2: Verification persistence

**Files:** `src/factory/verification/{__init__,errors,models,store}.py`, `tests/verification/test_{models,store}.py`.

**Interfaces:** Public read-only reader plus confined writer; canonical JSON schemas; digest verification on every read; deterministic duplicate-run and recovery semantics.

- [ ] Write failing round-trip, digest, tamper, append-only, duplicate, and restart/idempotency tests.
- [ ] Implement stable canonical persistence and fail-closed reads without weakening migration constraints.
- [ ] Run focused persistence tests, migration regressions, Ruff, and strict mypy.
- [ ] Review and commit verification persistence.

### Task 3: Independent Verification Engine

**Files:** split focused modules under `src/factory/verification/` as needed; `tests/verification/test_engine*.py` and fixtures.

**Interfaces:** `VerificationEngine.verify(task_id, run)` produces exact independently generated evidence and, only on success, an immutable manifest; all state changes use the Orchestrator writer.

- [ ] Write failing tests for direct-read-only, staged-write, sandboxed execution, scope/protected paths, artifact/digest integrity, syntax, typing, lint, focused/regression tests, explicit task acceptance, tampering, duplicates, interruption, and restart.
- [ ] Implement deterministic check planning and execution; missing required tools/tests/evidence fail closed and subprocesses remain bounded.
- [ ] Replace substring acceptance with structured task-specific criteria and recorded proof.
- [ ] Run focused, integration, failure-path, persistence, Ruff, and strict mypy checks.
- [ ] Review and commit the Verification Engine.

### Task 4: Promotion Service

**Files:** `src/factory/promotion/`, verification/approval/Git integration points, migration-compatible stores, and `tests/promotion/`.

**Interfaces:** Approval binding includes task, run, evidence digest, manifest digest, target, and revision; service implements approve/reject/promote/rollback/reconcile while Orchestrator remains authoritative.

- [ ] Write failing success, rejection, conflict, tamper, protected-target, rollback, interruption, restart, and concurrency tests.
- [ ] Implement immutable pre-promotion revalidation, target serialization, durable records, deterministic rollback, and fail-closed reconciliation.
- [ ] Prove only a successful promotion reaches `COMPLETE` and no approval is inferred.
- [ ] Run focused promotion, approval, Git, state-machine, failure-path, Ruff, and strict mypy checks.
- [ ] Review and commit the Promotion Service.

### Task 5: Lifecycle and API integration

**Files:** worker/orchestrator services and startup wiring, API models/routes/services, migrations only if an additive compatible change is required, and end-to-end/restart tests.

**Interfaces:** `intake -> claim -> execute -> verify -> await approval -> approve/reject -> promote/rollback -> durable final state` through real service boundaries.

- [ ] Write failing end-to-end, verification-failure, approval/rejection, interrupted verification/promotion, restart, and durable API-state tests.
- [ ] Wire worker success to independent verification and approval actions to the real Promotion Service.
- [ ] Add safe startup reconciliation without blind resume.
- [ ] Run backend integration, API, restart, full collection, Ruff, and strict mypy checks.
- [ ] Review and commit lifecycle/API integration.

### Task 6: Phase 3B UI

**Files:** UI API/query/types/components/pages/state/realtime modules and colocated tests.

**Interfaces:** Backend durable state remains authoritative; UI exposes evidence/manifest review, approve/reject, promotion/rollback state, and reconnect reconciliation only.

- [ ] Write failing unit/integration tests for display, bound actions, progress/failure evidence, and reconnect/restart reconciliation.
- [ ] Implement the minimal Phase 3B controls using existing React Query and realtime patterns.
- [ ] Run frontend typecheck, lint, Vitest, and production build.
- [ ] Review and commit the UI milestone.

### Task 7: Evidence, documentation, and final verification

**Files:** `README.md`, `docs/10-IMPLEMENTATION-ROADMAP.md`, `docs/planning/00-CONTINUATION-LEDGER.md`, Phase 3B handoff and verification matrices/reports.

**Interfaces:** Every reported result names the exact command and exact tested commit; statuses distinguish PASS, FAIL, SKIP, and ENVIRONMENT-BLOCKED.

- [ ] Run lockfile, full collection/suite, Ruff format/lint, repository mypy, every applicable repository verifier, and frontend install/typecheck/lint/test/build.
- [ ] Run environment-specific checks separately; record exact errors, missing capability, and required rerun environment for each block.
- [ ] Write the handoff, requirement-to-test matrix, failure-path matrix, verification report, roadmap, ledger, and README against the tested commit.
- [ ] Re-run documentation integrity and final verification after documentation changes.
- [ ] Obtain final whole-branch code review, resolve Critical/Important findings, and commit evidence/documentation.
