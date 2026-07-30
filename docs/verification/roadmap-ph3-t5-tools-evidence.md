# RPH3-T5 (Tools enforcement) — Verification Evidence Report

> Historical Linux/Python 3.12 evidence. The Windows/Python 3.12-3.14 correction is recorded in
> `docs/verification/roadmap-ph3-windows-python314-correction-evidence.md`.

**Phase / component:** roadmap PH-3, Task **RPH3-T5** — CMP-TOOLREG (registry) + CMP-TOOLGW (gateway) +
CMP-FILEOP (safe file-op) + CMP-DIAG (Safe Mode, PH-3 scope). **Branch:**
`claude/roadmap-ph3-security-spine-planning` (this commit). **Date:** 2026-07-30. **Governing:**
`tool-registry-spec`, `tool-gateway-spec`, `file-op-service-spec`, `safe-mode-spec`; `01K` §2.1-3/§2.18-25/
§2.26-27/§2.32/§3.1; `01R` Dec B; `XSC-RPH3` (Class-1 registry ops, Class-3 file delete); `DEP-RPH3`
§2/§3/§4A. **Verdict: PASS.** RPH3-T5 gate only — **NOT** `PROM-RPH3`. Builds on accepted RPH3-T4/T3/T2
(unmodified). **RPH3 performs no direct host execution;** actual OS resource/process-tree enforcement is
PH-5 (EG-PH5-04/05/06) — the gateway defines the request contracts and fails closed without a sandbox.

## 1. Environment
| Field | Value |
|---|---|
| OS / runtime | Linux; Python 3.12.3; stdlib `sqlite3` (WAL) |
| Coverage | tools **98.7%**, fileops **97.6%**, safemode **98%** branch (each ≥95%) |
| Migration SHA (pinned) | `0003_tools.sql` = `0050e74f80932fb58ea15d1f60f95661c7589d57dd623aad7691e26ea73a69b5` |
| Reused | `factory.contracts.validation.paths.PathAuthority` (fileop path safety + zip-slip) |

## 2. Requirement → test → verdict
| # | Obligation | Test(s) | Verdict |
|---|---|---|---|
| 1 | Default-deny — an unregistered tool is uncallable (01K-AC-01) | `tools/unit/test_tool_registry.py::test_unregistered_is_default_deny`; `tools/security/test_tool_security.py::test_no_bypass_unregistered_cannot_execute` | PASS |
| 2 | Complete declaration required; incomplete rejected | `tools/unit/…::test_incomplete_declaration_rejected` | PASS |
| 3 | Provenance/integrity for downloaded components (01K-AC-09) | `tools/unit/…::test_incomplete_provenance_rejected_for_download` | PASS |
| 4 | Version pinning (distinct versions; unpinned uncallable) | `tools/unit/…::test_version_pinning_distinct_versions` | PASS |
| 5 | Quarantine (repeated equivalent failure; no use until released, 01K-AC-18) | `tools/unit/…::test_repeated_failure_quarantines`, `::test_quarantine_makes_uncallable_and_release_restores`; `tools/security/…::test_repeated_output_failure_quarantines_tool` | PASS |
| 6 | No-bypass gateway — only path; unregistered/quarantined denied | `tools/unit/test_tool_gateway.py::test_unregistered_denied`; `tools/security/…::test_quarantined_tool_denied_at_gateway` | PASS |
| 7 | TOCTOU — permission revalidated at call time | `tools/unit/test_tool_gateway.py::test_revoked_grant_denied_toctou` | PASS |
| 8 | Output validation — malformed/oversized/out-of-scope fails closed (01K-DEC-25) | `tools/unit/test_tool_gateway.py::test_output_validation_rejects_{oversized,missing_keys}`; `tools/unit/test_tool_edges.py::test_validate_output_rejects_*` | PASS |
| 9 | Resource-limit REQUEST CONTRACT; limit increase → permission change | `tools/unit/test_tool_gateway.py::test_limit_increase_routes_to_approval`, `::test_enforce_limits_within_and_over` | PASS |
| 10 | Termination REQUEST CONTRACT; fail-closed w/o sandbox; no direct host exec | `tools/unit/test_tool_gateway.py::test_no_executor_fails_closed`, `::test_terminate_tree_fails_closed_without_executor` | PASS |
| 11 | Path safety #10 — traversal/absolute/ADS/reserved/null/symlink/zip-slip | `fileops/test_fileops.py::test_path_escapes_denied`, `::test_archive_zip_slip_blocked` (+ reused `PathAuthority` suite) | PASS |
| 12 | Decision B — no delete path without a valid consumed approval; Class-3 audited | `fileops/test_fileops.py::test_delete_requires_valid_approval_decision_b`, `::test_delete_with_valid_approval_is_class3_audited` | PASS |
| 13 | Archive limits #11 — entry/depth/decompressed-size caps prevent bombs | `fileops/test_fileops.py::test_archive_{entry_count,decompressed_size}_capped` | PASS |
| 14 | Write containment + atomicity | `fileops/test_fileops.py::test_write_atomic_and_read`, `::test_write_to_read_only_path_denied`; `fileops/test_fileops_edges.py::test_write_over_directory_fails` | PASS |
| 15 | Safe Mode — no autonomous writes (01K-AC-22 / 01M-AC-20) | `safemode/test_safemode.py::test_repair_without_valid_approval_denied_no_autonomous_write` | PASS |
| 16 | Safe Mode — unapproved repair denied; inspection/export read-only; out-of-scope refused; no control weakened | `safemode/test_safemode.py::test_{inspect_is_read_only,export_evidence_is_read_only,repair_without_valid_permission_denied,out_of_scope_capability_refused,approved_repair_applies_with_valid_approval_and_permission}` | PASS |
| 17 | XSC-RPH3 Class-1 registry ops joined by `op_key`; crash reconciliation; fail-closed | `tools/integration/test_tool_cross_store.py`; `tools/failure_paths/test_tool_faults.py` | PASS |
| 18 | Sole-writer partition + read-only + cross-domain isolation (§4A) | `tools/security/test_tool_security.py::test_writer_denied_writes_outside_tool_tables`, `::test_reader_connection_denies_every_write`, `::test_writer_is_not_publicly_exported`; `tools/unit/test_tool_store.py::test_writer_authorizer_matrix` | PASS |

## 3. Test-suite summary
| Category | Count |
|---|---|
| tools (unit 38 / security 6 / failure-path 11 / integration 2) | **57** |
| fileops | **21** |
| safemode | **10** |
| **RPH3-T5 total** | **88 passed** |
| **full repo (regression)** | **721 passed, 1 skipped** (Windows-only; +88 vs 633 at T2, no regression) |

## 4. Static quality gates
`ruff check` over all four component packages + tests + `scripts/verify_roadmap_ph3_t5.py` → clean ·
`mypy --strict` per package (tools/fileops/safemode + tests) → clean · branch coverage ≥95% each. SQL is
fully-literal / bound-parameter only. `0003_tools.sql` uses `CREATE TABLE IF NOT EXISTS schema_migrations`
so it composes with `0001`/`0002` in canonical order; the tool runner skips other domains' migrations.

## 5. RPH3 boundary (no over-claim)
- **No direct host execution.** CMP-TOOLGW never spawns a process; it delegates to an injected PH-5
  `SandboxExecutor` and **fails closed** when none exists (`NO_SANDBOX_EXECUTOR`). Actual OS resource caps
  and complete process-tree termination are **PH-5** (EG-PH5-04/05/06); T5 proves the request contracts +
  fail-closed + no-bypass only.
- **No cross-database atomicity / absolute tamper-prevention / power-loss durability** claimed beyond the
  XSC-RPH3 protocol + WAL + the crash-window fault-injection tests.
- CMP-FILEOP delete is a real irreversible effect ⇒ modeled as XSC-RPH3 **Class-3** (durable INTENT before,
  COMPLETION after); an unproven outcome is not reported successful.

## 6. Reproduction
```
uv run python3.12 scripts/verify_roadmap_ph3_t5.py                                  # 10/10 PASS
uv run python3.12 -m pytest tests/tools tests/fileops tests/safemode -q             # 88 passed
uv run python3.12 -m pytest -q                                                      # 721 passed, 1 skipped
```

## 7. Promotion readiness
RPH3-T5 gate: [x] tool migration (0003, SHA-pinned, ordered) · [x] registry (default-deny + declaration +
provenance + quarantine) · [x] gateway (no-bypass + TOCTOU + limits + output validation + no-direct-exec) ·
[x] file-op (path safety + Decision-B Class-3 delete + archive caps + atomic write) · [x] Safe Mode (no
autonomous write, approval+perm-gated repair, read-only inspect/export) · [x] Class-1 reconciliation ·
[x] cross-domain isolation · [x] ≥95% coverage · [x] ruff + mypy --strict clean · [x] full regression green
· [ ] operator acceptance (pending).

**RPH3-T5 is the tools-enforcement gate only.** It is not `PROM-RPH3`; Lane A / Watchdog remain paused, and
no PH-5 enforcement gate (EG-PH5-*) is claimed.
