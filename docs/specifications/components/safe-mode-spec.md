# Component Specification — Diagnostic Safe Mode (CMP-DIAG, PH-3 scope)

**Instance authority:** L25.1 planning record · **Phase:** roadmap PH-3 (RPH3-T5) · **Governing:** `01K`
(§2.32, acceptance #22), `01M` (§2.26/§3.8, acceptance #20). Parent index:
`docs/specifications/components/00-COMPONENT-MAP.md` #37. Baselines inherited; only deltas stated. **Scope
note:** CMP-DIAG's full diagnostics surface is PH-8; **this spec covers only the PH-3 Safe Mode responsibility.**

```yaml
component_id:          CMP-DIAG
name:                  Diagnostic Safe Mode (PH-3 scope)
implementation_phase:  PH-3 (RPH3-T5)  # full CMP-DIAG diagnostics = PH-8
responsibility: >
  A restricted diagnostic mode that permits inspection, evidence export, integrity checks, recovery, and
  approved repair operations WITHOUT enabling normal autonomous task execution or unrestricted writes. Every
  Safe-Mode repair is an explicit, approved (CMP-APPROVAL), permission-checked (CMP-PERM), audited (CMP-AUDITW)
  action — never an autonomous write. Capability-scoped: it declares exactly which capabilities are available
  and never weakens permission/audit/evidence/verification/isolation/state-authority.
non_responsibilities:
  - Performs no autonomous writes and no normal task execution (01K §2.32 / 01M §2.26).
  - Cannot bypass approvals, permissions, or audit; cannot weaken any mandatory control (BASE-D).
  - Does not build the PH-8 diagnostics/telemetry surface.
authoritative_state:   none; operates in a degraded, capability-scoped mode; every approved repair is applied
                       through the normal CMP-PERM -> CMP-APPROVAL -> CMP-ORCH/CMP-AUDITW path.
inputs:
  - operator entry into Safe Mode; inspection/repair requests
  - integrity verdicts (CMP-AUDITV, CMP-JOURNAL) to guide approved repair
outputs:
  - inspection/integrity/evidence-export results (read-only)
  - approved-repair actions (each permission-checked + approved + audited)
  - a visible capability-scope declaration (what is available vs blocked)
interfaces:
  - "SafeMode.enter(reason) -> SafeModeSession"
  - "SafeMode.inspect(target) -> InspectionResult          # read-only"
  - "SafeMode.export_evidence(range) -> EvidenceExport      # read-only"
  - "SafeMode.approved_repair(action, approval_ref) -> RepairResult  # requires valid CMP-APPROVAL"
dependencies:
  - CMP-PERM (permission check on every repair)
  - CMP-APPROVAL (explicit approval for every repair)
  - CMP-AUDITW (all inspection-privileged + repair actions audited)
  - CMP-AUDITV / CMP-JOURNAL (integrity inputs)
owned_contracts:       [ ] (consumes CTR-PERMISSION-GRANT, CTR-APPROVAL-RECORD, CTR-AUDIT-RECORD)
permitted_authority:   BASE-P restricted to inspection/export/integrity/recovery + approved repair only.
prohibited_authority:  BASE-X + NO autonomous write, NO unrestricted execution, NO approval/permission bypass.
trust_boundary:        BASE-T; inspection inputs are untrusted; repair proceeds only on a valid approval bound
                       to the exact action.
failure_modes:
  - unapproved repair attempted -> denied (no autonomous write path)
  - capability requested outside the declared scope -> refused
degradation_behavior:  BASE-D; Safe Mode IS a capability-scoped degraded mode; it explicitly enumerates
                       available vs blocked capabilities and weakens no mandatory control.
recovery_behavior:     BASE-R; supports recovery/integrity operations but never silent resume; exit to normal
                       operation requires the standard controls to be healthy (fail closed otherwise).
security_requirements: BASE-S; "no autonomous writes / no approval bypass" is a core control verified by test.
resource_requirements: BASE-RES; negligible; no GPU/net.
required_tests:
  - Safe Mode performs no autonomous writes (01K-AC-22 / 01M-AC-20)
  - a repair without a valid approval is denied
  - inspection/export are read-only and cannot mutate authoritative state
  - capability scope is declared and enforced (out-of-scope request refused)
  - no mandatory control (permission/audit/evidence/isolation/state-authority) is weakened in Safe Mode
```

## Lifecycle

- **Initialization:** enter on operator request or as a fail-closed fallback; publish the capability-scope
  declaration.
- **Runtime:** inspect/export/verify freely (read-only); apply repairs only through permission + approval +
  audit; block anything outside the declared scope.
- **Exit:** return to normal operation only when the mandatory controls are verified healthy.
