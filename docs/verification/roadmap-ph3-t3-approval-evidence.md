# RPH3-T3 (CMP-APPROVAL) — Verification Evidence Report

**Phase / component:** roadmap PH-3, Task **RPH3-T3** — Approval Engine (CMP-APPROVAL). **Branch:**
`claude/roadmap-ph3-security-spine-planning` (this commit). **Date:** 2026-07-30. **Governing:**
`approval-spec` (interfaces + required tests), `01K` §2.6-11 (approvals, non-reuse `01K-AC-03`, separate
confirmation §2.10-11), `01L §3.2` (complete card scope), `XSC-RPH3` Class-1 (§3/§5/§6/§10), `DEP-RPH3`
§2/§3/§4A (store boundary, ordered per-domain migration, sole-writer partition). **Verdict: PASS.** This is
the RPH3-T3 gate only — **NOT** `PROM-RPH3`, NOT authorization of any other task. Builds on the accepted
RPH3-T4 audit foundation (unmodified).

## 1. Environment
| Field | Value |
|---|---|
| OS / runtime | Linux; Python 3.12.3; stdlib `sqlite3` (WAL) |
| Tooling pins | pytest 9.1.1, pytest-cov 7.1.0, mypy 2.3.0, ruff 0.15.22 (`uv.lock`) |
| Coverage | **100.00% branch** on `src/factory/approval` (obligation ≥95%) |
| Migration SHA (pinned) | `0001_security_spine.sql` = `099ae959d6f06c6b944925af151d8fa8dd2b65fdffd63660cf2a4355b7878a51` |
| Known limitation | native-Windows behavior re-verified at release (PH-8), as in PH-1/PH-2 |

## 2. Requirement → test → verdict (approval-spec required tests + XSC-RPH3 + boundaries)
| # | Obligation | Test(s) | Verdict |
|---|---|---|---|
| 1 | Card completeness — full 01L §3.2 scope + autonomy + consequences | `unit/test_engine.py::test_enqueue_returns_complete_card` | PASS |
| 2 | Scope binding — approval bound to (task, action, path, scope) rejects any other action | `security/…::test_scope_binding_rejects_other_action` | PASS |
| 3 | No reuse (01K-AC-03) — consumed/expired/revoked cannot be reused | `security/…::test_{consumed,revoked,expired}_record_cannot_be_reused`; `integration/…::test_replayed_consumption_is_rejected` | PASS |
| 4 | Expiry — write/execution approvals auto-expire, then unusable | `unit/…::test_expiry_auto_and_swept`, `::test_is_valid_predicate` | PASS |
| 5 | Repetition — bounded batch consumed at most N, then invalid | `unit/…::test_repetition_limit_consumes_at_most_n_then_invalid` | PASS |
| 6 | Security violation — denied + audited, never queued | `security/…::test_security_violation_denied_audited_never_queued`; `unit/test_engine_edges.py::test_security_violation_fails_closed_when_audit_unavailable` | PASS |
| 7 | Separate confirmation (01K §2.10-11) for destructive/external | `security/…::test_destructive_grant_requires_separate_confirmation` | PASS |
| 8 | Legal transitions / replay guard — decide/consume idempotent, no double-decision | `unit/test_engine_edges.py::test_replayed_decision_rejected`; `integration/…::test_replayed_consumption_is_rejected` | PASS |
| 9 | XSC-RPH3 Class-1 — durable intent → PENDING mutation → completion audit → COMMITTED; one record + one COMPLETION joined by `op_key` (INV-1); `audit_seq` set | `integration/test_cross_store.py::test_class1_happy_path_one_record_one_completion_joined_by_op_key` | PASS |
| 10 | Crash windows — before-audit → roll back (ABORTED); after-audit → roll forward (COMMITTED); transition restores prior | `failure_paths/test_crash_reconciliation.py::test_crash_before_audit_rolls_enqueue_back`, `::test_crash_after_audit_rolls_enqueue_forward`, `::test_crash_before_audit_rolls_transition_back_to_prior_state` | PASS |
| 11 | Startup reconciliation — invalid chain fails closed; idempotent | `failure_paths/…::test_reconcile_refuses_invalid_audit_chain`, `::test_reconcile_is_idempotent` | PASS |
| 12 | Fail-closed on storage/audit failure | `failure_paths/…::test_enqueue_fails_closed_when_audit_unavailable`, `::test_transition_fails_closed_and_restores_prior`; `test_writer_faults.py` (stage/commit/rollback) | PASS |
| 13 | Migration integrity — SHA pin, malformed/missing/partial fail closed; idempotent | `failure_paths/…::test_migration_{missing,malformed_filename,integrity_mismatch,apply_failure}_*`; `unit/test_store.py::test_migration_is_idempotent` | PASS |
| 14 | Sole-writer + read-only consumers (§4A) — writer denied outside approval tables; reader read-only; writer not exported | `security/…::test_writer_denied_writes_outside_approval_tables`, `::test_reader_connection_denies_every_write`, `::test_writer_is_not_publicly_exported`; `unit/test_store.py::test_writer_authorizer_*` | PASS |

## 3. Test-suite summary
| Category | Count | Notes |
|---|---|---|
| unit | 27 | engine lifecycle + guard branches + store/migration/authorizer |
| security | 9 | scope binding, non-reuse, security-violation, destructive-confirm, isolation |
| failure-path | 16 | crash windows, reconciliation, fail-closed, migration faults, writer faults |
| integration | 4 | Class-1 cross-store happy path, full lifecycle, replay, op_key uniqueness |
| **approval total** | **56 passed** | 0 failed |
| **full repo (regression)** | **564 passed, 1 skipped** | 1 Windows-only skip; +56 vs 508 at T4, no regression |

## 4. Static quality gates
`ruff check src/factory/approval tests/approval scripts/verify_roadmap_ph3_t3.py` → clean · `mypy --strict
src/factory/approval tests/approval` → clean (14 files) · branch coverage `src/factory/approval` =
**100.00%** (≥95%). SQL is fully-literal / bound-parameter only (no runtime interpolation; S608-clean).

## 5. Cross-store & durability caveats (no over-claim)
- **No cross-database atomicity claimed.** The security-spine and audit stores are separate SQLite files;
  durability across them is provided by the XSC-RPH3 Class-1 protocol (durable completion audit as the commit
  point + startup reconciliation), **not** by a single cross-file transaction.
- **No absolute tamper-prevention claimed** for the audit store (that is T4's tamper-*evidence*).
- **Power-loss durability** rests on SQLite WAL + the reconciliation protocol; it is not independently proven
  here beyond the crash-window fault-injection tests.

## 6. Reproduction
```
uv run python3.12 scripts/verify_roadmap_ph3_t3.py                                   # 9/9 PASS
uv run python3.12 -m pytest tests/approval -q --cov=src/factory/approval --cov-branch # 56 passed, 100%
uv run python3.12 -m pytest -q                                                        # 564 passed, 1 skipped
```

## 7. Migration-contract resolution
The earlier open question (`DEP-RPH3 §3` "single all-tables `0001`" vs. an approval-only `0001`) is
**resolved**: the operator adopted the **ordered per-domain migration model** and `DEP-RPH3 §3/§3.1` was
amended (operator-authorized, 2026-07-30) to describe it, preserving the cumulative end-state inventory. See
`docs/planning/RPH3-T3-IMPLEMENTATION-NOTE.md`. No frozen invariant is weakened.

## 8. Promotion readiness
RPH3-T3 gate criteria: [x] migration + schema (approval domain, SHA-pinned) · [x] models (+ card completeness)
· [x] private sole-writer + read-only reader (writer not exported) · [x] engine full lifecycle · [x] XSC-RPH3
Class-1 + crash reconciliation · [x] scope binding / non-reuse / expiry / repetition · [x] security-violation
denied+audited · [x] separate confirmation · [x] ≥95% coverage (100%) · [x] ruff + mypy --strict clean ·
[x] full regression green · [ ] operator acceptance of RPH3-T3 (pending).

**RPH3-T3 is the approval domain only.** It is not `PROM-RPH3` and does not authorize CMP-PERM / CMP-TOOLREG /
CMP-TOOLGW / CMP-FILEOP / CMP-DIAG / CMP-WATCH work (Lane A remains paused).
