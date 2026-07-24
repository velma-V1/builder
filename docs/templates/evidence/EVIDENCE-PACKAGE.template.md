# Evidence Package — Template

**Type:** Scaffold (non-authoritative) · **Instance authority:** L26 produced record
**Governing:** `01G §6` (finalized verification package), `01C §2`. Integrity-protected once finalized (`01G §2.18`); proportionate hashing (`01G §2.19`).

## Required contents (`01G §6`)
```yaml
identifiers:           { task_id, project_id, workstream_id, requirement_ids, environment_id, artifact_ids, evidence_id }
versions:              { acceptance_criteria_version, verification_plan_version }
evidence_traceability_manifest: <embed or reference the complete ETM>
selected_methods:      [ unit, integration, system, regression, security, performance, visual, reproducibility, manual ]
method_rationale:      <why each selected; why any normally-expected check is N/A>
execution:             { commands, procedures, configurations, versions, inputs, outputs, errors, exit_codes, timestamps }
baseline:              { identity, comparison_result }   # when applicable
retry_instability:     { retry_history, instability_status, quarantine_status, owner, deadline }  # when applicable
requirement_coverage:  <requirement-by-requirement>
integrity:             { artifact_hashes, evidence_package_hash }
verification_changes:  [ change_records + superseded_versions ]  # 01G 3.2
unrelated_failures:    [ deterministic evidence + residual-risk approvals ]  # 01G 3.4
unresolved:            { failures, limitations, exclusions, uncertainty }
verdicts:              { per_criterion, package_verdict, promotion_eligibility }
```

## Rules
- Missing/unstable/quarantined verification is represented explicitly and cannot be estimated into a pass (`01G §2.25`).
- Release candidates additionally require a clean recreated-environment result (`01G §2.21`).
- Consumed by the Promotion Package, the release plan, and the completion checklist.
