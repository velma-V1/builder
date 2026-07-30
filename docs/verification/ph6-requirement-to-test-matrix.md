# PH-6 Requirement-to-Test Matrix (simulated)

Maps each PH-6 simulated-core requirement (from the SYSTEM directive + section-6 plan) to its module
and deterministic test(s). All tests are offline; sandbox/router assignment is simulated via the
PH-4/PH-5 fakes.

| # | Requirement | Module | Test(s) |
|---|---|---|---|
| R1 | workstream contract | `workstream/models.py` | admission tests (constructed contracts) |
| R2 | lane lifecycle state machine | `workstream/lane/lifecycle.py` | `test_legal_transition_chain`, `test_is_legal_helper` |
| R3 | three-workstream cap | `workstream/admission.py` | `test_cap_is_enforced` |
| R4 | independence admission gate | `workstream/admission.py` | `test_scope_overlap_denies_independence`, `test_path_prefix_overlap_all_arcs` |
| R5 | ownership leases | `workstream/ownership.py` | `test_single_write_owner_per_resource` |
| R6 | isolated checkout assignment | `workstream/lane/checkout.py` | `test_isolated_checkout_assignment` |
| R7 | fake sandbox assignment | `integration/demo.py` | `test_simulated_ip3_end_to_end` (distinct `sandbox_ids`) |
| R8 | fake router assignment | `integration/demo.py` | `test_simulated_ip3_end_to_end` (routes present) |
| R9 | single write owner | `workstream/ownership.py` | `test_single_write_owner_per_resource` |
| R10 | shared contract owner | `workstream/ownership.py` | `test_same_owner_reacquire_is_allowed` |
| R11 | baseline tracking | `workstream/conflict/baseline.py` | `test_baseline_is_immutable_and_drift_detected` |
| R12 | baseline drift detection | `workstream/conflict/baseline.py` | `test_baseline_is_immutable_and_drift_detected` |
| R13 | file conflict detection | `workstream/conflict/detector.py` | `test_set_dimension_conflicts_detected` |
| R14 | semantic conflict detection | `workstream/conflict/detector.py` | `test_set_dimension_conflicts_detected` (symbol/api/logical) |
| R15 | dependency conflict detection | `workstream/conflict/detector.py` | `test_config_and_dependency_version_conflicts` |
| R16 | schema & migration conflict detection | `workstream/conflict/detector.py` | `test_set_dimension_conflicts_detected`, `test_migration_id_and_order_conflicts` |
| R17 | scheduler priority | `workstream/scheduler/policy.py` | `test_resume_order_follows_policy`, `test_starvation_escalation` |
| R18 | checkpointed interruption | `workstream/scheduler/policy.py` | `test_interrupt_only_via_checkpointed_pause` |
| R19 | bounded resume | `workstream/scheduler/policy.py` | `test_resume_order_follows_policy` |
| R20 | failure counter | `workstream/scheduler/quarantine.py` | `test_different_signature_resets_sequence` |
| R21 | three-failure quarantine | `workstream/scheduler/quarantine.py` | `test_three_same_signature_failures_quarantine` |
| R22 | integration coordinator | `integration/coordinator.py` | `test_clean_integration_promotes_all` |
| R23 | coordinator never edits source | `integration/coordinator.py` | `test_conflicts_block_and_assign_remediation_to_owning_lanes` |
| R24 | audit & evidence hooks | `workstream/lane/lifecycle.py` | `test_illegal_transition_fails_closed_and_audits` (audit log) |
| R25 | simulated three-workstream demonstration | `integration/demo.py` | `test_simulated_ip3_end_to_end` |

All 25 requirements are covered by passing deterministic tests at 100% branch coverage.
