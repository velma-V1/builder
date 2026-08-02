# Phase 3B Requirement-to-Test Matrix

Implementation commit: `017b2f4`.

| Requirement | Evidence | Status |
|---|---|---|
| Baseline repairs | serialization, support, loopback, Ruff, mypy regressions | PASS |
| Evidence/manifest persistence | verification model/store tests | PASS |
| Independent fail-closed verifier | verification unit/integration/tamper/replay tests | PASS |
| Approval-bound promotion/rollback | promotion service tests | PASS |
| Lifecycle and restart reconciliation | worker, replay, lifecycle tests | PASS |
| API HTTP behavior | orchestrator API HTTP tests | ENVIRONMENT-BLOCKED |
| UI controls and reconnect | `Phase3BControls.test.tsx` | PASS |
| Full Python collection/suite | 1710 collected; 1625 passed, 85 skips | PASS |
| Repository section/roadmap scripts | three legacy failures | FAIL |
| Frontend type/lint/test/build | npm gates; 43 tests | PASS |
