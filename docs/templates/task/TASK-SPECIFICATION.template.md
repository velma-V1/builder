# Task Specification — Template

**Type:** Scaffold (non-authoritative) · **Instance authority:** L25.1 planning record
**Governing:** owning phase plan; Section 1 contract families; `01D` (task branch/workstream), `01M §3.11` (risk class), `01G` (evidence/ETM), `01 §11` + `01R` Dec B (deletion), `01I §2.8` (baseline), `01R` Dec A (autonomy).
**Placement:** embedded in the phase plan by default; promoted to `docs/plans/section-N/task-NN-<slug>.md` when large. Source for the task's later Task/Ownership/Permission/Evidence contracts.

## Required fields
```yaml
task_id:               TASK-...
phase:                 PH-...
objective:             <one bounded objective>
deliverables:          [ ... ]
parent_requirements:   [ REQ-... ]
owned_paths:           [ ... ]
forbidden_paths:       [ ... ]
protected_paths:       [ ... ]
read_only_paths:       [ ... ]
frozen_interfaces:     [ ... ]
dependencies:          [ task/contract refs ]
permitted_routes:      [ LOCAL_FAST | LOCAL_SUPERVISOR | LANE_n_WORKER/REVIEWER ]
resource_limits:       { tokens, requests, retries, time, files }
environment_class:     <ENV-DEV | ENV-SANDBOX | ...>
risk_class:            <low | ... | high>        # 01M 3.11 (mandatory)
autonomy_level:        <1-100 envelope>          # 01R Dec A
checkpoint_policy:     <...>
recovery_policy:       <...>
acceptance_criteria:   [ criterion -> ETM chain (01G 3.1) ]
deletion_policy:       approval-required          # 01R Dec B
completion_conditions: [ 01 13 gate items ]
```
**Rule:** every field schema-valid against the Task/Ownership/Permission/Evidence schemas; ownership/scope change = Change Contract; verification change = `01G §3.2`.
