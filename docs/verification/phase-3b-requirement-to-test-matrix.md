# Phase 3B Requirement-to-Test Matrix

Verified implementation commit: `48e0dd8`.

| Requirement | Evidence | Status |
|---|---|---|
| Baseline repairs | serialization, support, loopback, Ruff, mypy regressions | PASS |
| Evidence/manifest persistence | verification model/store tests | PASS |
| Independent fail-closed verifier | verification unit/integration/tamper/replay tests | PASS |
| Approval-bound promotion/rollback | promotion service tests | PASS |
| Lifecycle and restart reconciliation | worker, replay, lifecycle tests | PASS |
| API HTTP behavior | socket-capable rerun: 83 loopback tests | PASS |
| UI controls and reconnect | `Phase3BControls.test.tsx` | PASS |
| Native Windows junction escape denial | two real `mklink /J` cases | PASS |
| Section 1 bootstrap and contract gate | network-enabled verifier; 325 tests; 96.86% branch coverage | PASS |
| Full Python collection/suite | 1730 collected; 1730 passed | PASS |
| Repository section/roadmap scripts | Section 2 18/18; RPH3 10/10; PH-4 10/10 | PASS |
| Frontend type/lint/test/build | npm gates; 43 tests | PASS |
