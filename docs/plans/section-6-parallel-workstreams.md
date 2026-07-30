# PH-6 (Section 6) — Three Parallel Major-Stage Workstreams — Implementation Plan

**Status:** Approved planning order (L25.1) · **Governing:** `01D`, `01C §13`, `01L §3.1`, `01R` R2. Roadmap spec: `docs/10` PH-6. In force with `01R`.

**R2 applied:** the default execution unit is up to three parallel major-stage **workstreams**; the Worker/Reviewer paired-lane pattern is optional/secondary. This phase builds and demonstrates the ≤3-workstream capability.

## Task decomposition
### Task 6.1 — Workstream contracts + admission (independence-before-parallel)
- Owned paths: `src/factory/workstream/**`. Deliverables: workstream declaration (owner/scope/inputs/outputs/owned-contracts/completion-gate); independence check (`01D §3.4`); configurable ≤3 cap. Contracts: CTR-WORKSTREAM. Tests (`01D` 27): cap not exceeded; parallel blocked when contracts/deps/ownership/baselines/resources unstable; **independence proven before admission (not path-disjointness alone)**. Evidence: admission ETM. Completion: `01D §2.1-8`.
### Task 6.2 — Lane lifecycle + consistency with the authoritative SM
- Owned paths: `src/factory/workstream/lane/**`. Deliverables: lane lifecycle (`01D §3.1`) as a separate dimension consistent with `01L §3.1`. Contracts: CTR-LANE-LIFECYCLE. Tests: only legal lane transitions; a lane cannot be ACTIVE when its task is paused/cancelled/failed/quarantined/rolled-back; isolated checkouts prevent cross-lane contamination. Evidence: lane ETM. Completion: `01D §3.1`.
### Task 6.3 — Conflict detection beyond files + integration baselines
- Owned paths: `src/factory/workstream/conflict/**`. Deliverables: module/symbol/schema/API/migration/config/dependency/generated/logical conflict detection; immutable integration baseline. Tests: conflicts detected before integration; no silent baseline rebase/merge/change (`01D §3.3-3.4`). Evidence: conflict ETM. Completion: `01D §3.3-3.4`.
### Task 6.4 — Scheduler priority/interruption + checkpointed pause
- Owned paths: `src/factory/workstream/scheduler/**`. Deliverables: priority/interruption policy (5-min checkpoint deadline, starvation, priority inversion, resume order, `01D §3.5`); checkpointed pause before eviction. Tests: urgent interrupt via verified checkpointed pause only; checkpoint deadlines/starvation/resume order; 3-failure quarantine on normalized signature. Evidence: scheduler ETM. Completion: `01D §3.5/§3.7`.
### Task 6.5 — Integration coordinator + three-workstream demonstration
- Owned paths: `src/factory/integration/**`. Deliverables: coordinator (compare baselines/manifests, validate contracts, combine approved commits via Promotion/Integration Service, run integration verification, evidence-backed remediation) — **never edits source**; three-component parallel demo. Tests (IP-3): cross-workstream integration tests run before promotion; coordinator cannot modify source/tests/contracts; remediation returns to named owning lanes. Evidence: integration ETM (VM-4). Completion: `01D §3.8/§6`.

## Acceptance & handoff
Acceptance: `01D §6`(27) PASS (VM-4). Rollback boundary: per-workstream verified checkpoints; partial work preserved unpromoted. Promotion gate: PH-6 exit approval. Handoff → PH-7 (integration coordinator completed; evidence/promotion).
