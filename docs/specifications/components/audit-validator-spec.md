# Component Specification — Audit-Chain Validator (CMP-AUDITV)

**Instance authority:** L25.1 planning record · **Phase:** roadmap PH-3 (RPH3-T4) · **Governing:** `01K`
(§3.2, acceptance #20), `docs/10 §PH-3`. Parent index:
`docs/specifications/components/00-COMPONENT-MAP.md` #23. Baselines inherited; only deltas stated.

```yaml
component_id:          CMP-AUDITV
name:                  Audit-Chain Validator
implementation_phase:  PH-3 (RPH3-T4)
responsibility: >
  Verifies audit-chain integrity at startup, export, recovery, and release. Recomputes the hash chain,
  checks sequence continuity and predecessor identity, verifies signatures/anchors when configured, and
  detects deletion, truncation, reordering, rewriting, chain discontinuity, and invalid anchoring. Reports a
  detected break as an integrity/security event; while integrity is invalid, audit records are treated as
  NON-authoritative.
non_responsibilities:
  - Writes nothing to the chain (read-only over CMP-AUDITW's store; never repairs in place).
  - Does not decide permissions/approvals; does not delete/quarantine (raises events consumed by CMP-WATCH).
authoritative_state:   none (read-only validator; emits verdicts + integrity/security events).
inputs:
  - audit chain / export bundle (read-only, from CMP-AUDITW)
  - configured verification anchors / public keys (optional)
outputs:
  - IntegrityVerdict (valid / broken) with the first offending sequence + break class
  - integrity/security event on break (to CMP-WATCH + CMP-AUDITW as a new audited event)
interfaces:
  - "AuditValidator.verify_chain(range=all) -> IntegrityVerdict"
  - "AuditValidator.verify_export(bundle) -> IntegrityVerdict"
  - "AuditValidator.classify_break(verdict) -> {deletion|truncation|reorder|rewrite|discontinuity|bad_anchor}"
dependencies:
  - CMP-AUDITW (reads the chain/exports; the single writer whose output it checks)
  - CMP-WATCH (consumes integrity/security events raised on a detected break)
owned_contracts:       [ ] (validates CTR-AUDIT-RECORD; owns none)
permitted_authority:   BASE-P minus write; read-only verification only.
prohibited_authority:  BASE-X + never mutates or repairs the chain; never marks a broken chain valid.
trust_boundary:        BASE-T; the chain under test is untrusted input until verification passes; identity is
                       recomputed, not accepted from record fields.
failure_modes:
  - deletion/truncation/reorder/rewrite/invalid-anchor -> verdict=broken + classified + security event
  - missing anchor/key when required -> INCONCLUSIVE (treated as not-valid; fail closed)
degradation_behavior:  BASE-D; inability to verify => audit treated as non-authoritative (never assumed valid).
recovery_behavior:     BASE-R; a broken chain blocks reliance on audit until an operator-governed recovery;
                       no automatic in-place repair.
security_requirements: BASE-S; break detection is a core control; a detected break is a security event that
                       (via CMP-WATCH) can pause/contain high-risk work.
resource_requirements: BASE-RES; negligible (hash recomputation); no GPU/net.
required_tests:
  - detects deletion of a middle record (sequence gap)
  - detects truncation (missing tail)
  - detects reordering (predecessor mismatch)
  - detects rewriting (record hash mismatch)
  - detects invalid anchor/signature when configured
  - audit treated as non-authoritative while a break is unresolved (01K-AC-20)
```

## Lifecycle

- **Initialization:** invoked by CMP-AUDITW at startup before the chain is trusted.
- **Runtime:** verify on export/recovery/release and on demand; classify any break; raise a security event.
- **Recovery:** a broken chain is reported and blocks audit reliance; recovery is operator-governed (no silent
  repair, never marks broken as valid).
