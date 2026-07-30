# Roadmap PH-3 Windows Verification Matrix

**Host:** Windows. **Date:** 2026-07-30. All results below are from completed local runs.

| CPython | Integrated RPH3 tests | T1 | T2 | T3 | T4 | T5 | Cross | Integrated | Full repo | Ruff | mypy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 3.12.13 | 309 pass | 8/8 | 10/10 | 9/9 | 9/9 | 10/10 | 7/7 | 10/10 | 811 pass, 1 skip | PASS | PASS |
| 3.13.14 | 309 pass | 8/8 | 10/10 | 9/9 | 9/9 | 10/10 | 7/7 | 10/10 | 811 pass, 1 skip | PASS | PASS |
| 3.14.6 | 309 pass | 8/8 | 10/10 | 9/9 | 9/9 | 10/10 | 7/7 | 10/10 | 811 pass, 1 skip | PASS | PASS |

The integrated verifier promotes `ResourceWarning` and Pytest unraisable-warning wrappers to errors.
The full-repository runs used the same error policy. No warning occurred; the one skip is explicitly
classified in the warning/skip register.
