# RPH3-T4 (CMP-AUDITW / CMP-AUDITV) — Verification Evidence Report

**Phase / component:** roadmap PH-3, Task **RPH3-T4** — tamper-evident audit chain (CMP-AUDITW writer +
CMP-AUDITV validator). **Branch:** `claude/roadmap-ph3-security-spine-planning` (this commit). **Date:**
2026-07-26. **Governing acceptance:** `01K-AC-19` (privileged actions → append-only hash-chained tamper-
evident audit), `01K-AC-20` (deletion/truncation/reorder/rewrite/invalid-anchor detectable), VR-RPH3-14, and
the audit-record cardinality of the cross-store protocol (XSC-RPH3 §2; `UNIQUE(op_key, record_kind)`).
**Verdict: PASS.** This is the RPH3-T4 gate only — **NOT** `PROM-RPH3`, NOT authorization of any other task.

## 1. Environment
| Field | Value |
|---|---|
| OS / runtime | Linux; Python 3.12.3; stdlib `sqlite3` (WAL) |
| Tooling pins | pytest 9.1.1, pytest-cov 7.1.0, mypy 2.3.0, ruff 0.15.22, hypothesis 6.161.0 (`uv.lock`) |
| Coverage | **99.34% branch** on `src/factory/audit` (obligation ≥95%) |
| Known limitation | native-Windows behavior of OS-specific paths re-verified at release (PH-8), as in PH-1/PH-2 |

## 2. Requirement → test → verdict → evidence (authorized RPH3-T4 sequence)
| # | Obligation | Test(s) | Verdict |
|---|---|---|---|
| 1 | Audit migration (append-only, hash-chain columns, `UNIQUE(op_key, record_kind)`, triggers) | `migrations/audit/0001_audit_chain.sql`; `unit/test_audit_writer.py::test_migration_*`; `security/…::test_readonly_connection_denies_mutation` | PASS |
| 2 | Audit models (`RecordKind`, `AuditRecord`, `AuditEvent`, `BreakClass`, `compute_hash`) | `src/factory/audit/models.py`; `unit/test_audit_writer.py::test_record_hash_binds_content_and_position` | PASS |
| 3 | Append-only writer (sole appender; sequence=prev+1; genesis anchor; head/export) | `unit/test_audit_writer.py` (7+) | PASS |
| 4 | Chain validator (verify_chain / verify_export / classify_break) | `unit/test_audit_validator.py`; `failure_paths/test_partial_write_and_corruption.py` | PASS |
| 5 | `UNIQUE(op_key, record_kind)` enforcement (≤1 INTENT + ≤1 COMPLETION; duplicate rejected) | `security/…::test_duplicate_completion_rejected`, `::test_second_intent_rejected`, `::test_intent_completion_pair_allowed` | PASS |
| 6 | Class-3 completion-after-intent | `security/…::test_class3_completion_before_intent_rejected`; `unit/…::test_class3_intent_then_completion_two_records` | PASS |
| 7 | Concurrency & duplicate handling (retry past a taken sequence; no fork/gap; exhaustion fails closed) | `failure_paths/…::test_sequence_collision_retries_no_fork`; `failure_paths/test_writer_injection.py::test_append_retry_exhaustion_raises_contended` | PASS |
| 8 | Partial-write fault injection (failed append rolls back; mid-apply migration fails closed) | `failure_paths/…::test_failed_append_leaves_chain_unchanged`, `::test_append_to_unmigrated_store_fails_closed`; `test_writer_injection.py::test_migration_apply_failure_is_fail_closed` | PASS |
| 9 | Chain-corruption & tampering (deletion / truncation / reorder / rewrite / bad-anchor; incl. consistent re-forge) | `failure_paths/…::test_detects_{rewrite,deletion,truncation_with_expected_head,bad_anchor,reorder_via_export,consistent_reforge_of_middle_record,consistent_reforge_of_head_against_expected}` | PASS |
| 10 | T4 evidence report | this document + `scripts/verify_roadmap_ph3_t4.py` (9/9) | PASS |

## 3. Test-suite summary
| Category | Count | Notes |
|---|---|---|
| unit | 16 | writer + validator |
| security | 12 | append-only, cardinality, Class-3 ordering, forge-resistance |
| failure-path | 14 | partial-write, concurrency, tamper detection, injection |
| **audit total** | **42 passed** | 0 failed |
| **full repo (regression)** | **508 passed, 1 skipped** | 1 Windows-only skip; no regression vs 466 pre-T4 |

## 4. Static quality gates
`ruff check src/factory/audit tests/audit scripts/verify_roadmap_ph3_t4.py` → clean · `mypy --strict
src/factory/audit tests/audit` → clean (11 files) · branch coverage `src/factory/audit` = **99.34%** (≥95%).

## 5. Defects & regressions
Open critical/high: **none.** REGR seeded: none. The migration SHA is pinned
(`935e535a8db35693f94c6a30bcd9d312960eeeb24babea62e933ba7dfa06c433`) and integrity-fails-closed on tamper.

## 6. Reproduction
```
uv run python3.12 scripts/verify_roadmap_ph3_t4.py            # 9/9 PASS
uv run python3.12 -m pytest tests/audit -q --cov=src/factory/audit --cov-branch   # 42 passed, 99%
uv run python3.12 -m pytest -q                                # 508 passed, 1 skipped
```

## 7. Promotion readiness
RPH3-T4 gate criteria: [x] migration + schema (append-only, `UNIQUE(op_key, record_kind)`) · [x] models ·
[x] append-only writer · [x] chain validator · [x] cardinality enforcement · [x] Class-3 ordering ·
[x] concurrency/duplicate · [x] partial-write injection · [x] chain-corruption/tamper tests · [x] ≥95% coverage
· [x] ruff + mypy --strict clean · [x] zero critical/high · [ ] operator acceptance of RPH3-T4 (pending).

**RPH3-T4 is the audit foundation only.** It is not `PROM-RPH3` and does not authorize CMP-APPROVAL /
CMP-PERM / CMP-TOOLREG / CMP-FILEOP / CMP-DIAG / CMP-WATCH work (Lane A remains paused).
