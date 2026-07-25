# HANDOFF — Worker Execution Substrate (Prebuilt PH-4/PH-5 Execution Seam)

> **CLASSIFICATION (2026-07-25):** This describes the **Worker Execution Substrate**, reclassified
> as **prebuilt PH-4/PH-5 execution infrastructure**. It is **NOT** roadmap PH-3. Roadmap **PH-3
> (Watchdog, Permissions, Approval, Audit & Tools) remains UNBUILT**. The real `ProcessSpawner` and
> sandbox isolation remain **PH-5** responsibilities. **PH-4 may consume this seam only after the
> true PH-3 security interfaces are frozen.** No roadmap dependency is bypassed. The "PH-3"/`T3.x`/
> `SEC-PH3-xx`/`PROM-PH3` labels below denote this substrate's development track only — see
> `docs/WORKER-EXECUTION-SUBSTRATE-CLASSIFICATION.md`.

**Date**: 2026-07-25
**Component**: Worker Execution Substrate (`CMP-WORKER`) — prebuilt PH-4/PH-5 seam, **not roadmap PH-3**
**Status**: ✓ Substrate COMPLETE — substrate promotion gate passed (this is NOT a roadmap PH-3 exit gate)
**Base**: PH-2 Orchestrator (`claude/ph2-orchestrator-implementation` @ 7e023a2)
**Branch**: `claude/ph3-worker-engine`
**Test Results**: 85 substrate + 93 PH-2 = 178 passing (100%)
**Code Quality**: ruff ✓, mypy --strict ✓ (13 source files)

---

## Executive Summary

The Worker Engine spawns and supervises worker processes, dispatches ready tasks under
fenced leases, executes them with bounded untrusted-output capture, routes every
authoritative state change through the PH-2 single writer (R1), and recovers from crashes
without blind resume (R3). It builds strictly on the frozen PH-2 interfaces and adds no new
migrations (schema freeze respected).

---

## What Was Built (commits)

| Task | Commit | Deliverable |
|------|--------|-------------|
| Planning cycle | `6d5ae2d` | 6 planning docs (spec, plan, failure, security, verification, certificate) |
| T3.1 | `270300f` | WorkerPool + process lifecycle (spawner protocols, reclaim, crash detection, shutdown) |
| T3.5 | `9dd4ac6` | LeaseCoordinator over PH-2 fenced leases |
| T3.2 | `db1da21` | Dispatcher + bounded streaming + TaskExecutor |
| T3.3 | `be048e1` | StateIntegration (single-writer routing) |
| T3.4 | `aaba6fe` | Recovery + retry + quarantine + startup reconciliation |
| Integration | `9814401` | E2E suite + verify_worker_substrate.py (18 checks) |

---

## Module Map (`src/factory/workers/`)

| Module | Responsibility |
|--------|----------------|
| `models.py` | WorkerState, WorkerStatus, ExecutionEvent/Result, event-type enum |
| `errors.py` | `WorkerEngineError(code, message)` |
| `process.py` | `ProcessSpawner`/`ProcessHandle` protocols; `SubprocessSpawner`; `WorkerProcess` slot |
| `lifecycle.py` | pure worker-slot transition policy |
| `pool.py` | `WorkerPool` — spawn/allocate/transition/reclaim/poll_health/shutdown |
| `lease_coordinator.py` | `LeaseCoordinator` — acquire/renew/validate/release under pool epoch |
| `dispatcher.py` | `Dispatcher` — ready→lease→assign |
| `streaming.py` | `OutputAccumulator`, `ExecutionStream` — bounded, append-only |
| `execution.py` | `TaskExecutor`, `RawWorkerEvent`, `CancelToken` |
| `state_integration.py` | `StateIntegration` — **sole holder of `_OrchestratorStateWriter`** |
| `recovery.py` | `RetryPolicy`, `WorkerRecovery`, `StartupRecovery` |
| `quarantine.py` | append-only `QuarantineRegistry` |

---

## Critical Design Decisions (Binding for PH-4+)

### 1. Worker Success → VERIFYING (NOT COMPLETE)
Per the authoritative 01L §3.1 table, `RUNNING → COMPLETE` is **not legal**; COMPLETE is
reachable only from VERIFYING. A worker therefore cannot certify its own task complete —
`StateIntegration.finalize` on success transitions RUNNING → VERIFYING and hands off to a
verification phase (PH-7). **PH-7 owns VERIFYING → COMPLETE.**

### 2. Single-Writer Confinement (R1)
`StateIntegration` is the only Worker-Engine type that holds `_OrchestratorStateWriter`. The
writer is **not** exported from `factory.workers` and no worker process receives a DB handle.
All recovery transitions (fail_crashed / block_for_review / quarantine) are methods on
StateIntegration so the writer never escapes. **PH-4/PH-5 must route state mutations the same way.**

### 3. No Blind Resume (R3)
On restart, `StartupRecovery.recover` applies PH-2 `reconcile_startup` outcomes: in-flight
tasks (PLANNING/RUNNING/VERIFYING/…) → BLOCKED, never silently back to RUNNING. Resuming a
BLOCKED task is an explicit operator/approval action (PH-4). STOPPING → CANCELLED is the one
safe auto-completion (an interrupted cancel).

### 4. Process-Epoch Fencing (R4)
Each `WorkerPool` generates one immutable `ProcessEpoch`. `LeaseCoordinator` is bound to it;
a lease minted under a prior epoch is rejected by a later pool regardless of wall-clock TTL.
Fencing is primary, expiry secondary.

### 5. Bounded Untrusted Output
Worker output is Zone-3 untrusted: 64 KiB/chunk + 512 MiB/task caps, sticky truncation,
SHA-256 hashed, never executed. Overflow → `output_overflow` failure. Prevents OOM (threat T-03).

---

## Interfaces for PH-4 / PH-5

### Dispatch a ready task
```python
from factory.workers import WorkerPool, LeaseCoordinator, Dispatcher
from factory.orchestrator.models import ProcessEpoch

epoch = ProcessEpoch.generate()
pool = WorkerPool(spawner=my_spawner, size=4, process_epoch=epoch)
coord = LeaseCoordinator.for_pool(runtime_db_path, epoch)
dispatcher = Dispatcher(pool=pool, coordinator=coord)

records = dispatcher.dispatch_ready(dependency_graph, states)  # tuple[DispatchRecord, ...]
# each record: .task_id, .worker_id, .lease
```

### Execute + integrate state
```python
from factory.workers import TaskExecutor, StateIntegration

integration = StateIntegration(writer=writer, reader=reader)  # only place the writer lives
integration.start_execution(rec.task_id, actor=rec.worker_id)      # → RUNNING
pool.mark_running(rec.worker_id)

result = TaskExecutor().execute(rec.task_id, output_source)         # bounded ExecutionResult
integration.finalize(rec.task_id, result, actor=rec.worker_id)     # → VERIFYING / FAILED / CANCELLED
pool.mark_done(rec.worker_id)
coord.release_task_lease(rec.lease)
```

### Recover after crash / restart
```python
from factory.workers import WorkerRecovery, StartupRecovery, QuarantineRegistry

# crash mid-run:
WorkerRecovery(pool=pool, integration=integration).recover_crashed()   # fail + reclaim

# process restart:
StartupRecovery(integration=integration, quarantine=QuarantineRegistry()).recover(task_ids)
```

### Provide a real worker (PH-5 sandbox seam)
Implement `ProcessSpawner.spawn(worker_id) -> ProcessHandle` and feed the process's
stdout/stderr into an iterable of `RawWorkerEvent` for `TaskExecutor.execute`. PH-5 substitutes
a sandbox-backed spawner without touching pool/dispatch logic.

---

## Known Limitations (for PH-4+ Consideration)

1. **Real process I/O is a seam, not wired.** `TaskExecutor` consumes an injected
   `RawOutputSource`; binding it to actual subprocess pipes / a PH-5 sandbox is deferred.
2. **VERIFYING → COMPLETE is not implemented** (PH-7 verification owns it).
3. **Approval-gated resume of BLOCKED tasks** needs the PH-4 approval engine.
4. **No sandbox isolation** — workers assume a valid sandbox (PH-5, Dec C).
5. **No output redaction** — raw logs stored; credential redaction is PH-7 staging.
6. **Resource quotas** (VRAM/RAM/timeouts) are PH-4; PH-3 respects submitted deadlines only.
7. **Heartbeat polling cadence** is caller-driven (`pool.poll_health()`); a supervising
   loop/thread is a PH-4 Watchdog concern.

---

## Schema

**No new migrations.** PH-3 uses the frozen PH-2 tables (0001–0003) unchanged. The schema
freeze holds: future structural needs require a new `0004_*.sql` with SHA pinning.

---

## Verification

```bash
uv run python3.12 scripts/verify_worker_substrate.py  # 18/18 PASS (substrate gate, not roadmap PH-3)
uv run python3.12 -m pytest tests/workers/ -q         # 85 passed
uv run python3.12 -m pytest tests/orchestrator/ -q    # 93 passed (regression)
uv run ruff check src/factory/workers/ tests/workers/
uv run mypy src/factory/workers/ --strict
```

Evidence: `docs/verification/worker-execution-substrate-evidence-report.md`,
`docs/verification/worker-execution-substrate-test-summary.md`.

---

## Roadmap position (corrected)

This substrate is **NOT** roadmap PH-3. Roadmap **PH-3 = Watchdog, Permissions, Approval, Audit &
Tools** (`docs/plans/section-3-orchestrator-watchdog-and-permissions.md`) and **remains UNBUILT**;
that plan is unchanged and still governs. This substrate is **prebuilt PH-4/PH-5 execution
infrastructure**: it exposes a `ProcessSpawner`/`ProcessHandle` seam whose real implementation is a
**PH-5** responsibility (sandbox/process isolation), and it will be consumed by PH-4/PH-5.

**Ordering constraint:** PH-4 (Model & Worker Routing) depends on the true PH-3 security
interfaces — permission enforcement + tool gateway (dependency map §6, roadmap §11). **PH-4 may
consume this seam only after those PH-3 interfaces are frozen.** No roadmap dependency is bypassed.

**Next real phase:** build roadmap **PH-3 Watchdog/Permissions** per its existing plan.

---

**Substrate promotion gate: PASS. This is NOT a roadmap PH-3 exit gate; roadmap PH-3 remains unbuilt.**

---

## Transfer to New Session (2026-07-25)

This section provides everything a new Claude Code session needs to resume work on this
repository without relying on prior chat history.

### Repository State Snapshot

| Field | Value |
|---|---|
| Active branch | `claude/ph3-worker-engine` |
| HEAD | `699279c` |
| Remote | synced (`origin/claude/ph3-worker-engine` == local HEAD) |
| `main` | `9bce1ca` — **untouched throughout all phases** (standing operator instruction) |
| Working tree | clean (no staged, unstaged, or untracked changes) |
| PR #10 | open / draft / not merged / mergeable (`https://github.com/velma-V1/builder/pull/10`) |
| Superseded branch | `claude/ph3-worker-engine-xefzze` @ `7e023a2` — 0 unique commits, inert |

### Completed Work (cumulative)

| Phase | Branch | Status | Tests | Evidence |
|---|---|---|---|---|
| PH-1 (Requirements & Contracts) | `claude/builder-handoff-pr8-inc9p8` | PASS, 96.85% cov | 288 passed, 1 skipped | `docs/verification/section-1-requirements-contracts.md` |
| PH-2 (Orchestrator: Queue & State Machine) | `claude/ph2-orchestrator-implementation` | PROM-PH2 PASS | 93 passed | `docs/verification/section-2-evidence-report.md` |
| Worker Execution Substrate (CMP-WORKER) | `claude/ph3-worker-engine` | Substrate gate PASS | 85 substrate + 93 PH-2 = 178 | `docs/verification/worker-execution-substrate-evidence-report.md` |

**None of the above branches have been merged into `main`.** Each builds on the prior:
PH-1 → PH-2 → substrate. The substrate branch (`claude/ph3-worker-engine`) contains all
cumulative work.

### Roadmap Alignment

| Roadmap phase | Status | Notes |
|---|---|---|
| PH-1: Requirements & Contracts | COMPLETE | Verified, promoted for phase order; final re-verify deferred but executed (DEF-01 resolved) |
| PH-2: Orchestrator (Queue & State Machine) | COMPLETE | 93 tests; PROM-PH2 passed |
| Worker Execution Substrate | COMPLETE (out-of-roadmap) | Prebuilt PH-4/PH-5 seam; **NOT roadmap PH-3** |
| **PH-3: Watchdog, Permissions, Approval, Audit & Tools** | **UNBUILT** | Plan exists: `docs/plans/section-3-orchestrator-watchdog-and-permissions.md` |
| PH-4: Model & Worker Routing | NOT STARTED | Depends on PH-3 security interfaces being frozen |
| PH-5: Sandbox & Process Isolation | NOT STARTED | Owns real `ProcessSpawner`; substrate provides the seam |
| PH-6 through PH-8 | NOT STARTED | — |

**Ordering constraint:** PH-4 may consume the Worker Execution Substrate seam **only after
roadmap PH-3 security interfaces (permission enforcement + tool gateway) are frozen**. No
roadmap dependency is bypassed.

**Authoritative classification:** `docs/WORKER-EXECUTION-SUBSTRATE-CLASSIFICATION.md`

### Decision Gate

Before any new work begins, the operator must explicitly authorize the next action. The
following are plausible next actions — **none is pre-authorized**:

1. **Merge PR #10** (Worker Execution Substrate) into `main` — currently draft/unmerged
2. **Begin roadmap PH-3 planning** (Watchdog, Permissions, Approval, Audit & Tools)
3. **Begin roadmap PH-3 implementation** (requires planning first)
4. Other operator-directed work

**Standing constraints (always in effect unless explicitly lifted):**
- Do not merge any branch into `main` without explicit authorization
- Do not modify `main` directly
- Do not begin implementation without planning approval
- Do not amend the Master Implementation Roadmap
- The "PH-3"/"T3.x"/"SEC-PH3-xx" labels in `src/factory/workers/` and `tests/workers/`
  refer to the substrate's development track, **not** roadmap PH-3 — see label mapping in
  `docs/WORKER-EXECUTION-SUBSTRATE-CLASSIFICATION.md` §3

### Key Documents (authority order)

1. `PROJECT_DEFINITION.md` — governing purpose, boundaries, priorities
2. `docs/00-DOCUMENTATION-INDEX.md` — full authority chain (read this first for navigation)
3. `docs/planning/00-CONTINUATION-LEDGER.md` — cross-session state of record (§9 is current)
4. `docs/planning/00-PLANNING-AUTHORITY-LEDGER.md` — planning document registry
5. `docs/WORKER-EXECUTION-SUBSTRATE-CLASSIFICATION.md` — substrate reclassification record
6. `docs/10-IMPLEMENTATION-ROADMAP.md` — master roadmap (unamended)
7. `docs/plans/section-3-orchestrator-watchdog-and-permissions.md` — roadmap PH-3 plan (unbuilt)
8. `HANDOFF-PH2.md` — PH-2 handoff (corrected forward-refs)
9. This file — substrate handoff + transfer record

### Restart Instructions (Repository Realignment Protocol)

A new session MUST perform these checks before taking any action:

```
1. Verify branch:     git branch --show-current
                      → must be claude/ph3-worker-engine

2. Verify HEAD:       git rev-parse --short HEAD
                      → must be 699279c (or a later commit on this branch)

3. Verify remote:     git diff origin/claude/ph3-worker-engine --stat
                      → must be empty (synced)

4. Verify main:       git log --oneline origin/main -1
                      → 9bce1ca (untouched)

5. Verify tree:       git status --short
                      → must be empty (clean)

6. Verify PR #10:     Check via GitHub — open/draft/not merged

7. Read authority:    docs/00-DOCUMENTATION-INDEX.md
                      docs/planning/00-CONTINUATION-LEDGER.md §9
                      docs/WORKER-EXECUTION-SUBSTRATE-CLASSIFICATION.md

8. Report state:      Report all findings to operator BEFORE any action
```

### Bootstrap Prompt

Copy this prompt verbatim into a new Claude Code session to resume:

> Resume this repository from the authoritative handoff at
> `HANDOFF-WORKER-EXECUTION-SUBSTRATE.md`. Perform Repository Realignment
> before taking action. Verify the branch, commit, remote state, working
> tree, roadmap authority, dependency map, and PR #10 against the handoff.
> Do not rely on previous chat history. Do not merge, plan, or implement
> until you report the verified current state and receive explicit operator
> instruction.
