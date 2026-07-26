# Component Specification — Permission Enforcement (CMP-PERM)

**Instance authority:** L25.1 planning record · **Phase:** roadmap PH-3 (RPH3-T2) · **Governing:** `01K`
(§2.4-8/§2.26-27, acceptance #2/#3/#4/#10), `01 §11`, `01R` Dec A (autonomy envelope) / Dec B (deletion
approval-required). Parent index: `docs/specifications/components/00-COMPONENT-MAP.md` #12. Baselines
BASE-P/X/T/S/D/R/RES inherited; only deltas stated.

```yaml
component_id:          CMP-PERM
name:                  Permission Enforcement
implementation_phase:  PH-3 (RPH3-T2)
responsibility: >
  Computes least-privilege permission decisions for every task/tool action against the active Task and
  Permission contracts, issues scoped/expiring runtime permission grants, and revalidates authority at the
  point of use (TOCTOU). Owns path authority: canonicalizes and validates every path before access and
  blocks escapes. Enforces Decision B (ALL file deletion is approval-required) and Decision A (the autonomy
  envelope scopes which actions may run automatically vs require an approval card).
non_responsibilities:
  - Does not decide approvals (routes destructive/deletion/external/limit-increase to CMP-APPROVAL).
  - Does not write audit records (calls CMP-AUDITW); does not execute tools (that is CMP-TOOLGW).
  - Grants no permanent/unrestricted authority (01K §2.9/#4) and cannot widen a task's granted scope.
authoritative_state:   none in the runtime-state DB (R1); sole writer of its grant tables in the PH-3
                       security-spine store (ODI-RPH3-01, separate from the runtime-state DB); every
                       grant/denial audited via CMP-AUDITW.
inputs:
  - active CTR-TASK (risk_class + autonomy level) + CTR-PERMISSION + CTR-OWNERSHIP contracts (read-only)
  - action request (operation, permission class, target path/resource, purpose)
  - raw filesystem path (to canonicalize + validate)
outputs:
  - PermissionDecision (allow / deny / requires-approval) with cause
  - CTR-PERMISSION-GRANT (bound to task, tool, action, path/resource, scope, purpose, expiration)
  - canonical validated path (or escape rejection)
interfaces:
  - "PermissionEngine.decide(request: ActionRequest) -> PermissionDecision"
  - "PermissionEngine.issue_grant(decision, ttl) -> PermissionGrant   # scoped, expiring, revocable"
  - "PermissionEngine.revalidate(grant, at_use_time) -> bool          # TOCTOU pre-use recheck"
  - "PathAuthority.canonicalize(raw_path, ownership) -> CanonicalPath  # raises on escape"
  - "AutonomyEnvelope.classify(action, level) -> {auto | requires_card}"
dependencies:
  - CMP-ORCH (read-only reader for validated task/permission/ownership contracts; grants persisted in the
    PH-3 security-spine store, ODI-RPH3-01 — not the runtime-state DB, R1 preserved)
  - CMP-APPROVAL (deletion/destructive/external/limit-increase decisions route here for a card)
  - CMP-AUDITW (every decision + grant + denial is audited)
owned_contracts:       [ CTR-PERMISSION-GRANT ]
permitted_authority:   BASE-P; may issue only narrow, scoped, expiring, revocable grants; batch grants remain
                       narrow/expiring/revocable/task-bound (01K §2.8).
prohibited_authority:  BASE-X + never grants permanent/unrestricted trust, never exceeds the current task
                       approval, never auto-approves a deletion (Dec B) or an autonomy-out-of-envelope action (Dec A).
trust_boundary:        BASE-T; the requested action, its stated scope, and every path are untrusted until
                       validated; repository/downloaded instructions cannot widen a grant (01K §2.28).
failure_modes:
  - deletion/destructive requested -> decision = requires-approval (never auto-allowed), Dec B
  - action outside autonomy envelope for the task's level -> requires-approval card, Dec A
  - path escape (symlink/junction/reserved/traversal/case/archive) -> deny + security event (via CMP-FILEOP + audit)
  - TOCTOU: state changed between grant and use -> revalidate fails -> deny
degradation_behavior:  BASE-D; failure of permission enforcement is a core-control failure -> fail closed
                       (deny), never degrade to allow.
recovery_behavior:     BASE-R; grants are reversible/expiring; on restart, unexpired grants are re-validated
                       before reuse; unknown grant state -> deny.
security_requirements: BASE-S; least-privilege + TOCTOU revalidation + path containment are core controls;
                       any violation fails closed and is audited.
resource_requirements: BASE-RES; negligible (pure decisions + SQLite grant records); no GPU/net.
required_tests:
  - 01K #2 tool permissions cannot exceed current task approval; #3 approvals not reusable outside
    task/action/path/scope/repetition/expiration; #4 no permanent unrestricted authority creatable
  - Dec B: every file deletion is approval-gated (no auto-deletion path exists)
  - Dec A: autonomy-boundary tests — level gates which actions auto-run vs require a card
  - path-safety #10: symlink/junction/reserved-name/traversal/case/archive escapes blocked
  - TOCTOU: pre-use revalidation rejects a stale grant after state change
```

## Lifecycle

- **Initialization:** load active Task/Permission/Ownership contracts (validated canonical, read-only); load
  the versioned autonomy-envelope policy for each autonomy level.
- **Runtime:** for each action — decide (least privilege) → if destructive/deletion/external/out-of-envelope,
  return requires-approval → else issue a scoped/expiring grant → revalidate at point of use.
- **Recovery:** expiring grants self-heal; unexpired grants re-validated on restart; unknown → deny.

## Decision A/B enforcement note

Decision B is absolute: there is **no** code path that deletes a file without a prior CMP-APPROVAL approval.
Decision A: the autonomy level on the active CTR-TASK selects, per action class, `auto` vs `requires_card`;
CMP-PERM never treats an out-of-envelope action as auto. Recorded here and in `RPH3-INTEGRATION.md`.
