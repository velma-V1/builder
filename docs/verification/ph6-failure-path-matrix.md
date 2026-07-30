# PH-6 Failure-Path Matrix (simulated)

Every failure/denial mode, the deterministic injection, and the required fail-closed behavior. No
unstable or non-independent parallel work is admitted; no conflict silently integrates; the
integration gate never edits source.

| # | Failure / denial mode | Injection | Required behavior | Test |
|---|---|---|---|---|
| F1 | fourth workstream over cap | 3 active + 1 | `DENIED_CAP` | `test_cap_is_enforced` |
| F2 | scope overlap (not path-disjoint) | overlapping scope prefix | `DENIED_NOT_INDEPENDENT` + `SCOPE_OVERLAP` | `test_scope_overlap_denies_independence` |
| F3 | shared owned contract | same owned contract | `SHARED_CONTRACT` finding | `test_shared_contract_denies_independence` |
| F4 | baseline mismatch | divergent baseline | `DENIED_UNSTABLE` + `BASELINE_MISMATCH` | `test_baseline_mismatch_is_unstable` |
| F5 | unresolved dependency | dep not complete | `DENIED_UNSTABLE` | `test_unresolved_dependency_is_unstable` |
| F6 | root-scope overlap | `**` scope | `SCOPE_OVERLAP` (both orderings) | `test_root_scope_overlaps_everything` |
| F7 | concurrent write ownership | second writer | `OWNERSHIP_CONFLICT` | `test_single_write_owner_per_resource` |
| F8 | double checkout assignment | assign lane twice | `CHECKOUT_ALREADY_ASSIGNED` | `test_isolated_checkout_assignment` |
| F9 | illegal lane transition | PROPOSED→ACTIVE | `LANE_ILLEGAL_TRANSITION` + audit | `test_illegal_transition_fails_closed_and_audits` |
| F10 | lane ACTIVE while task blocked | task PAUSED | `LANE_TASK_INCONSISTENT` | `test_lane_cannot_be_active_when_task_blocked` |
| F11 | file/symbol/schema/api/generated/logical conflict | overlapping manifests | conflict detected, blocks integration | `test_set_dimension_conflicts_detected` |
| F12 | duplicate / ordered migration | same id or same order | `MIGRATION` conflict | `test_migration_id_and_order_conflicts` |
| F13 | config / dependency version clash | differing values | `CONFIG` / `DEPENDENCY` conflict | `test_config_and_dependency_version_conflicts` |
| F14 | silent baseline change | re-record different commit | `BASELINE_IMMUTABLE` | `test_baseline_is_immutable_and_drift_detected` |
| F15 | three equivalent failures | same signature ×3 | quarantine | `test_three_same_signature_failures_quarantine` |
| F16 | transient failure miscounted | transient in sequence | excluded, no quarantine | `test_transient_failures_are_excluded` |
| F17 | interrupt without checkpoint | no checkpoint in deadline | `BLOCKED`, never unsafe eviction | `test_interrupt_only_via_checkpointed_pause` |
| F18 | interrupt non-preemptible commit | commit boundary | `NON_PREEMPTIBLE` | `test_interrupt_only_via_checkpointed_pause` |
| F19 | interrupt by non-higher priority | requester ≤ holder | `NOT_HIGHER_PRIORITY` | `test_interrupt_only_via_checkpointed_pause` |
| F20 | integrate with failed local gate | local gate not passed | `BLOCKED_LOCAL_GATE`, no promotion | `test_local_gate_failure_blocks` |
| F21 | integrate divergent baselines | different baselines | `BLOCKED_BASELINE` | `test_divergent_baseline_blocks` |
| F22 | integrate with conflicts | overlapping manifests | `BLOCKED_CONFLICTS` + remediation to owning lanes | `test_conflicts_block_and_assign_remediation_to_owning_lanes` |
| F23 | coordinator editing source | (structural) | `COORDINATOR_EDITS_SOURCE=False`; only remediation returned | `test_conflicts_block_and_assign_remediation_to_owning_lanes` |
