# Component Specification — Tool Registry (CMP-TOOLREG)

**Instance authority:** L25.1 planning record · **Phase:** roadmap PH-3 (RPH3-T5) · **Governing:** `01K`
(§2.1-3/§2.18-24, acceptance #1/#9/#18). Parent index:
`docs/specifications/components/00-COMPONENT-MAP.md` #9. Baselines inherited; only deltas stated.

```yaml
component_id:          CMP-TOOLREG
name:                  Tool Registry
implementation_phase:  PH-3 (RPH3-T5)
responsibility: >
  The one authoritative registry of approved tools, default-DENY: an unregistered tool cannot execute. Each
  registered tool carries a complete declaration — capabilities, inputs, outputs, side effects, permission
  classes, version, environment needs, resource profile, and failure behavior — plus provenance (source,
  version, checksum/immutable integrity id, license, approval, destination env) for downloaded components.
  Manages tool quarantine: repeatedly failing/compromised/unsafe tools are held until reviewed and released.
non_responsibilities:
  - Does not execute tools or validate their output (CMP-TOOLGW does); does not grant permissions (CMP-PERM).
  - Supports no permanent unrestricted trusted-tool rule (01K §2.9) and no launch plugin ecosystem (01K §2.23).
authoritative_state:   OWNS the tool registry + declarations + quarantine state (sole writer of its tables in
                       the PH-3 security-spine store, ODI-RPH3-01; not the runtime-state DB); registry
                       changes are audited (privileged) via CMP-AUDITW.
inputs:
  - tool declarations (CTR-TOOL-DECLARATION) + provenance records
  - failure/quarantine signals from CMP-TOOLGW
outputs:
  - registration verdicts (approved / rejected)
  - lookup results (is-registered + declaration) for the gateway
  - quarantine/release state transitions (audited)
interfaces:
  - "ToolRegistry.register(declaration, provenance) -> RegistrationVerdict"
  - "ToolRegistry.lookup(tool_id, version) -> ToolDeclaration | NotRegistered"
  - "ToolRegistry.quarantine(tool_id, reason) -> None"
  - "ToolRegistry.release(tool_id, review_ref) -> None"
dependencies:
  - CMP-SCHEMA (tool-declaration schema; PH-1 migration pattern)
  - CMP-PERM (declared permission classes are enforced at call time by the gateway via CMP-PERM)
  - CMP-AUDITW (registration/quarantine/release are privileged, audited actions)
owned_contracts:       [ CTR-TOOL-DECLARATION ]
permitted_authority:   BASE-P; approves only fully-declared tools with pinned versions (01K §2.20); every
                       declaration is complete or the tool is rejected.
prohibited_authority:  BASE-X + never registers a tool without a complete declaration/provenance; never
                       creates permanent unrestricted trust; never auto-releases a quarantined tool.
trust_boundary:        BASE-T; a submitted declaration + downloaded component is untrusted until provenance +
                       integrity identity are recorded and validated (01K §2.18/§2.25).
failure_modes:
  - unregistered tool requested -> lookup=NotRegistered -> gateway denies (default-deny)
  - incomplete declaration/provenance -> registration rejected
  - repeated equivalent tool failure -> quarantine (unusable until reviewed + released)
degradation_behavior:  BASE-D; registry unavailable -> default-deny (no tool runs) rather than allow.
recovery_behavior:     BASE-R; quarantine state is durable; on restart a quarantined tool stays quarantined
                       until an explicit release.
security_requirements: BASE-S; default-deny + complete declaration + provenance + version pinning are core
                       controls; violation fails closed.
resource_requirements: BASE-RES; negligible; no GPU/net (registry only).
required_tests:
  - default-deny: an unregistered tool cannot execute (01K-AC-01)
  - complete declaration required: incomplete declaration rejected
  - provenance/integrity recorded for downloaded components (01K-AC-09)
  - version pinning: a tool is pinned for the duration of a task
  - quarantine: repeated equivalent failure quarantines; no use until released (01K-AC-18)
```

## Lifecycle

- **Initialization:** open the registry (via CMP-ORCH); load the tool-declaration schema.
- **Runtime:** register (complete declaration + provenance) → lookup for the gateway (default-deny on miss) →
  quarantine on repeated failure → release only on explicit review.
- **Recovery:** durable quarantine survives restart; no auto-release.

## Registry ↔ gateway split note

CMP-TOOLREG is the source of truth for *what is approved*; CMP-TOOLGW is the single runtime path for *calling*
an approved tool. A tool absent from the registry is uncallable (default-deny). Recorded in `RPH3-INTEGRATION.md`.
