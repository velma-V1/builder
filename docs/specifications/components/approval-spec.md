# Component Specification — Approval Engine (CMP-APPROVAL)

**Instance authority:** L25.1 planning record · **Phase:** roadmap PH-3 (RPH3-T3) · **Governing:** `01K`
(§2.6-8/§2.10-11), `01L §3.2` (complete approval-card scope), `01R` Dec A (autonomy-level display). Parent
index: `docs/specifications/components/00-COMPONENT-MAP.md` #11. Baselines inherited; only deltas stated.

```yaml
component_id:          CMP-APPROVAL
name:                  Approval Engine
implementation_phase:  PH-3 (RPH3-T3)
responsibility: >
  Maintains the central approval queue and issues bound, expiring, revocable approvals. Produces complete
  approval cards (full 01L §3.2 scope) that state task, tool, action, path/resource, scope, purpose,
  repetition count, expiration, consequences, and the active autonomy level. Write/execution approvals expire
  automatically and are revocable; destructive/irreversible and real-world external actions require separate
  explicit confirmation from ordinary code-execution approval.
non_responsibilities:
  - Does not compute permission decisions (CMP-PERM) or execute the approved action (CMP-TOOLGW/CMP-FILEOP).
  - Never offers a security violation as an approvable action — such requests are denied + audited (not queued).
  - Creates no permanent/unrestricted or non-expiring authority (01K §2.9).
authoritative_state:   OWNS the approval queue + CTR-APPROVAL-RECORD instances (sole writer of its tables in
                       the PH-3 security-spine store, ODI-RPH3-01; not the runtime-state DB — R1 preserved);
                       every issue/consume/expire/revoke is audited via CMP-AUDITW.
inputs:
  - approval requests from CMP-PERM (destructive/deletion/external/limit-increase/out-of-envelope)
  - operator decisions (grant / deny / revoke)
  - clock (monotonic) for expiration
outputs:
  - ApprovalCard (complete scope, 01L §3.2) for operator display
  - CTR-APPROVAL-RECORD (bound/expiring/revocable) on grant
  - consume/expiry/revocation events (audited)
interfaces:
  - "ApprovalEngine.enqueue(request) -> ApprovalCard"
  - "ApprovalEngine.decide(card_id, operator_decision) -> ApprovalRecord | Denial"
  - "ApprovalEngine.consume(record, action_fingerprint) -> bool   # binds task/action/path/scope/repetition"
  - "ApprovalEngine.revoke(record_id) -> None"
  - "ApprovalEngine.is_valid(record, at) -> bool                  # scope + expiry + repetition check"
dependencies:
  - CMP-PERM (source of approval requests; consumer of granted approvals)
  - CMP-ORCH (read-only reader for task context; records persisted in the PH-3 security-spine store,
    ODI-RPH3-01 — not the runtime-state DB, R1 preserved)
  - CMP-AUDITW (every card/decision/consume/expire/revoke audited)
owned_contracts:       [ CTR-APPROVAL-RECORD ]
permitted_authority:   BASE-P; issues only bound/expiring/revocable approvals; bounded batch approval stays
                       narrow/expiring/revocable/task-bound (01K §2.8).
prohibited_authority:  BASE-X + no reusable/permanent/unbounded approval; a security violation is never
                       presented as an approvable card (denied + audited, 01K acceptance).
trust_boundary:        BASE-T; a consume request is untrusted until the action fingerprint matches the bound
                       task/action/path/scope and the record is unexpired + unrevoked.
failure_modes:
  - reuse attempt outside scope/expiry/repetition -> is_valid=false -> denied
  - expired approval used -> denied (auto-expiry)
  - security-violating request enqueued -> rejected as denial, audited, never queued
degradation_behavior:  BASE-D; approval failure fails closed (no action proceeds without a valid approval).
recovery_behavior:     BASE-R; on restart, unexpired records revalidated; in-flight requests remain pending
                       (never auto-granted); revoked/expired stay terminal.
security_requirements: BASE-S; approval binding + expiry + non-reuse are core controls; violation fails closed.
resource_requirements: BASE-RES; negligible; no GPU/net.
required_tests:
  - scope binding: an approval bound to (task, action, path, scope) rejects any other action
  - expiry: write/execution approvals auto-expire and are then unusable
  - repetition: a bounded batch approval is consumed at most its repetition count, then invalid
  - no reuse: consumed/expired/revoked record cannot be reused (01K #3)
  - security violations denied + audited, never offered as approvals (01K acceptance)
  - card completeness: every card carries the full 01L §3.2 scope + autonomy level + consequences
```

## Lifecycle

- **Initialization:** open the approval queue (via CMP-ORCH); load 01L §3.2 card schema + autonomy-level
  display policy.
- **Runtime:** enqueue request → present complete card → operator decides → on grant, issue bound/expiring
  record → consumer (CMP-PERM/CMP-TOOLGW) consumes once within scope → auto-expire/revoke as applicable.
- **Recovery:** pending requests never auto-grant on restart; unexpired records revalidated before reuse.

## Card completeness note

A card is invalid unless it carries the complete 01L §3.2 scope (task, tool, action, path/resource, scope,
purpose, repetition, expiration, consequences) and the active autonomy level (Dec A). Destructive/external
actions carry an explicit consequence statement and a separate confirmation (01K §2.10-11).
