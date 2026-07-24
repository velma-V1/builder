# Workstream Handoff — Template

**Type:** Scaffold (non-authoritative) · **Instance authority:** L26 produced record
**Governing:** `01D` (workstream lifecycle), `01J §2.8` (structured context packet).

## Required contents
```yaml
workstream_id:         WS-...
owner:                 <owner>
completed_scope:       <major stage delivered>
owned_contracts:       [ CTR-... versions (frozen) ]
produced_artifacts:    [ ids + hashes ]
local_verification:    { package_verdict, evidence_ref }   # must pass before integration (01D 2.15)
open_dependencies:     [ ... ]
integration_baseline:  <commit id (unchanged during execution, 01D 3.3)>
checkpoint:            <verified lane checkpoint, 01D 3.6>
conflicts_resolved:    [ 01D 3.4 conflict classes checked ]
handoff_to:            <integration coordinator | next workstream>
```
**Rule:** the integration coordinator diagnoses and assigns from this packet but never edits source (`01D §3.8`). A workstream cannot enter integration without passing its own applicable verification gate.
