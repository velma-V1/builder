# Phase 3B Requirement-to-Test Matrix

Implementation commit: `c25bb4c`.

| Requirement | Evidence | Status |
|---|---|---|
| Baseline repairs | serialization, support, loopback, Ruff, mypy regressions | PASS |
| Evidence/manifest persistence | verification model/store tests | PASS |
| Independent fail-closed verifier | verification unit/integration/tamper/replay tests | PASS |
| Approval-bound promotion/rollback | promotion service tests | PASS |
| Lifecycle and restart reconciliation | worker, replay, lifecycle tests | PASS |
| API HTTP behavior | socket-capable rerun: 83 loopback tests | PASS |
| UI controls and reconnect | `Phase3BControls.test.tsx` | PASS |
| Full Python collection/suite | 1729 collected; 1644 passed, 85 classified skips | PASS |
| Repository section/roadmap scripts | Section 2 18/18; RPH3 10/10; PH-4 10/10 | PASS |
| Frontend type/lint/test/build | npm gates; 43 tests | PASS |
