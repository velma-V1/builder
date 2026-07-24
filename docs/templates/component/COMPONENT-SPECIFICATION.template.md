# Component Specification — Template

**Type:** Scaffold (non-authoritative) · **Instance authority:** L25.1 planning record
**Governing:** `02` + the component's governing supplement(s); `01R` (R1–R5). Placement: `docs/specifications/components/<component>-spec.md`.

## Required fields (mirrors Pass-4 component map)
```yaml
component_id:          CMP-...
name:                  <name>
implementation_phase:  PH-...
responsibility:        <what it does>
non_responsibilities:  [ what it must not do ]
authoritative_state:   <owns? / none (submits to Orchestrator, R1)>
inputs:                [ ... ]
outputs:               [ ... ]
interfaces:            [ public interface signatures ]
dependencies:          [ CMP-... ]
owned_contracts:       [ CTR-... ]
permitted_authority:   <BASE-P + deltas>
prohibited_authority:  <BASE-X + deltas>   # no direct authoritative-state write except Orchestrator
trust_boundary:        <BASE-T + delta>
failure_modes:         [ ... ]
degradation_behavior:  <BASE-D + delta>
recovery_behavior:     <BASE-R + delta>
security_requirements: <BASE-S + delta>
resource_requirements: <BASE-RES + delta>
required_tests:        [ governing-supplement acceptance criteria + categories ]
```
Baseline authority/trust/security/degradation/recovery/resource defaults are defined in the Pass-4 component map header and `docs/10`. Interface change = Change Contract with consumer-impact analysis (`01D §3.2`).
