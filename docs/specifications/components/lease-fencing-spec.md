# Component Specification — Lease & Fencing System (CMP-LEASE)

**Instance authority:** L25.1 planning record · **Phase:** PH-2 · **Governing:** `01M §3.6/§3.19`
(fenced expiring leases), `01M §3.12` (monotonic timing), `01R` R1. Parent index: `00-COMPONENT-MAP.md` #28.
Baselines inherited; only deltas stated.

```yaml
component_id:          CMP-LEASE
name:                  Lease & Fencing System
implementation_phase:  PH-2
responsibility: >
  Issues expiring leases over scoped resources with strictly increasing fencing tokens, so a delayed
  former owner cannot write after its lease is superseded. Tokens are PERSISTENT SQLite integers scoped
  to (resource_type, resource_id); every protected write validates the current token.
non_responsibilities:
  - Does not itself guard other components' writes — it provides validate_token; callers enforce it.
  - Does not use time.monotonic() for token ordering (it resets on restart and cannot be compared across
    restarts). Monotonic clocks apply to TTL/stall measurement only, not to token identity.
  - Only TASK and RESOURCE lease kinds exist in PH-2; workspace/branch/model/sandbox/promotion lease kinds
    bind when those components exist (PH-5+) — adding a kind is a shared-contract change, not silent.
authoritative_state:   co-owns fencing_counters + leases sub-schemas.
inputs:                [ resource_type, resource_id, owner_id, ttl_seconds, ProcessEpoch ]
outputs:               [ Lease (with fencing_token, process_epoch, expires_at) ]
interfaces:
  - "LeaseManager.acquire(resource_type, resource_id, owner_id, ttl_seconds) -> Lease"
  - "LeaseManager.renew(lease, ttl_seconds) -> Lease"
  - "LeaseManager.release(lease) -> None"
  - "LeaseManager.validate_token(resource_type, resource_id, token) -> bool"
dependencies:          [ CMP-ORCH (shared DB + tx), ProcessEpoch ]
owned_contracts:       [ CTR-LEASE-FENCING ]
permitted_authority:   BASE-P.
prohibited_authority:  BASE-X; never issues a non-increasing token; never trusts a lease from a prior epoch.
trust_boundary:        BASE-T; a presented token is untrusted until compared to the persisted counter.
failure_modes:
  - write presenting a superseded (lower) token -> validate_token False (rejected)
  - renew with a stale token -> OrchestratorError
  - lease from a different ProcessEpoch -> treated as expired regardless of wall-clock expires_at
degradation_behavior:  BASE-D.
recovery_behavior:     BASE-R; across a restart, tokens keep increasing (persisted counter) and prior-epoch
                       leases are invalid — the cross-restart safety net, not the wall clock.
security_requirements: BASE-S; fencing is a core recovery-safety control (fail closed on token conflict).
resource_requirements: negligible.
required_tests:
  - repeated acquire yields strictly increasing tokens, persisted across a simulated process restart
  - superseded (lower) token rejected by validate_token
  - renew extends expiry only with the current highest token; stale token raises
  - lease whose process_epoch != current epoch treated as expired regardless of expires_at
  - release is idempotent (re-release does not error or mint a new token)
```
