# Worker Execution Substrate — Classification Record

**Document ID:** WES-CLASS-000
**Status:** Authoritative classification (operator decision, 2026-07-25)
**Applies to:** all work on branch `claude/ph3-worker-engine`
**Authority note:** This record does NOT amend the Master Implementation Roadmap
(`docs/10-IMPLEMENTATION-ROADMAP.md`). It classifies an out-of-roadmap component and corrects
prior documentation that mislabeled it as roadmap PH-3.

---

## 1. Decision

The completed work on `claude/ph3-worker-engine` is reclassified as the
**WORKER EXECUTION SUBSTRATE** — **prebuilt PH-4/PH-5 execution infrastructure**.

- It is **NOT** roadmap PH-3.
- **Roadmap PH-3 (Watchdog, Permissions, Approval, Audit & Tools) remains UNBUILT.**
- The Master Implementation Roadmap is **not amended**; **no new numbered phase is inserted**.
- The real `ProcessSpawner` and sandbox/process isolation remain **PH-5** responsibilities.
- **PH-4 may consume this seam only after the true PH-3 security interfaces
  (permission enforcement + tool gateway) are frozen.**
- **No roadmap dependency is bypassed.**

Chosen options: **A (reclassify, do not amend roadmap) + C (treat as prebuilt PH-4/PH-5 seam)**.

---

## 2. What the substrate is (and is not)

**Is:** a verified, self-contained execution substrate under `src/factory/workers/` —
worker-process lifecycle (pool, spawner protocols, reclaim, crash detection), fenced-lease
coordination over PH-2 leases, bounded untrusted-output streaming, task dispatch, state
integration through the PH-2 single writer (R1), and crash/startup recovery (R3). It consumes
**only frozen PH-2 interfaces** and adds **no new migrations**.

**Is not:** the roadmap's PH-3 security spine. It builds none of the Watchdog, permission
enforcement, approval engine, audit writer/validator, tool registry/gateway, or Safe Mode.

**Roadmap placement of its responsibilities:**
| Substrate capability | Roadmap owner |
|---|---|
| Bounded coding-worker adapter (real spawn target) | PH-4, Task 4.2 (Aider adapter) |
| Real `ProcessSpawner` / sandbox / process isolation | PH-5 |
| Task-execution state mechanics (start/finalize/cancel/reconcile) | PH-2 primitives (already built) + consumed by PH-4/PH-5/PH-6 |

The substrate deliberately exposes a `ProcessSpawner`/`ProcessHandle` **seam** and leaves the real
implementation to its owning phase (PH-5). See "Known Limitations" in the substrate handoff.

---

## 3. Label mapping (removes ambiguity without touching verified code)

The verified implementation and its tests use an internal development-track vocabulary. Within
`src/factory/workers/**` and `tests/workers/**`, the following labels denote **this substrate's
development track only** and do **NOT** refer to roadmap PH-3:

| Label in code/tests | Meaning here | NOT |
|---|---|---|
| "PH-3", "Phase 3" (in workers docstrings) | Worker Execution Substrate track | roadmap PH-3 (Watchdog) |
| `T3.1`…`T3.5` | substrate task breakdown | roadmap Section 3 tasks |
| `SEC-PH3-01`…`05` | substrate security checks | roadmap PH-3 security spine (VM-2) |
| `PROM-PH3` | substrate promotion gate | roadmap PH-3 exit gate |

These identifiers are **preserved as-is** to avoid rewriting verified implementation
(operator instruction: "Do not redesign or rewrite the verified implementation"). This mapping is
the authoritative disambiguation.

---

## 4. Documentation corrections applied (2026-07-25)

Renamed (identity de-collided from roadmap Section 3):
- `HANDOFF-PH3.md` → `HANDOFF-WORKER-EXECUTION-SUBSTRATE.md`
- `docs/plans/section-3-worker-engine.md` → `docs/plans/worker-execution-substrate.md`
- `docs/verification/section-3-evidence-report.md` → `docs/verification/worker-execution-substrate-evidence-report.md`
- `docs/verification/section-3-test-summary.md` → `docs/verification/worker-execution-substrate-test-summary.md`
- `docs/planning/PH3-*.md` (×4) → `docs/planning/WES-*.md`
- `scripts/verify_section3.py` → `scripts/verify_worker_substrate.py`

Corrected in place (removed "PH-3 = Worker Engine" / roadmap-completion claims):
- `README.md`, `HANDOFF-PH2.md`, `docs/verification/section-2-evidence-report.md`,
  `docs/specifications/components/worker-engine-spec.md`, `docs/planning/00-CONTINUATION-LEDGER.md`

Untouched (preserved): all of `src/factory/workers/**` and `tests/workers/**`
(verified implementation), and `docs/plans/section-3-orchestrator-watchdog-and-permissions.md`
(the real roadmap PH-3 plan).

---

## 5. Superseded branch

`claude/ph3-worker-engine-xefzze` — tip `7e023a2` (the PH-2 base), **zero commits unique to it**,
not present on the remote. It contains **no unique required work** and is **superseded by
`claude/ph3-worker-engine`**. Left inert; not fast-forwarded.

---

## 6. Remaining roadmap PH-3 work (unchanged, still to build)

Per `docs/plans/section-3-orchestrator-watchdog-and-permissions.md` and roadmap §PH-3:
independent read-only **Watchdog** + narrow interface; **permission enforcement** (+ deletion
approval-gating, Dec B; autonomy envelope, Dec A); **approval engine/queue**; tamper-evident
**audit writer + chain validator**; **tool registry + gateway** + safe file-op; diagnostic
**Safe Mode**. Acceptance: `01M`(32) + `01K`(25), VM-2 security spine. **None of this is built.**
