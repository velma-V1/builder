# Section (Phase) Handoff — Template

**Type:** Scaffold (non-authoritative) · **Instance authority:** L26 produced record
**Governing:** `01D §1` (design→…→handoff), `01J §2.8` (structured handoff packets), Section 1 plan Task 5, `HANDOFF.md` shape.

## Required contents
```yaml
phase:                 PH-...
completed_scope:       <what was delivered>
evidence_refs:         [ evidence package ids + ETM refs ]
produced_interfaces:   [ frozen interfaces / contracts ]
produced_contracts:    [ CTR-... versions ]
produced_schemas:      [ schema ids ]
open_items:            [ known limitations / deferred ]
next_phase_prerequisites: [ what the consuming phase needs ]
checkpoint:            <checkpoint id>
baseline:              <commit id>
verification_status:   { per_criterion_verdicts, package_verdict }
approvals:             [ phase-exit approval record ]
self_hosting_cutover:  <St.N enabled? (01B)>
```
**Rule:** a handoff cannot claim readiness without its verification evidence (`01D §2.15/§3.6`). Consumed by the next phase plan, the workstream map, and the integration coordinator.
