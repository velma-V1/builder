# Roadmap PH-3 Complete Requirement-to-Test Matrix

| VR | Requirement | Primary test/verifier evidence | Verdict |
|---|---|---|---|
| VR-RPH3-01 | Independent read-only Watchdog | T1 observer/isolation checks; watchdog security tests | PASS |
| VR-RPH3-02 | Monotonic timing, thresholds, hysteresis | T1 timing check; `test_watchdog_unit.py` | PASS |
| VR-RPH3-03 | Critical triggers and bounded recovery | T1 recovery check; watchdog failure-path tests | PASS |
| VR-RPH3-04 | Narrow validated audited intervention | T1 WIR check; intervention security/integration tests | PASS |
| VR-RPH3-05 | No blind resume; Watchdog-loss recovery | watchdog reconciliation/failure-path tests | PASS |
| VR-RPH3-06 | Restricted Safe Mode, no autonomous write | T5 verifier; Safe Mode and cross-lane tests | PASS |
| VR-RPH3-07 | Watchdog loss pauses/blocks high-risk work | watchdog process/failure-path tests | PASS |
| VR-RPH3-08 | Default-deny registry and gateway | T5 verifier; tool security tests | PASS |
| VR-RPH3-09 | Least privilege and TOCTOU | T2 verifier; permission security tests | PASS |
| VR-RPH3-10 | Bound/expiring/revocable approval | T3 verifier; approval security tests | PASS |
| VR-RPH3-11 | Path canonicalization and archive limits | T2/T5 verifiers; fileop/path tests | PASS |
| VR-RPH3-12 | No unapproved telemetry emission | static no-bypass checks; no telemetry path exists | PASS |
| VR-RPH3-13 | Tool provenance and quarantine | T5 registry/failure-path tests | PASS |
| VR-RPH3-14 | Append-only hash chain and break detection | T4 verifier; audit security/failure tests | PASS |
| VR-RPH3-15 | RPH3 emergency containment contract | T1 WIR integration/failure tests | PASS |
| VR-RPH3-16 | Untrusted instructions cannot expand authority | T2 security and contracts injection tests | PASS |
| VR-RPH3-17 | Decision A autonomy envelope | T2 autonomy tests; T3 card tests | PASS |
| VR-RPH3-18 | Decision B deletion approval | T2/T3/T5 and full cross-lane flow | PASS |
| VR-RPH3-19 | Audit completion before privileged success | cross-store suites and full cross-lane flow | PASS |
| VR-RPH3-20 | Validated tool output; fail closed without executor | T5 gateway/security/failure tests | PASS |

Every row is exercised by the integrated RPH3 test selection and the full repository matrix. PH-5
OS enforcement and PH-7 evidence enforcement remain explicitly outside this verdict.
