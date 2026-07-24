# PH-2 (Section 2) — Orchestrator: Task Queue & State Machine — Implementation Plan

**Status:** Approved planning order (L25.1) · **Governing:** `01L §3.1`, `01D §3.1`, `02 §4/§6/§7`, `01M §3.6`, `01R` R1. Roadmap spec: `docs/10` PH-2. In force with `01R`.

**R1 is applied throughout:** the **Orchestrator** is the sole authoritative writer; there is no "watchdog-writes-state" component here (the Watchdog is built in PH-3 as a separate read-only supervisor).

## Task decomposition
### Task 2.1 — State definitions & legal transition table (authoritative `01L §3.1`)
- Owned paths: `src/factory/orchestrator/state/**`. Deliverables: the `01L §3.1` task/workstream states + legal-transition policy (versioned). Interfaces: `transition_request`/`query`. Deps: PH-1. Tests: only legal transitions occur; invalid → fail closed + audit event; every change records prev/new/cause/actor/order/timestamp/evidence. Evidence: state-machine ETM. Completion: `01L` #3–5.
### Task 2.2 — Runtime-state DB + transactional Orchestrator writer
- Owned paths: `src/factory/orchestrator/store/**`, `migrations/runtime/0001_state.sql`. Deliverables: SQLite WAL/FK store; Orchestrator as sole writer; atomic transition (validate→apply→counter→audit→commit). Contracts: CTR-RUNTIME-STATE-DB. Tests: atomic transition/rollback; **no other component writes** authoritative state; generation only on activation. Evidence: writer-boundary ETM. Completion: `02 §4/§7`.
### Task 2.3 — Durable journal + startup reconciliation (RM-1)
- Owned paths: `src/factory/orchestrator/journal/**`. Deliverables: durable transactional journal (flush-before-success); startup reconciliation. Contracts: CTR-RECOVERY-JOURNAL. Tests (journal-replay #17, crash #16): critical transition not reported before durable commit; idempotent replay; unknown state → BLOCKED/QUARANTINED. Evidence: journal ETM. Completion: `01M §3.6/§2.18`.
### Task 2.4 — Fenced expiring leases (fencing-token #18)
- Owned paths: `src/factory/orchestrator/leases/**`. Deliverables: expiring leases + monotonic fencing tokens for task/resource/workspace/branch/model/sandbox/promotion locks. Contracts: CTR-LEASE-FENCING. Tests: stale former owner cannot write after a newer token; monotonic timing across wall-clock changes. Evidence: fencing ETM. Completion: `01M §2.19/§3.6`.
### Task 2.5 — Queue, dependencies, cancellation, idempotent restart + core memory
- Owned paths: `src/factory/orchestrator/queue/**`, `src/factory/memory/core/**`. Deliverables: queue/dependency readiness/priority/cancellation; idempotent restart; core project-authority memory records. Contracts: CTR-MEMORY-RECORD(partial). Tests: dependency gating; idempotent restart; memory no-auto-persist + provenance. Evidence: queue+memory ETM. Completion: `05 S2`; `01F` core.

## Acceptance & handoff
Acceptance: `05 S2` outputs + `01L §3.1`/`01M §3.6` criteria PASS; external-process deadlock is detectable (prep for PH-3 Watchdog). Rollback boundary: journal-authoritative; migrations transactional. Promotion gate: PH-2 exit approval. Handoff → PH-3 (Watchdog observes the Orchestrator; permission/approval/audit write through it).
