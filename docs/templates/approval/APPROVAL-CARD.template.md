# Approval Card — Template

**Type:** Scaffold (non-authoritative) · **Instance authority:** L26 produced record
**Governing:** `01L §3.2` (complete approval-card scope), `01K §2.6` (bound approvals), `01 §11` + `01R` Decision B (deletion approval-required), `01R` Decision A (autonomy envelope).

## Required fields (`01L §3.2`)
```yaml
action:               <exact command | normalized action>
tool:                 { identity, version }
context:              { working_directory, task_branch, worktree, sandbox_id }
affected_paths:       [ ... ]
expected_diffs:       <diff summary>
non_file_effects:     [ resource/state changes ]
network:              { destinations, protocols, operations }        # when applicable
credentials:          { identity, broker_reference, granted_scope }  # secret never shown
external_effects:     [ recipients / side effects ]                  # when applicable
risk_class:           <low | ... | high>
autonomy_level:       <1-100 — whether this level auto-permits or requires this card>
expiration:           <ts>
repetition:           <permitted count>
required_evidence:    [ ids ]
verification_status:  <current>
rollback_available:   <yes/no + reference>
flags:                { reversible, destructive, privileged, promotional, externally_consequential }
decision:             { operator, decision, timestamp, record_id }
```

## Rules
- Fields that do not apply are marked **not applicable**, never silently omitted when absence could change the operator's understanding (`01L §3.2`).
- Security violations are **denied and audited**, not presented as ordinary approvals (`01G §11`, Section 1 §11).
- Every issued card produces a `CTR-APPROVAL-RECORD` and a tamper-evident audit entry.
