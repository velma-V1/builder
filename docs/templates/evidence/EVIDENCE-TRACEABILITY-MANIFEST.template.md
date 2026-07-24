# Evidence Traceability Manifest — Template

**Type:** Scaffold (non-authoritative) · **Instance authority:** L26 produced record
**Governing:** `01G §3.1` (mandatory per required criterion) · machine schema: `schemas/manifests/etm-v1.schema.json` (PH-7)
**Rule:** one record per required acceptance criterion; a broken/missing/ambiguous/hash-mismatched link makes the criterion incomplete and **blocks promotion**. Stable identifiers, not narrative. Protected component (`01H §4.1`); anti-weakening (`01G §3.2`).

## Per-criterion record (required fields)
```yaml
project_id:            PROJ-...
requirement_id:        REQ-...
task_id:               TASK-...
acceptance_criterion:  <stable criterion id + statement>
verification_plan_id:  <plan id>
check_id:              <check id>
command_or_procedure:  <exact automated command | normalized manual procedure>
tool_versions:         { tool: ver, dependency: ver, fixture: ver, expected_output: ver }
environment:           { identity, configuration, sandbox_id, source_commit, hardware_profile }
start_time:            <ts>
completion_time:       <ts>
exit_status:           <code>
measured_result:       <actual-result field>
expected_result:       <expected>
verdict:               PASS | FAIL | BLOCKED | INCONCLUSIVE | NOT_TESTABLE
evidence_file:         <path | stable evidence id>
evidence_hash:         <sha-256>
tested_artifact_id:    <artifact id>
tested_artifact_hash:  <sha-256>
baseline:              <baseline id + comparison>   # when applicable
approver:              <approver id + approval_record_id> | APPROVAL_NOT_REQUIRED_BY_POLICY
refs:                  { supersession, retry, instability, exclusion, residual_risk }  # when applicable
```

## Package-level rule
A package-level `PASS` may be issued only when the manifest proves complete promotion-eligible coverage for **every** required criterion (`01G §3.1`). Any required criterion with a non-`PASS` verdict blocks promotion.
