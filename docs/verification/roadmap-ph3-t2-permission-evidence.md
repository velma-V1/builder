# RPH3-T2 (CMP-PERM) — Verification Evidence Report

**Phase / component:** roadmap PH-3, Task **RPH3-T2** — Permission Enforcement (CMP-PERM). **Branch:**
`claude/roadmap-ph3-security-spine-planning` (this commit). **Date:** 2026-07-30. **Governing:**
`permission-spec` (interfaces + required tests), `01K` §2.4-8/§2.26-27 (AC-02/03/04/10), `01R` Dec A
(autonomy envelope) / Dec B (all deletion approval-gated), `XSC-RPH3` Class-1 (§3/§5/§6), `DEP-RPH3`
§2/§3/§4A (store boundary, ordered per-domain migration, sole-writer partition). **Verdict: PASS.** This is
the RPH3-T2 gate only — **NOT** `PROM-RPH3`, NOT authorization of any other task. Builds on the accepted
RPH3-T4 audit foundation and the RPH3-T3 approval domain (shared security-spine store); both unmodified.

## 1. Environment
| Field | Value |
|---|---|
| OS / runtime | Linux; Python 3.12.3; stdlib `sqlite3` (WAL) |
| Tooling pins | pytest 9.1.1, pytest-cov 7.1.0, mypy 2.3.0, ruff 0.15.22 (`uv.lock`) |
| Coverage | **100.00% branch** on `src/factory/permission` (obligation ≥95%) |
| Migration SHA (pinned) | `0002_permission.sql` = `a65d227d9683eb060c834ae8b3cb65f33186ba37420b4065eec8623f8ded88cb` |
| Reused (not reinvented) | `factory.contracts.validation.paths.PathAuthority` (path canonicalize + contain, TOCTOU) |

## 2. Requirement → test → verdict (permission-spec required tests + XSC-RPH3 + boundaries)
| # | Obligation | Test(s) | Verdict |
|---|---|---|---|
| 1 | Least-privilege allow (in-envelope, path-contained) → scoped/expiring/revocable grant | `unit/test_permission_engine.py::test_allow_in_envelope_path_contained`, `::test_issue_grant_is_active_committed_and_bound` | PASS |
| 2 | Deny-by-default — a class outside the task permit set is denied (01K-AC-02) | `security/…::test_deny_by_default_class_not_permitted`, `::test_grant_cannot_exceed_task_mismatch` | PASS |
| 3 | Decision B — **every** deletion is approval-gated; no auto-delete path exists | `security/…::test_every_delete_is_approval_gated_no_auto_path`; `unit/test_autonomy.py::test_envelope_classify` (DELETE at every level → requires_card) | PASS |
| 4 | Decision A — autonomy envelope gates auto vs requires-card | `unit/test_permission_engine.py::test_out_of_envelope_is_requires_approval_decision_a`; `unit/test_autonomy.py` (full matrix + unknown-level fail-closed) | PASS |
| 5 | Path safety #10 — traversal / absolute / drive / ADS / reserved-name / null-byte / trailing / symlink-escape blocked | `security/…::test_path_escapes_are_denied[7 cases]`, `::test_symlink_escape_is_denied`; reuses `tests/contracts/security/test_path_attacks.py` | PASS |
| 6 | Only the canonical path is stored (never a raw path) | `security/…::test_grant_only_stores_canonical_path_never_raw` | PASS |
| 7 | TOCTOU — pre-use revalidation rejects a stale grant after a state change | `unit/…::test_revalidate_after_revoke_is_false`; `security/…::test_toctou_stale_grant_rejected_after_state_change`; `unit/test_permission_engine_edges.py::test_revalidate_{missing_grant,fingerprint_mismatch}_is_false` | PASS |
| 8 | Grant lifecycle — issue / revalidate / revoke / expire; guards (not-found/inflight/terminal) | `unit/test_permission_engine.py`, `unit/test_permission_engine_edges.py` | PASS |
| 9 | 01K-AC-04 — no permanent/unrestricted authority (grants are ACTIVE→REVOKED/EXPIRED, expiring, revocable) | `unit/…::test_expire_sweeps_and_revalidate_false`, `::test_revalidate_after_revoke_is_false` | PASS |
| 10 | XSC-RPH3 Class-1 — durable intent → PENDING mutation → completion audit → COMMITTED; one grant + one COMPLETION joined by `op_key` (INV-1); `audit_seq` set | `integration/test_permission_cross_store.py::test_class1_happy_path_one_grant_one_completion_joined_by_op_key` | PASS |
| 11 | Crash windows — before-audit → roll back (ABORTED); after-audit → roll forward (COMMITTED); transition restores prior | `failure_paths/test_permission_crash_reconciliation.py::test_crash_before_audit_rolls_issue_back`, `::test_crash_after_audit_rolls_issue_forward`, `::test_crash_before_audit_rolls_transition_back` | PASS |
| 12 | Reconciliation — invalid chain fails closed; idempotent | `failure_paths/…::test_reconcile_refuses_invalid_audit_chain`, `::test_reconcile_is_idempotent` | PASS |
| 13 | Fail-closed on audit/storage failure | `failure_paths/…::test_issue_fails_closed_when_audit_unavailable`, `::test_revoke_fails_closed_and_restores_prior`; `test_permission_writer_faults.py` (stage/commit/rollback) | PASS |
| 14 | Migration integrity — SHA pin, malformed/missing/partial fail closed; idempotent; ordered per-domain | `failure_paths/…::test_migration_{missing,malformed_filename,integrity_mismatch,apply_failure}_*`; `unit/test_permission_store.py::test_migration_is_idempotent` | PASS |
| 15 | Sole-writer + read-only + cross-domain isolation (§4A; approval/permission table isolation) | `security/…::test_writer_denied_writes_outside_permission_tables`, `::test_permission_writer_cannot_touch_approval_tables`, `::test_reader_connection_denies_every_write`, `::test_writer_is_not_publicly_exported`; `unit/test_permission_store.py::test_writer_authorizer_*` | PASS |

## 3. Test-suite summary
| Category | Count | Notes |
|---|---|---|
| unit | 33 | decide matrix, grant lifecycle, autonomy envelope, store/migration/authorizer, guard branches |
| security | 18 | least-privilege, path escapes (#10), Decision B, TOCTOU, isolation |
| failure-path | 15 | crash windows, reconciliation, fail-closed, migration faults, writer faults |
| integration | 3 | Class-1 cross-store happy path, full lifecycle, op_key uniqueness |
| **permission total** | **69 passed** | 0 failed |
| **full repo (regression)** | **633 passed, 1 skipped** | 1 Windows-only skip; +69 vs 564 at T3, no regression |

## 4. Static quality gates
`ruff check src/factory/permission tests/permission scripts/verify_roadmap_ph3_t2.py` → clean · `mypy
--strict src/factory/permission tests/permission` → clean (16 files) · branch coverage
`src/factory/permission` = **100.00%** (≥95%). SQL is fully-literal / bound-parameter only (S608-clean).

## 5. Shared-store & migration model
The permission domain is the **second ordered per-domain migration** (`0002_permission.sql`) in the single
security-spine SQLite store (operator-adopted model; `DEP-RPH3 §3` and `SCHEMA-REGISTRY.md` amended). Each
domain runner owns only its own SHA-pinned migration and **skips** other domains' valid-versioned files;
`0002` creates `schema_migrations IF NOT EXISTS` so it composes with `0001` in canonical order. Cross-domain
write isolation is structural: the permission writer's SQLite authorizer denies writes to `approval_*` (and
any non-permission table); the approval `0001` migration is unmodified.

## 6. Cross-store & durability caveats (no over-claim)
- **No cross-database atomicity claimed** — durability across the security-spine and audit stores is the
  XSC-RPH3 Class-1 protocol (durable completion audit + reconciliation), not a single cross-file transaction.
- **No absolute tamper-prevention** claimed for the audit store (that is T4's tamper-*evidence*).
- **Power-loss durability** rests on WAL + reconciliation; not independently proven beyond the crash-window
  fault-injection tests.

## 7. Reproduction
```
uv run python3.12 scripts/verify_roadmap_ph3_t2.py                                       # 10/10 PASS
uv run python3.12 -m pytest tests/permission -q --cov=src/factory/permission --cov-branch # 69 passed, 100%
uv run python3.12 -m pytest -q                                                            # 633 passed, 1 skipped
```

## 8. Promotion readiness
RPH3-T2 gate criteria: [x] migration + schema (permission domain, SHA-pinned, ordered) · [x] models +
autonomy envelope · [x] private sole-writer + read-only reader (not exported) · [x] least-privilege decide
(deny-by-default) · [x] Decision A/B enforcement · [x] path safety #10 (reused PathAuthority) · [x] TOCTOU
revalidation · [x] XSC-RPH3 Class-1 + crash reconciliation · [x] cross-domain isolation · [x] ≥95% coverage
(100%) · [x] ruff + mypy --strict clean · [x] full regression green · [ ] operator acceptance (pending).

**RPH3-T2 is the permission domain only.** It is not `PROM-RPH3` and does not authorize CMP-TOOLREG /
CMP-TOOLGW / CMP-FILEOP / CMP-DIAG / CMP-WATCH work (Lane A remains paused).
