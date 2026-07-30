# PH-5 Requirement-to-Test Matrix (preinstallation)

Maps each PH-5 preinstallation-core requirement (from the SYSTEM directive + section-5 plan) to its
module and deterministic test(s). Git tests use real temporary repositories; sandbox/secret/network
use deterministic fakes; cache/staging are pure logic.

| # | Requirement | Module | Test(s) |
|---|---|---|---|
| R1 | Git manager core | `git/manager.py` | `test_git_manager` (whole file) |
| R2 | approved baseline manifest | `git/models.py` | `test_manifest_primary_and_lookup`, `test_manifest_missing_primary_raises` |
| R3 | branch lifecycle from baseline | `git/manager.py` | `test_create_task_branch_from_baseline` |
| R4 | worktree lifecycle | `git/manager.py` | `test_worktree_lifecycle` |
| R5 | repository ownership validation | `git/manager.py` | `test_checkpoint_rejects_out_of_scope_changes` |
| R6 | exact change tracking | `git/manager.py` | `test_exact_change_tracking`, `test_rename_is_not_miscounted` |
| R7 | protected-ref denial | `git/manager.py` | `test_protected_ref_and_force_push_guards`, `test_checkpoint_on_protected_branch_denied` |
| R8 | force-push denial | `git/manager.py` | `test_protected_ref_and_force_push_guards` |
| R9 | commit-trailer validation | `git/trailers.py` | `test_git_trailers` (whole file) |
| R10 | checkpoint & recovery | `git/manager.py` | `test_checkpoint_owned_paths_only`, `test_checkpoint_empty_is_rejected` |
| R11 | sandbox identity | `sandbox/fake_backend.py` | `test_provision_clean_spec_records_identity` |
| R12 | fake WSL/Docker backend | `sandbox/fake_backend.py` | `test_sandbox_backend` (whole file) |
| R13 | non-root policy | `sandbox/policy.py` | `test_root_execution_denied_two_ways` |
| R14 | Windows-native execution denial | `sandbox/policy.py` | `test_prohibited_flags_are_denied[windows_native]` |
| R15 | mount policy | `sandbox/policy.py` | `test_writable_host_project_mount_denied`, `test_readonly_host_project_mount_allowed` |
| R16 | resource limits | `sandbox/policy.py` | `test_nonpositive_resource_limits_denied` |
| R17 | explicit runtime-unavailable results | `sandbox/fake_backend.py` | `test_provision_when_backend_unavailable_is_explicit` |
| R18 | restart reconciliation | `sandbox/fake_backend.py` | `test_reconcile_destroys_orphans` |
| R19 | secret broker interface + fake backend | `secret/*` | `test_backend_satisfies_protocol`, `test_inject_creates_active_lease` |
| R20 | scoped secret leases | `secret/models.py` | `test_inject_creates_active_lease`, `test_expired_lease_is_not_active` |
| R21 | redaction | `secret/redaction.py` | `test_redaction_hides_active_material`, `test_standalone_redaction_helpers` |
| R22 | revocation | `secret/fake_backend.py` | `test_revoke_drops_material`, `test_revoke_task_clears_all_for_task` |
| R23 | no secret persistence | `secret/fake_backend.py` | `test_revoke_drops_material` (`has_persisted_material`) |
| R24 | network broker interface + fake backend | `network/*` | `test_backend_satisfies_protocol`, `test_permitted_request_allowed` |
| R25 | default deny | `network/fake_backend.py` | `test_default_deny_without_contract` |
| R26 | explicit allow rules | `network/fake_backend.py` | `test_protocol_and_method_denied`, `test_malformed_and_unlisted_destinations` |
| R27 | redirect containment | `network/fake_backend.py` | `test_redirect_containment` |
| R28 | DNS / destination validation | `network/fake_backend.py` | `test_malformed_and_unlisted_destinations`, `test_empty_destination_is_invalid` |
| R29 | cache project/sandbox scoping | `cache/store.py` | `test_sandbox_scoping_is_isolated` |
| R30 | contamination prevention | `cache/store.py` | `test_invalidate_one_scope_leaves_the_other` |
| R31 | cache invalidation | `cache/store.py` | `test_invalidate_scope_bulk`, `test_get_miss_raises` |
| R32 | credential-free cache | `cache/store.py` | `test_credential_material_rejected` |
| R33 | staging containment (single exit) | `staging/manager.py` | `test_staging_is_sealed_after_promotion` |
| R34 | provenance + inventory | `staging/inspection.py` | `test_clean_output_passes_inspection` |
| R35 | inspection gate | `staging/inspection.py` | `test_*` (secret/executable/scope/escape/bomb) |
| R36 | promotion denial without authorization | `staging/manager.py` | `test_promote_requires_clean_and_authorization` |
| R37 | process-tree termination | `staging/manager.py` | `test_process_tree_termination_is_complete`, `test_process_tree_dedupes_shared_descendants` |

All 37 requirements are covered by passing deterministic tests at 100% branch coverage.
