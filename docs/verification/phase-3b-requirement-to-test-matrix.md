# Phase 3B Requirement-to-Test Matrix

Linux and native-Windows tested implementation commit:
`8c05e6c8ed13d8120dec970906a502a14540e992`. Independent review of the following evidence-only
PR head remains pending.

| Requirement | Evidence | Status |
|---|---|---|
| Baseline repairs | serialization, support, loopback, Ruff, mypy regressions | PASS |
| Evidence/manifest persistence | verification model/store tests | PASS |
| Independent fail-closed verifier | isolated-runner regressions and focused verifier suite | PASS — independent re-review pending |
| Approval-bound promotion/rollback | authenticated runtime-session boundary and durable rollback regressions | PASS — independent re-review pending |
| Lifecycle and restart reconciliation | quick-start wiring and interrupted-promotion reconciliation regressions | PASS — independent re-review pending |
| API HTTP behavior | socket-capable rerun: 85 loopback tests | PASS |
| UI controls and reconnect | `Phase3BControls.test.tsx` | PASS |
| Native Windows junction escape denial | exact-commit native-Windows run | PASS — 2 passed |
| Section 1 bootstrap and contract gate | 324 passed, 1 native-Windows skip; 96.86% branch coverage | PASS |
| Full Python collection/suite | 1747 collected; 1660 passed and 87 classified skips on restricted Linux; loopback 85/85 separately | PASS |
| Repository section/roadmap scripts | Section 2 18/18; RPH3 10/10; PH-4 10/10 | PASS |
| Frontend type/lint/test/build | npm gates; 45 tests | PASS |
