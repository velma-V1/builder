# PH-5 Failure-Path Matrix (preinstallation)

Every failure/abuse mode, the deterministic injection, and the required fail-closed behavior. No
failure silently succeeds; every isolation breach is denied and, where applicable, recorded as a
security event.

| # | Failure / abuse mode | Injection | Required behavior | Test |
|---|---|---|---|---|
| F1 | write to protected ref | `guard_protected_ref("main")` | `PROTECTED_REF_WRITE` (security) | `test_protected_ref_and_force_push_guards` |
| F2 | checkpoint on protected branch | checkpoint while on `main` | `PROTECTED_REF_WRITE` | `test_checkpoint_on_protected_branch_denied` |
| F3 | automatic force-push | `guard_no_force_push(force=True)` | `FORCE_PUSH_DENIED` (security) | `test_protected_ref_and_force_push_guards` |
| F4 | unexplained local changes at start | dirty tree | `UNEXPLAINED_CHANGES` | `test_require_clean_start` |
| F5 | out-of-scope checkpoint | change outside owned paths | `CHECKPOINT_SCOPE` (security) | `test_checkpoint_rejects_out_of_scope_changes` |
| F6 | empty checkpoint | no changes | `CHECKPOINT_EMPTY` | `test_checkpoint_empty_is_rejected` |
| F7 | trailer disagreement | mismatched trailers | `TRAILER_MISMATCH` | `test_validate_against_detects_mismatch` |
| F8 | unknown Factory trailer | `Factory-Bogus:` | `TRAILER_UNKNOWN` | `test_unknown_factory_trailer_is_rejected` |
| F9 | bad git command | bad baseline commit | `GIT_COMMAND_FAILED` | `test_create_task_branch_bad_baseline_fails` |
| F10 | privileged / host-socket / host-ns sandbox | prohibited flag | `SANDBOX_POLICY_DENIED` (security) | `test_prohibited_flags_are_denied` |
| F11 | root sandbox | `run_as_root` / `uid=0` | `ROOT_DENIED` | `test_root_execution_denied_two_ways` |
| F12 | Windows-native sandbox | `windows_native=True` | `WINDOWS_NATIVE_DENIED` | `test_prohibited_flags_are_denied[windows_native]` |
| F13 | writable host-project mount | RW host-project mount | `HOST_PROJECT_WRITE_DENIED` | `test_writable_host_project_mount_denied` |
| F14 | missing resource limits | non-positive limit | `RESOURCE_LIMITS_REQUIRED` | `test_nonpositive_resource_limits_denied` |
| F15 | sandbox backend down | `available=False` | explicit `RUNTIME_UNAVAILABLE` | `test_provision_when_backend_unavailable_is_explicit` |
| F16 | orphaned sandbox after restart | reconcile without it | orphan destroyed | `test_reconcile_destroys_orphans` |
| F17 | isolation boundary breach | `boundary_failure` | destroy + security clearance | `test_boundary_failure_destroys_and_requires_clearance` |
| F18 | unknown secret ref | inject unknown | `SECRET_UNKNOWN` | `test_inject_unknown_ref_rejected` |
| F19 | non-positive secret TTL | `max_ttl=0` | `SECRET_TTL_INVALID` | `test_inject_bad_ttl_rejected` |
| F20 | secret leaked to export | material in export text | `SECRET_IN_EXPORT` | `test_scan_export_blocks_leaked_secret` |
| F21 | secret survives disposal | revoke then check | no active material | `test_revoke_task_clears_all_for_task` |
| F22 | network without contract | approval `None` | `NO_CONTRACT` deny | `test_default_deny_without_contract` |
| F23 | unsolicited inbound | inbound request | `INBOUND_DENIED` | `test_inbound_denied_unless_permitted` |
| F24 | expired network contract | `now >= expires_at` | `EXPIRED` | `test_expired_contract_denied` |
| F25 | off-allowlist destination/protocol/method | mismatched request | `DESTINATION/PROTOCOL/METHOD_DENIED` | `test_malformed_and_unlisted_destinations`, `test_protocol_and_method_denied` |
| F26 | malformed destination | `"bad host/path"`, `""` | `DESTINATION_INVALID` | `test_malformed_and_unlisted_destinations`, `test_empty_destination_is_invalid` |
| F27 | redirect escapes allowlist | redirect to `evil.com` | denied by containment | `test_redirect_containment` |
| F28 | transfer over limit | cumulative bytes | `TRANSFER_LIMIT` | `test_transfer_limit_and_negative` |
| F29 | credential into cache | forbidden value in bytes | `CACHE_CREDENTIAL` | `test_credential_material_rejected` |
| F30 | cross-sandbox cache contamination | same bytes, two sandboxes | isolated entries | `test_sandbox_scoping_is_isolated`, `test_invalidate_one_scope_leaves_the_other` |
| F31 | cache miss after invalidation | get invalidated key | `CACHE_MISS` | `test_get_miss_raises` |
| F32 | staged secret/executable/bomb/escape/scope | crafted staged files | non-clean inspection blocks promotion | `test_secret_in_output_blocks_promotion` + inspection tests |
| F33 | unauthorized promotion | `authorized=False` | `PROMOTION_UNAUTHORIZED` | `test_promote_requires_clean_and_authorization` |
| F34 | staging after promotion | stage post-promote | `STAGING_SEALED` | `test_staging_is_sealed_after_promotion` |
