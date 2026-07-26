# Schema Registry

**Status:** Derived/non-overriding reference (L25.D)
**Recorded:** July 24, 2026
**Sources:** Section 1 §15 (schema layout), `01G/01E/01I` manifest requirements, `01 §16` serialization, `01P §3.2` schema versioning. In force with `01R`.

Regenerated when a schema is added or versioned. All contract schemas use JSON Schema Draft 2020-12 with `additionalProperties: false` at authority-bearing objects (Section 1 Task 1). Manifest schemas live under `schemas/manifests/` and are built by their owning phase.

## Contract schemas (PH-1)

| Schema | `$id` | schema_version | Path | Owning phase |
|---|---|---|---|---|
| common definitions | `https://factory.local/schemas/common/definitions-v1.schema.json` | 1.0 | `schemas/common/definitions-v1.schema.json` | PH-1 |
| common envelope | `https://factory.local/schemas/common/envelope-v1.schema.json` | 1.0 | `schemas/common/envelope-v1.schema.json` | PH-1 |
| Project | `…/contracts/project/v1.schema.json` | 1.0 | `schemas/contracts/project/v1.schema.json` | PH-1 |
| Requirement | `…/contracts/requirement/v1.schema.json` | 1.0 | `schemas/contracts/requirement/v1.schema.json` | PH-1 |
| Task | `…/contracts/task/v1.schema.json` | 1.0 | `schemas/contracts/task/v1.schema.json` | PH-1 (adds `risk_class`, `autonomy_level` per R5/Dec A) |
| Ownership | `…/contracts/ownership/v1.schema.json` | 1.0 | `schemas/contracts/ownership/v1.schema.json` | PH-1 |
| Permission | `…/contracts/permission/v1.schema.json` | 1.0 | `schemas/contracts/permission/v1.schema.json` | PH-1 (deletion approval-gated; autonomy envelope) |
| Evidence | `…/contracts/evidence/v1.schema.json` | 1.0 | `schemas/contracts/evidence/v1.schema.json` | PH-1 (verdict enum = 01G five values) |
| Change | `…/contracts/change/v1.schema.json` | 1.0 | `schemas/contracts/change/v1.schema.json` | PH-1 |

## Runtime / migration schemas

| Schema | Path | Owning phase | Notes |
|---|---|---|---|
| activation store | `migrations/contracts/0001_activation_store.sql` | PH-1 | WAL, FK, append-only events (Section 1 plan T4) |
| runtime-state DB | `migrations/runtime/*.sql` | PH-2 | tasks/lanes/queues/leases/journal/counters |
| security-spine (permission/approval/tool + `*_intents` + `intervention_journal`) | `migrations/security/0001_security_spine.sql` | PH-3 | PH-3-owned store, separate from runtime DB (DEP-RPH3 §2/§3/§3.1, ODI-RPH3-01); per-domain sole writer incl. operation-intent tables (XSC-RPH3); R1 preserved |
| model fingerprint/exec/quota | `migrations/runtime/*` | PH-4 | |
| audit chain | `migrations/audit/0001_audit_chain.sql` | PH-3 | separate append-only hash-chained store; CMP-AUDITW sole writer; `UNIQUE(op_key)`; `RAISE(ABORT)` on UPDATE/DELETE |

## Roadmap PH-3 (RPH3) contract schemas (Draft 2020-12; authored RPH3 implementation, arch DEP-RPH3)

| Schema | `$id` | schema_version | Owner | Contract |
|---|---|---|---|---|
| permission-grant | `…/contracts/permission-grant/v1.schema.json` | 1.0 | CMP-PERM (PH-3) | CTR-PERMISSION-GRANT |
| approval-record | `…/contracts/approval-record/v1.schema.json` | 1.0 | CMP-APPROVAL (PH-3) | CTR-APPROVAL-RECORD |
| tool-declaration | `…/contracts/tool-declaration/v1.schema.json` | 1.0 | CMP-TOOLREG (PH-3) | CTR-TOOL-DECLARATION |
| audit-record | `…/contracts/audit-record/v1.schema.json` | 1.0 | CMP-AUDITW (PH-3) | CTR-AUDIT-RECORD |

## Manifest schemas (`schemas/manifests/`)

| Schema | Path | Owning phase | Source |
|---|---|---|---|
| Evidence Traceability Manifest | `schemas/manifests/etm-v1.schema.json` | PH-7 | `01G §3.1` |
| Evidence Package | `schemas/manifests/evidence-package-v1.schema.json` | PH-7 | `01G §6` |
| Promotion Package | `schemas/manifests/promotion-package-v1.schema.json` | PH-5/PH-7 | `01E §3.8` |
| Project Baseline Manifest | `schemas/manifests/project-baseline-manifest-v1.schema.json` | PH-5 | `01I §3.3` |
| Snapshot Manifest | `schemas/manifests/snapshot-manifest-v1.schema.json` | PH-7 | `01M §3.9` |
| Release Manifest | `schemas/manifests/release-manifest-v1.schema.json` | PH-8 | `01O §3.9` |
| Graph Index | `schemas/manifests/graph-index-v1.schema.json` | PH-8 | `01P §3.1/§3.2` |
| Support Profile | `schemas/manifests/support-profile-v1.schema.json` | PH-8 | `01O §3.2` |

## Compatibility & migration rules
- Schema identity = `(contract_type, schema_version)`; loaded by `SchemaRegistry` (Section 1 plan Task 1), fail on duplicate `$id`, unsupported draft, or missing family.
- A new schema version must be migrated deterministically or the old index rebuilt (`01P §3.2`); no old index appears current under incompatible code.
- Incompatible schema/state downgrade fails closed (`01O §2.29`).
