# Component Specification — Memory System, Core (CMP-MEM, PH-2 partial)

**Instance authority:** L25.1 planning record · **Phase:** PH-2 (partial; retention/global/holds are PH-7)
· **Governing:** `01F §2/§3/§4`, `01R` R1. Parent index: `00-COMPONENT-MAP.md` #24. Baselines inherited;
only deltas stated.

```yaml
component_id:          CMP-MEM
name:                  Memory System (core project-authority records)
implementation_phase:  PH-2 (partial)
responsibility: >
  Stores project-authority memory records only, with provenance, status lifecycle
  (PROPOSED/VERIFIED/SUPERSEDED/REFUTED/ARCHIVED), and versioned correction. Corrections and
  supersessions never edit a row in place — they insert a new record linked to the prior one.
non_responsibilities:
  - Implements ONLY the PROJECT_AUTHORITY class. Active-task-context, user-preference, global-knowledge,
    raw-session, and derived-retrieval classes (01F §3) are NOT implemented here (PH-7 / deferred).
  - No retention lifecycle, no holds, no integrity scan, no global-namespace promotion (PH-7).
  - Cannot store secrets — the record shape has no free-form value field capable of holding one.
authoritative_state:   owns memory_records sub-schema (append + supersede-by-insert; no in-place edit).
inputs:                [ MemoryRecord (source, scope, summary<=64KiB, evidence_ref?, supersedes?) ]
outputs:               [ MemoryRecord with assigned status; linked supersession chains ]
interfaces:
  - "MemoryStore.propose(record) -> MemoryRecord      # status PROPOSED"
  - "MemoryStore.verify(record_id) -> MemoryRecord    # PROPOSED -> VERIFIED only"
  - "MemoryStore.supersede(record_id, new_record) -> MemoryRecord  # inserts new, marks prior SUPERSEDED"
  - "MemoryStore.get(record_id) -> MemoryRecord | None"
dependencies:          [ CMP-ORCH (shared DB + tx) ]
owned_contracts:       [ CTR-MEMORY-RECORD (partial: PROJECT_AUTHORITY only) ]
permitted_authority:   BASE-P; records become authoritative only via explicit verify (no auto-persist).
prohibited_authority:  BASE-X; a model conversation cannot become a permanent record automatically (01F §2.2).
trust_boundary:        BASE-T.
failure_modes:
  - verify on a non-PROPOSED (already SUPERSEDED/REFUTED/ARCHIVED) record -> rejected
  - supersede attempting in-place edit -> impossible by construction (insert-only)
degradation_behavior:  BASE-D.
recovery_behavior:     BASE-R; superseded rows remain readable (history preserved, 01F §2.7/§2.9).
security_requirements: BASE-S; memory_class DB-constrained to 'PROJECT_AUTHORITY'; no secret-bearing field.
resource_requirements: negligible.
required_tests:
  - newly proposed record has status PROPOSED
  - verify moves PROPOSED -> VERIFIED only; rejects verifying a non-PROPOSED record
  - supersede inserts a new record with supersedes=prior_id, marks prior SUPERSEDED, both remain readable
  - MemoryRecord field set is exactly {record_id, project_id, memory_class, status, source, scope,
    summary, evidence_ref, supersedes, created_at} — no free-form value field (structural test)
```
