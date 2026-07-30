# Factory Test & Verification Strategy

**Status:** Authoritative planning record (L25.1)
**Recorded:** July 24, 2026
**Governing:** `01G` (verification & evidence), `01C §2`, `01M §30` (failure sims), `01O §3.7` (lifecycle/failure paths), `01N/01O` (Windows-11-Home baseline). In force with `01R` (R5 verdicts/ETM).

## 1. Verification architecture (canonical)

Every required acceptance criterion carries a mandatory **Evidence Traceability Manifest** chain (`01G §3.1`):
```
Requirement → acceptance criterion → test/check → command/procedure → environment
→ expected result → actual-result field → evidence file → evidence hash
→ tested-artifact hash → approver / approval record
```
Broken, ambiguous, missing, or hash-mismatched links make the criterion incomplete and **block promotion**.

## 2. Verdicts (only these — `01G §3.3`, R5)

| Verdict | Meaning | Promotion effect (required criterion) |
|---|---|---|
| `PASS` | complete valid evidence met expected result | allowed only after all gates + approvals |
| `FAIL` | check ran/inspected, result not met | blocks |
| `BLOCKED` | dependency/permission/prereq/env/resource prevented completion | blocks until resolved |
| `INCONCLUSIVE` | evidence insufficient/conflicting/unstable | blocks |
| `NOT_TESTABLE` | cannot be performed under declared constraints | blocks (permitted only for documented non-required checks) |

Any required criterion with a non-`PASS` verdict blocks promotion; missing/unstable/quarantined verification cannot be estimated into a pass; a retry-dependent pass is `UNSTABLE` and cannot alone satisfy a required criterion (`01G §3.5`).

## 3. Anti-weakening protocol (`01G §3.2`)
After implementation-start (task `RUNNING` / first material change / first implementation command), changing any acceptance criterion, test, fixture, expected output, threshold, command, environment, baseline, or required-vs-non-required classification requires **all** of: recorded justification · separate approval · versioned supersession · impact analysis · affected-scope re-verification. A change whose primary purpose is to convert a failure into a pass without proving the original invalid is rejected and recorded as an anti-gaming/security event. The ETM system and verification engine are protected control-plane components (`01H §4.1`).

## 4. Verification classes & selection (`01G §2.7`, §4)
Distinguish unit, integration, system, regression, security, performance, visual, reproducibility, and manual verification. Select the **minimum complete** set proving the task without weakening required coverage; the verification plan states why each selected check is required and why any normally expected check is not applicable. Security testing is required when a change affects permissions, inputs, execution, network, secrets, trust boundaries, or isolation (`01G §2.8`); performance testing when resource/latency/capacity behavior may have changed (`01G §2.9`).

## 5. Environment identity & reproducibility
Every verification record retains commands, tool/dependency versions, configuration, environment identity, inputs, outputs, errors, exit codes, timestamps, and resource data (`01G §2.16`). Release candidates are verified in a clean recreated environment (`01G §2.21`). Environments: `ENV-DEV`, `ENV-SANDBOX`, `ENV-CLEAN`, `ENV-CLEAN-WIN` (unactivated Windows 11 Home), `ENV-ISO-RESTORE`, `ENV-OFFLINE`.

## 6. Numeric flaky-test policy (`01G §3.5`)
- Max **2** automatic retries after the initial failure (3 total attempts); delays **5 s** then **30 s**; only when artifact/source/test/fixture/command/config/env unchanged.
- A pass after any retry is `UNSTABLE`, not a clean `PASS`, and cannot alone satisfy a required criterion.
- Quarantine when (a) a failure→retry-pass occurs in 2 sessions within 7 days, or (b) 3 retry-dependent passes within 30 days. Quarantined tests get an owner within 1 business day and a deadline within 7 days; reinstatement requires 5 consecutive first-attempt clean passes across ≥2 clean sessions.

## 7. Failure-path, recovery & Windows evidence
- Failure-path and recovery simulations per `01M §30` / `01O §3.7`: crash, interruption/power-loss, failed migration, corrupted package, invalid/expired/revoked signature, artifact-hash mismatch, disk-full, missing network, missing/incompatible model, WSL/Docker unavailable, snapshot creation/verification/restoration failure, lease-fencing, restart-exhaustion, Watchdog-loss, upgrade-from-every-supported-version, unsupported-downgrade rejection, uninstall with/without data removal.
- Windows 11 Home tests run on the declared baseline **without requiring activation** (`01N`, `01O §2.36-37`); activated and unactivated systems follow identical tests.

## 8. Evidence integrity & coverage
Finalized evidence packages and promoted artifacts receive integrity identities (`01G §2.18/§2.20`); proportionate hashing (`01G §2.19`) — not every log line. Coverage: ≥95% branch coverage for `src/factory/contracts` (Section 1); each phase defines its own coverage obligation in its phase plan. A package-level `PASS` requires complete promotion-eligible coverage for every required criterion (`01G §3.1`).

## 9. Model review is not verification
A separate model may critique or review, but its findings remain claims until verified by an approved deterministic method (`01G §2.22-23`, `01J §1`). Deterministic evidence is authoritative.

## 10. Category → phase mapping
The full 35-category → component/task/requirement/environment/evidence/gate mapping is maintained in `docs/planning/VERIFICATION-MATRIX.md`.
