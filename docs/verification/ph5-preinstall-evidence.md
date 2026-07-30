# PH-5 (Section 5) — Git, Worktree & Sandbox Isolation — Preinstallation Evidence

**Scope:** PH-5 preinstallation isolation core — real Git on temporary repositories + deterministic
fake sandbox/secret/network backends + pure-logic cache/staging.
**Status:** `PH5_PREINSTALLATION_CORE_COMPLETE — LIVE_SANDBOX_PENDING`.
**Not:** a phase promotion, a merge, or any live-runtime claim. `main` and PR #10 unchanged.
**Base:** roadmap PH-3 promoted baseline; continues from PH-4 (`9dd851b`).
**Governing:** `docs/plans/section-5-git-worktree-and-sandbox.md`, `01I`, `01E`, `04`, `01R` Dec C;
CTR-BASELINE-MANIFEST / CTR-COMMIT-TRAILER / CTR-SECRET-REF / CTR-NETWORK-APPROVAL.

## Verdict

**PASS (preinstallation).** The isolation core is implemented, tested to 100% branch coverage, and
gated. Real WSL2/Docker execution, live container identity/mount/network-namespace validation, live
secret injection, and live resource enforcement remain pending installation
(`ph5-pending-live-gate-register.md`). Decision C is structural: no Windows-native execution path
exists — a Windows-native spec is expressible only to be rejected.

## What was built (owner paths per the section-5 plan)

| Task | Owner path | Delivered (preinstallation) |
|---|---|---|
| 5.1 Git & worktree lifecycle | `src/factory/git/` | `GitManager` on real repos: task branch from approved baseline, worktree lifecycle, owned-path checkpoints, exact change tracking, protected-ref + force-push denial, unexplained-change block, CTR-COMMIT-TRAILER validation, CTR-BASELINE-MANIFEST |
| 5.2 Sandbox lifecycle | `src/factory/sandbox/` | `SandboxBackend` interface + `FakeWslDockerBackend`; isolation policy (non-root, prohibited privileges, no writable host-project mount, Windows-native denial, hard limits); runtime-unavailable results; restart reconcile; boundary-failure destroy + clearance |
| 5.3 Secret broker | `src/factory/secret/` | `SecretBroker` interface + `FakeSecretBackend`: scoped TTL leases, redaction, revoke-and-forget, pre-export scan (CTR-SECRET-REF) |
| 5.3 Network broker | `src/factory/network/` | `NetworkBroker` interface + `FakeNetworkBackend`: default-deny, allowlists, expiry, no inbound, redirect containment, destination validation, transfer limits (CTR-NETWORK-APPROVAL) |
| 5.4 Cache isolation | `src/factory/cache/` | `ContentAddressedCache`: content-addressed, immutable, project/sandbox scoping, contamination prevention, credential-free, trusted invalidation |
| 5.4 Quarantined staging | `src/factory/staging/` | `QuarantinedStaging`: single exit, inventory+hash+provenance, path-escape/secret/executable/archive-bomb/scope inspection, promotion denied without clean gate + authorization, complete process-tree termination |

## Gate results (CPython 3.12.11, this environment)

| Gate | Result |
|---|---|
| `scripts/verify_ph5_preinstall.py` | **10/10 PASS** |
| PH-5 focused tests | **84 passed** (git 23, sandbox 19, secret 11, network 11, cache 9, staging 11) |
| Branch coverage (6 PH-5 packages) | **100.00%** (obligation ≥95%) |
| Ruff (`src` + `tests`) | clean |
| mypy `--strict` | clean (42 source files) |
| Full repository (`pytest`) | **988 passed, 1 skipped** (Windows-only); +84 vs the PH-4 (904) state, no regression |
| PH-4 verifier | still 10/10 |
| RPH-3 integrated verifier | still 10/10 |
| Worker Execution Substrate verifier | still 18/18 |

## Governing-invariant coverage (`01I §5`, `01E §6`)

| Criterion | Where enforced | Test |
|---|---|---|
| `01I §5.4/§5.7` no protected-ref write by workstream | `GitManager.guard_protected_ref` | `test_protected_ref_and_force_push_guards`, `test_checkpoint_on_protected_branch_denied` |
| `01I §5.13` no auto force-push / history rewrite | `GitManager.guard_no_force_push` | `test_protected_ref_and_force_push_guards` |
| `01I §5.8` unexplained changes block start | `GitManager.require_clean_start` | `test_require_clean_start` |
| `01I §5.10` exact change tracking | `GitManager.changed_files` | `test_exact_change_tracking`, `test_rename_is_not_miscounted` |
| `01I §5.12` trailers match task record | `git.trailers.validate_against` | `test_validate_against_detects_mismatch` |
| ownership validation (owned-path checkpoints) | `GitManager.checkpoint` | `test_checkpoint_rejects_out_of_scope_changes` |
| `01E §6.13/§3.1` prohibited privileges denied | `sandbox.policy.evaluate_spec` | `test_prohibited_flags_are_denied` |
| `01E §6.14/§3.2` non-root default | `sandbox.policy` | `test_root_execution_denied_two_ways` |
| `01R` Dec C Windows-native excluded | `sandbox.policy` | `test_prohibited_flags_are_denied[windows_native]` |
| `01E §6.15` no writable host-project mount | `sandbox.policy` | `test_writable_host_project_mount_denied` |
| `01E §6.12` secrets revoked/removed before disposal | `FakeSecretBackend.revoke_task` | `test_revoke_task_clears_all_for_task` |
| `01E §6.11` secrets excluded from export | `FakeSecretBackend.scan_export` | `test_scan_export_blocks_leaked_secret` |
| `01E §6.8/§6.10` network default-deny + no inbound | `FakeNetworkBackend.evaluate` | `test_default_deny_without_contract`, `test_inbound_denied_unless_permitted` |
| `01E §6.9/§3.3` redirect containment | `FakeNetworkBackend.evaluate_redirect` | `test_redirect_containment` |
| `01E §6.7/§3.5` cache immutable/scoped/credential-free | `ContentAddressedCache` | `test_sandbox_scoping_is_isolated`, `test_credential_material_rejected` |
| `01E §6.16/§6.17/§3.7` staging-only exit + inspection | `staging.inspection`, `QuarantinedStaging` | `test_*` (secret/executable/scope/escape/bomb) |
| `01E §6.18` promotion needs complete gate + authorization | `QuarantinedStaging.promote` | `test_promote_requires_clean_and_authorization` |
| `01E §3.9` complete process-tree termination | `terminate_process_tree` | `test_process_tree_termination_is_complete` |

## Boundaries held

- No installation, no live WSL2/Docker/network/secrets; Git uses real *local temporary* repos only.
- `main` (`9bce1ca`) unchanged; PR #10 (`7b1922e`) draft/open/unmodified.
- No merge, no phase promotion, no Stage-2/3/4 cutover, no PH-6 code in this commit.
- RPH-3 spine, Worker Execution Substrate, and PH-4 routing unmodified; full repo regression green.

See the accompanying requirement-to-test matrix, failure-path matrix, and pending-live-gate register.
