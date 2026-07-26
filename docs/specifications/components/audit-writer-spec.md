# Component Specification — Audit Writer (CMP-AUDITW)

**Instance authority:** L25.1 planning record · **Phase:** roadmap PH-3 (RPH3-T4) · **Governing:** `01K`
(§2.29/§3.2, acceptance #19/#20), `docs/10 §PH-3`. Parent index:
`docs/specifications/components/00-COMPONENT-MAP.md` #22. Baselines inherited; only deltas stated.

```yaml
component_id:          CMP-AUDITW
name:                  Audit Writer
implementation_phase:  PH-3 (RPH3-T4)
responsibility: >
  The SOLE writer of the tamper-evident privileged-action audit chain. Appends append-only, hash-chained
  records — each carrying a sequence number and predecessor identity — for every privileged, credentialed,
  destructive, external, and promotion action. Optionally signs/keys records when configured. The chain is a
  protected component and a separate authoritative store from the runtime-state DB (single-audit-writer
  invariant, analogous to R1 for state).
non_responsibilities:
  - Never updates or deletes an existing record (append-only; no UPDATE/DELETE path exists).
  - Does not validate the chain (that is CMP-AUDITV) and does not decide permissions/approvals.
  - Does not claim absolute immutability against the machine owner — it provides tamper-EVIDENCE (01K §3.2).
authoritative_state:   OWNS the audit chain store (append-only, hash-chained); sole writer. Records reference
                       task/sandbox/execution/evidence/approval identities.
inputs:
  - audit events (actor, action class, task/resource ref, decision, timestamp, optional payload hash)
  - configured signing key (optional)
outputs:
  - appended AuditRecord (sequence, predecessor_hash, record_hash, optional signature)
  - export bundles (for CMP-AUDITV / operator)
interfaces:
  - "AuditWriter.append(event: AuditEvent) -> AuditRecord   # sole append path; sequence = prev+1"
  - "AuditWriter.head() -> AuditRecord | None                # current chain tip (read)"
  - "AuditWriter.export(range) -> AuditExport                # integrity-checked on the way out"
dependencies:
  - CMP-SCHEMA (PH-1 SHA-256-pinned transactional migration pattern for the audit-chain schema; new 0004_*)
  - CMP-ORCH (append occurs inside a durable transaction; flush-before-success)
owned_contracts:       [ CTR-AUDIT-RECORD ]
permitted_authority:   BASE-P; the ONLY component permitted to append audit records; append is atomic +
                       durable before the audited action is reported successful.
prohibited_authority:  BASE-X + must expose no update/delete path and no second write path; a write that does
                       not extend the chain (bad predecessor/sequence) is rejected.
trust_boundary:        BASE-T; the event payload is untrusted (hashed, never executed); chain identity fields
                       are computed by the writer, never accepted from the caller.
failure_modes:
  - attempted update/delete -> rejected (no such operation)
  - sequence/predecessor mismatch (concurrent append) -> rejected, retry against current head
  - mid-append failure -> transaction rollback; chain unchanged (no partial record)
degradation_behavior:  BASE-D; if the audit store is unavailable, privileged actions fail closed rather than
                       proceed unaudited (audit is a core control, 01M §2.25).
recovery_behavior:     BASE-R; on startup the chain is integrity-checked (via CMP-AUDITV) before it is treated
                       as authoritative; an invalid chain is reported, not silently trusted.
security_requirements: BASE-S; append-only + hash-chaining + optional signing are core controls; the writer is
                       a protected component (governing controls not weakenable via an Improvement Packet).
resource_requirements: BASE-RES; negligible (append-only SQLite/log store); no GPU/net.
required_tests:
  - append-only: no UPDATE/DELETE path exists; attempts rejected (01K-AC-19)
  - hash-chain: each record links predecessor identity + monotonic sequence
  - durability: record is flushed before the audited action reports success
  - concurrency: two appends against the same head — one wins, the other retries; no gap/fork
  - security: caller cannot forge sequence/predecessor/hash fields
```

## Lifecycle

- **Initialization:** open/create the audit-chain store; run the SHA-256-pinned `0004_*` migration; load
  optional signing key; verify the existing chain tip (delegates to CMP-AUDITV).
- **Runtime:** serve `append` under a durable transaction — compute sequence = prev+1 and predecessor hash,
  write, flush, then allow the audited action to report success.
- **Recovery:** integrity-check before serving; an invalid chain marks audit non-authoritative (fail closed).

## Single-audit-writer note

Exactly one CMP-AUDITW instance holds the audit-append authority; no sibling (CMP-PERM/CMP-APPROVAL/
CMP-TOOLGW/CMP-WATCH) writes the chain directly — they all call `append`. This mirrors the R1 single-writer
discipline for the audit domain. Recorded here and in `RPH3-INTEGRATION.md` §Ownership.
