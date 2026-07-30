# PH-6 (Section 6) — Three Parallel Workstreams — Simulated-Core Evidence

**Scope:** PH-6 simulated workstream core — workstream engine, lane lifecycle, conflict detection,
scheduler/quarantine, and integration coordinator, demonstrated end-to-end against the PH-4/PH-5
deterministic fakes (simulated IP-3).
**Status:** `PH6_SIMULATED_CORE_COMPLETE — LIVE_INTEGRATION_PENDING`.
**Not:** a phase promotion, a merge, or any live-runtime claim. `main` and PR #10 unchanged.
**Base:** continues from PH-5 (`26f9657`).
**Governing:** `docs/plans/section-6-parallel-workstreams.md`, `01D`, `01C §13`, `01L §3.1`, `01R` R2;
CTR-WORKSTREAM / CTR-LANE-LIFECYCLE.

## Verdict

**PASS (simulated).** The workstream engine is implemented, tested to 100% branch coverage, gated,
and demonstrated running three independent workstreams end-to-end. Live sandbox/router assignment and
live cross-workstream integration (IP-3) remain pending installation
(`ph6-pending-live-gate-register.md`). File-path disjointness alone is never treated as independence —
module/symbol/schema/API/migration/config/dependency/logical conflicts are all detected.

## What was built (owner paths per the section-6 plan)

| Task | Owner path | Delivered (simulated) |
|---|---|---|
| 6.1 Workstream contracts + admission | `src/factory/workstream/` | CTR-WORKSTREAM, `AdmissionController` (≤3 cap + independence gate), `OwnershipRegistry` (single-writer + shared-contract leases) |
| 6.2 Lane lifecycle + isolated checkouts | `src/factory/workstream/lane/` | 12-state `LaneMachine` with legal-transition + task-consistency enforcement + audit; `IsolatedCheckoutAssigner` |
| 6.3 Conflict detection + baseline | `src/factory/workstream/conflict/` | `ConflictDetector` (10 dimensions beyond files); `BaselineTracker` (immutable baseline + drift detection) |
| 6.4 Scheduler + quarantine | `src/factory/workstream/scheduler/` | `WorkstreamScheduler` (checkpointed interruption, resume order, starvation); `FailureCounter` (normalized signature, 3-failure quarantine) |
| 6.5 Integration coordinator + IP-3 | `src/factory/integration/` | `IntegrationCoordinator` (compare/validate/combine/assign remediation — never edits source); `run_simulated_ip3` |

## Gate results (CPython 3.12.11, this environment)

| Gate | Result |
|---|---|
| `scripts/verify_ph6_preinstall.py` | **11/11 PASS** |
| PH-6 focused tests | **35 passed** (workstream 29, integration 6) |
| Branch coverage (2 PH-6 package trees) | **100.00%** (obligation ≥95%) |
| Simulated three-workstream demonstration (IP-3) | integrates via fakes; coordinator never edits source |
| Ruff (`src` + `tests`) | clean |
| mypy `--strict` | clean (27 source files) |
| Full repository (`pytest`) | **1023 passed, 1 skipped** (Windows-only); +35 vs the PH-5 (988) state, no regression |
| PH-5 verifier | still 10/10 |
| PH-4 verifier | still 10/10 |
| RPH-3 integrated verifier | still 10/10 |
| Worker Execution Substrate verifier | still 18/18 |

## Governing-invariant coverage (`01D §6`)

| Criterion | Where enforced | Test |
|---|---|---|
| §6.1 active-workstream cap | `AdmissionController` | `test_cap_is_enforced` |
| §6.2 parallel blocked when unstable | `AdmissionController` | `test_baseline_mismatch_is_unstable`, `test_unresolved_dependency_is_unstable` |
| §6.3 declared workstream contract | `WorkstreamContract` | admission tests (constructed contracts) |
| §6.5/§6.7 single write owner | `OwnershipRegistry` | `test_single_write_owner_per_resource` |
| §6.6 isolated checkouts | `IsolatedCheckoutAssigner` | `test_isolated_checkout_assignment` |
| §6.8 conflicts beyond files detected | `ConflictDetector` | `test_set_dimension_conflicts_detected`, `test_migration_id_and_order_conflicts` |
| §6.10 no silent baseline change | `BaselineTracker` | `test_baseline_is_immutable_and_drift_detected` |
| §6.11 only legal lane transitions, auditable | `LaneMachine` | `test_legal_transition_chain`, `test_illegal_transition_fails_closed_and_audits` |
| §3.1 lane not ACTIVE when task blocked | `LaneMachine` | `test_lane_cannot_be_active_when_task_blocked` |
| §6.14/§6.26 interrupt via checkpointed pause | `WorkstreamScheduler.interrupt` | `test_interrupt_only_via_checkpointed_pause` |
| §6.15 resume order + starvation | `WorkstreamScheduler` | `test_resume_order_follows_policy`, `test_starvation_escalation` |
| §6.24 three-failure quarantine | `FailureCounter` | `test_three_same_signature_failures_quarantine` |
| §6.25 transient failures excluded | `FailureCounter` | `test_transient_failures_are_excluded` |
| §6.20 remediation to owning lanes | `IntegrationCoordinator` | `test_conflicts_block_and_assign_remediation_to_owning_lanes` |
| §6.21 integration gate never edits source | `IntegrationCoordinator` (`COORDINATOR_EDITS_SOURCE=False`) | `test_conflicts_block_and_assign_remediation_to_owning_lanes` |
| §6.18/§6.19 local gate + integration | `IntegrationCoordinator` | `test_local_gate_failure_blocks`, `test_clean_integration_promotes_all` |

## Boundaries held

- No installation, no live runtime; sandbox/router assignment simulated via PH-4/PH-5 fakes.
- `main` (`9bce1ca`) unchanged; PR #10 (`7b1922e`) draft/open/unmodified.
- No merge, no phase promotion; the integration coordinator never edits source (structural).
- RPH-3 spine, substrate, PH-4 routing, and PH-5 isolation unmodified; full repo regression green.

See the requirement-to-test matrix, failure-path matrix, simulated IP-3 report, and pending-live-gate
register.
