# RPH3-T1 CMP-WATCH Lane A and internal WIR - Verification Evidence

**Scope:** M1 `RPH3_T1_CMP_WATCH_LANE_A` on
`claude/roadmap-ph3-security-spine-planning`. **Date:** 2026-07-30.
**Verdict:** PASS, ready for the next authorized cross-lane integration milestone.
This is not `PROM-RPH3`.

## Environment and exact gates

| Field | Result |
|---|---|
| Windows | Microsoft Windows 10.0.26200.8875 |
| Python | CPython 3.12.13, 3.13.14, 3.14.6 |
| Focused tests | 39 passed on each required Python version |
| Focused coverage | 95.92% branch-aware total for `src/factory/watchdog` (required >=95%) |
| Dedicated verifier | `scripts/verify_roadmap_ph3_t1.py`: 8/8 PASS on each required Python version |
| Full repository | 794 passed, 1 classified skip on each required Python version |
| Ruff | PASS: Watchdog source, tests, and verifier |
| strict mypy | PASS: Watchdog source and tests (17 source files) |
| Warnings | none emitted by the recorded M1 verifier/full-suite runs |
| Skip | `test_symlink_escape_is_denied`: classified NOT_TESTABLE on Windows by its existing contract |

## Migration and integrity evidence

`migrations/security/0004_watchdog.sql` is the next ordered, forward-only security-spine
migration. It creates only the internal WIR intervention journal and the shared version ledger
when absent. Its byte-exact SHA-256 is:

`21ad8fa85055e1e55b703a55865a442b4e1af907c39baf668f7fcf34a4488b80`

The migration is transactionally applied, SHA-pinned before execution, idempotent on an existing
database, and rejects modified or malformed input. Existing migrations were not edited; their
verified hashes remain:

- `0001_security_spine.sql`: `099ae959d6f06c6b944925af151d8fa8dd2b65fdffd63660cf2a4355b7878a51`
- `0002_permission.sql`: `a65d227d9683eb060c834ae8b3cb65f33186ba37420b4065eec8623f8ded88cb`
- `0003_tools.sql`: `0050e74f80932fb58ea15d1f60f95661c7589d57dd623aad7691e26ea73a69b5`

## Delivered behavior

- CMP-WATCH is the single Lane A component. The Watchdog observer has no writable DB, shell,
  filesystem, or policy-mutation interface and is not auto-launched on Windows.
- Monotonic authenticated heartbeats, replay/future rejection, sustained staged thresholds,
  hysteresis, missing-sensor `REDUCED_MONITORING`, and deterministic failure identity are tested.
- Recovery is bounded by attempt count, backoff, and a per-service circuit breaker.
- The internal WIR accepts exactly the seven governed commands. It authenticates the supervised
  Watchdog, bounds targets/reasons, checks expected state, applies an approval/permission authority
  gate, and defaults unknown commands to denial.
- Task interventions call only frozen CMP-ORCH transitions. Service restart calls only the injected
  PH-3 Service Supervisor. Restore/snapshot remain inert until PH-7; non-task quarantine remains
  inert until PH-5.
- Class-2 transitions are durable before completion audit and reconcile by roll-forward/rollback.
  Class-3 restart records audit intent before the external call and quarantines an unproven outcome
  without retry. `APPLIED` is returned only after completion audit durability.
- Duplicate/concurrent requests have one effect and one audit. Watchdog/WIR loss blocks new
  high-risk work and pauses existing high-risk work. Reduced monitoring routes toward Safe Mode;
  critical state routes toward quarantine without granting write authority to the observer.
- The intervention journal has a private structural sole writer; consumers use SQLite `mode=ro`
  with a write-denying authorizer.

## Test categories

| Category | Count | Principal evidence |
|---|---:|---|
| unit/detection/recovery | 12 | heartbeat, thresholds, hysteresis, false-positive resistance, deterministic failure, bounded restart, Safe Mode/quarantine routing |
| migration/store/isolation | 4 | fresh/existing lifecycle, malformed/tampered rejection, read-only reader, writer not exported |
| security/adversarial | 9 | spoofing, wildcard/bulk/stale state, immutable allowlist, authority denial, inert phase boundaries |
| crash/failure/reconciliation | 11 | Watchdog loss, failed restart, Class-2 pre/post-audit windows, Class-3 pre-intent/uncertain/completed windows, audit/store outage |
| integration/concurrency | 3 | pause/contain/restart, audit ordering, duplicate concurrency |
| **Total** | **39** | all PASS |

Detailed traceability is in `roadmap-ph3-t1-watchdog-requirements.md`; crash ordering is in
`roadmap-ph3-t1-watchdog-failure-paths.md`.

## Boundaries and remaining work

- WIR is an internal interface/facet of CMP-WATCH, not a separate component.
- Lane B remains the accepted T2/T3/T4/T5 implementation and was not reimplemented.
- Service registration/automatic launch is intentionally off by default; an external supervisor
  hosts the process-side policy. No direct host shell or PH-5 sandbox enforcement was added.
- Real Permission/Approval/ToolGateway/FileOps/Safe Mode cross-lane propagation is the next
  authorized M2 milestone. The generic M1 authority gate fails closed until that wiring exists.
- SQLite `ResourceWarning` promotion debt remains tracked for M3 root-cause resolution.
- `main`, PR 10, PH-4, PH-5, merge, and `PROM-RPH3` remain untouched/not authorized.
