# Phase 3B Blocker Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clear all six Phase 3B merge blockers with fail-closed, regression-tested behavior.

**Architecture:** Add narrow security seams at existing boundaries: an isolated verification
runner, runtime session authentication, explicit launcher composition, last-moment path
revalidation, durable promotion intents, and verified process cleanup. Preserve existing lifecycle
and public model shapes except where authentication removes caller authority.

**Tech Stack:** Python 3.14, Starlette, SQLite, pytest, TypeScript/React, Git.

## Global Constraints

- Keep PR #18 draft and do not restart review before Linux and native Windows pass.
- Do not persist runtime credentials in source, browser storage, logs, or repository files.
- Use tests first and run only focused tests until all six fixes are complete.
- Make one implementation commit and one push after the complete Linux gate.

---

### Task 1: Isolated verification runner

**Files:** `src/factory/verification/engine.py`, new focused runner module if needed,
`tests/verification/test_engine_integration.py`, `tests/verification/test_engine_policy.py`.

**Interfaces:** Produce a typed command-runner protocol returning exit code/stdout/stderr; the
engine requires it for lint, typing, and tests and records a failed evidence item when unavailable.

- [ ] Add tests proving host `subprocess.run` is never used and missing isolation fails closed.
- [ ] Run those tests and observe the expected failure.
- [ ] Implement the runner boundary and route all worker-controlled commands through it.
- [ ] Run verification tests and confirm PASS.

### Task 2: Authenticated approval authority

**Files:** `src/factory/orchestrator_api/app.py`, `scripts/run_orchestrator.py`,
`ui/src/api/orchestrator.ts`, API and frontend tests.

**Interfaces:** `create_app` accepts a session authenticator; protected requests carry a runtime
credential; handlers derive operator identity from the authenticated principal.

- [ ] Add tests for missing/wrong credentials, ignored body identity, authenticated approve/reject,
  and memory-only frontend injection.
- [ ] Run them and observe failure.
- [ ] Implement constant-time server authentication and runtime in-memory UI injection.
- [ ] Run focused backend/frontend tests and confirm PASS.

### Task 3: Complete quick-start composition

**Files:** `scripts/start_all.py`, `scripts/run_orchestrator.py`, launcher tests.

**Interfaces:** launcher passes runtime DB, security DB, audit DB, session credential, and worker
configuration; orchestrator constructs verifier and worker lifecycle and reconciles before health.

- [ ] Add a behavioral launcher test that executes captured service argv/composition.
- [ ] Run it and observe failure.
- [ ] Implement the smallest complete composition using existing services.
- [ ] Run launcher and lifecycle tests and confirm PASS.

### Task 4: Pre-write path revalidation

**Files:** `src/factory/worker_engine/builder_worker_transport.py`, transport security tests.

**Interfaces:** reuse the original `PathAuthority` and authorization result with
`revalidate_before_use` immediately before filesystem mutation.

- [ ] Add a TOCTOU test swapping an authorized directory during the model call.
- [ ] Run it and observe the escaped write.
- [ ] Revalidate and fail before `mkdir`/`write_text`.
- [ ] Run transport tests and confirm PASS.

### Task 5: Interrupted-promotion rollback

**Files:** promotion models/store/service and migration only if the existing record cannot retain
the intent; promotion restart tests.

**Interfaces:** persist original target and checkpoint before ref movement; reconciliation calls
`restore_ref(repo, target, original, checkpoint)` and records rollback outcome before `FAILED`.

- [ ] Add crash-after-ref-advance restart tests for rollback success, rollback failure, and replay.
- [ ] Run them and observe failure.
- [ ] Implement durable intent and deterministic reconciliation.
- [ ] Run promotion tests and confirm PASS.

### Task 6: Bounded verified Windows cleanup

**Files:** `scripts/start_all.py`, `tests/scripts/test_start_all.py`.

**Interfaces:** cleanup uses fixed timeouts and raises `StartupFailure` on timeout, nonzero taskkill,
or a still-live process.

- [ ] Add Windows-mode tests for timeout, nonzero exit, still-live process, and successful cleanup.
- [ ] Run them and observe failure.
- [ ] Implement bounded taskkill and termination verification.
- [ ] Run launcher tests and confirm PASS.

### Task 7: Final verification and publication

- [ ] Run all six focused suites together.
- [ ] Run the complete Linux gate exactly once.
- [ ] Inspect the complete diff and commit all coherent changes once.
- [ ] Push the existing Phase 3B branch once and confirm PR #18 remains draft.
- [ ] Run focused launcher and junction tests on native Windows at the exact pushed SHA.
- [ ] Restart merge review only if both Linux and Windows gates pass.
