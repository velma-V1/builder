# Rollback & Recovery Plan

**Status:** Authoritative planning record (L25.1) · **Phases:** PH-2 (journal), PH-5 (sandbox), PH-7 (snapshots), PH-8 (updates)
**Recorded:** July 24, 2026
**Governing:** `01M` (recovery/Watchdog/snapshots), `04` (recovery policy), `01H §4.5` (improvement rollback), `01O §3.6` (executable rollback), `01C §12` (recovery snapshot). In force with `01R`.

> `04-RECOVERY-POLICY` (L22) and `01M` (L15) overlap; where they differ, **`01M` governs** (higher authority, more detailed). `04` provides the coarse policy; `01M` the binding controls.

## 1. Rollback layers
| Layer | Trigger | Mechanism | Scope |
|---|---|---|---|
| Task/checkpoint | failed test, scope drift | return to last verified safe checkpoint (`04 §2-4`, `01D §3.6`) | one task branch |
| Contract activation | failed activation | prior activated version + hash + generation retained (Section 1 §9) | one contract |
| Lane/workstream | integration failure | resume from verified lane checkpoint; partial work preserved unpromoted (`01D §2.18/§2.22`) | one workstream |
| Improvement | pre-approved trigger | automatic restore to last verified approved state; suspend remaining activations (`01H §4.5`) | Factory improvement |
| Update (executable) | failed migration/startup/health | previous executable recoverable until commitment (`01O §3.6`) | Factory install |
| Recovery snapshot | corruption / unknown state | restore active rolling snapshot (Factory-state only) (`01M §3.9`) | Factory state |

## 2. Recovery snapshot model (`01M §3.9`, `01C §12`)
**Single active rolling snapshot** of Factory configuration/databases/specifications/internal state. A new snapshot is a **candidate** and cannot replace the active one until it passes: content/manifest checksums; schema/migration compatibility; journal replay + incomplete-transition handling; record integrity; evidence/checkpoint/permission/reference consistency; successful isolated Factory startup; and **absence of GitHub project-repository restoration**. A failed candidate is quarantined; the active snapshot is unchanged. **GitHub project repositories are excluded** from Factory recovery snapshots and remain user-controlled (`01M §3.32`, `01O §3.8`).

## 3. Reconciliation outcomes (`01M §5`)
After restart/crash/interruption/Watchdog intervention each affected task receives exactly one: `RESUMABLE` / `BLOCKED` / `FAILED` / `QUARANTINED` / `COMPLETED` / `CANCELLED`. `RESUMABLE` only when task record, last verified checkpoint, repo baseline, sandbox/replacement env, model state, mounts, fencing tokens, locks, approvals, artifacts, journals, and evidence all agree — never inferred from a surviving process/container alone.

## 4. Automatic-rollback trigger requirements (`01H §4.5`)
Every pre-approved trigger defines exact metric/event/invariant; deterministic threshold + comparison; minimum sample/duration; debouncing/cooldown/hysteresis (anti-oscillation); max attempt count; verified active-snapshot identity + integrity; affected components/state/metrics/failure-domains; required rollback-event evidence; post-rollback verification + quarantine. A missing/stale/incompatible/unverified recovery path blocks activation. Repeated triggering / failed rollback / uncertain recovery opens the circuit breaker, quarantines, and fails closed.

## 5. Evidence preservation (`04 §10`, `01M §2.15`)
Rollback removes unsafe working state; it never erases history. Failed attempts remain in the audit record; evidence/logs/checkpoints are secured before restart/termination when safely possible; containment takes priority over graceful preservation during immediate danger.

## 6. Emergency storage (`01M §3.10/§3.33-34`)
Reserved storage protects journal commits, evidence finalization, shutdown records, audit events, and recovery metadata; new work pauses before the reserve is consumed. Protected evidence/audit/checkpoints/holds/authoritative memory are **never** auto-deleted to free storage.
