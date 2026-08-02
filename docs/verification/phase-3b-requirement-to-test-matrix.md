# Phase 3B Requirement-to-Test Matrix

Current Linux-tested implementation commit: `475c528580fb580922526b0404101f9b080a0c9c`.
Historical native-Windows evidence at `48e0dd8` does not verify the current PR head.

| Requirement | Evidence | Status |
|---|---|---|
| Baseline repairs | serialization, support, loopback, Ruff, mypy regressions | PASS |
| Evidence/manifest persistence | verification model/store tests | PASS |
| Independent fail-closed verifier | tests pass, but review found host execution of untrusted tests without a process sandbox | FAIL |
| Approval-bound promotion/rollback | tests pass, but review found caller-supplied operator authorization and incomplete crash rollback | FAIL |
| Lifecycle and restart reconciliation | tests pass, but quick-start does not wire the Phase 3B services and interrupted promotion can remain applied | FAIL |
| API HTTP behavior | socket-capable rerun: 83 loopback tests | PASS |
| UI controls and reconnect | `Phase3BControls.test.tsx` | PASS |
| Native Windows junction escape denial | historical two-case run at `48e0dd8`; exact-head rerun and TOCTOU fix required | ENVIRONMENT-BLOCKED |
| Section 1 bootstrap and contract gate | network-enabled verifier; 325 tests; 96.86% branch coverage | PASS |
| Full Python collection/suite | 1733 collected; 1648 passed and 85 environment-classified skips on restricted Linux; loopback 83/83 separately | PASS |
| Repository section/roadmap scripts | Section 2 18/18; RPH3 10/10; PH-4 10/10 | PASS |
| Frontend type/lint/test/build | npm gates; 43 tests | PASS |
