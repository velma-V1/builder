# Roadmap PH-3 — Deployment & Migration Plan (DEP-RPH3)

**Document ID:** DEP-RPH3 · **Repository path:** `docs/planning/RPH3-DEPLOYMENT-MIGRATION.md`
**Status:** Active plan (subordinate to `01O`/`01N`/`docs/release/*`) · **Owner:** RPH3 planning (Pass 9) ·
**Established:** 2026-07-26. **Governing:** `01O` (deployment/migration), `01N` (Windows-Home activation
independence), `CTR-MIGRATION` (SHA-verified transactional runner), schema-freeze rule (SCHEMA-REGISTRY).
**Namespace:** RPH3. Builds only on frozen PH-2 (PLAN-S3 §1).

## 1. Platform footprint

RPH3 is pure enforcement over the frozen PH-2 SQLite runtime — offline, local, no models/GPU/network. Target:
Windows 11 Home **± activation** (no activation gate, `01N`), Python 3.12 + stdlib `sqlite3`. Any *executing*
proof (tool-gateway process-tree termination, Watchdog as a separate OS process) runs in WSL2+Docker
(Decision C) inside the dev/test environment; native-Windows execution of OS-specific process-tree/service
behavior is a recorded known limitation re-verified at release (PH-8), as in PH-1/PH-2.

## 2. ODI-RPH3-01 — persistence boundary (RESOLVED)

**Resolution (frozen-PH-2-safe):** PH-3 authoritative records live in **PH-3-owned stores, separate from the
runtime-state DB**. Consequences:

- **Frozen PH-2 is not modified.** `CMP-ORCH` and `_OrchestratorStateWriter.apply_transition` are consumed
  read-only / as-is; **no additive method, no schema change, no code edit** to `src/factory/orchestrator/**`.
- **R1 preserved.** The runtime-state DB remains Orchestrator-only; **no PH-3 component writes it** (BASE-X).
- **Single-writer discipline per store/domain** (R1-analogue): each PH-3 domain component is the sole writer
  of its own tables, mirroring the PH-2 pattern where CMP-JOURNAL/CMP-LEASE own their sub-schemas.
- **Audit independence:** the audit chain is its own store (CMP-AUDITW sole writer) because tamper-evidence
  requires an append-only chain independent of the records it audits.

This resolution reconciles the Pass-4 spec phrasing "persisted via CMP-ORCH transaction" (now corrected in
`permission-spec`, `approval-spec`, `tool-registry-spec`, and `RPH3-INTEGRATION §2/§5`). The rejected
alternative — additively extending the Orchestrator writer via a Change Contract — was viable but touches a
frozen PH-2 module; the separate-store option is preferred to keep RPH3 fully self-contained and PH-2 frozen.

## 3. Schemas & migrations (SHA-pinned, transactional)

| Store | Migration | Tables | Owner (sole writer) |
|---|---|---|---|
| security-spine | `migrations/security/0001_security_spine.sql` | `permission_grants`, `approval_records`, `approval_queue`, `tool_registry`, `tool_declarations`, `tool_quarantine` | CMP-PERM / CMP-APPROVAL / CMP-TOOLREG (per-table) |
| audit | `migrations/audit/0001_audit_chain.sql` | `audit_records` (append-only, `sequence`, `predecessor_hash`, `record_hash`, optional `signature`) + `BEFORE UPDATE/DELETE` triggers `RAISE(ABORT)` | CMP-AUDITW |

**JSON-Schema contract schemas** (Draft 2020-12, `additionalProperties:false` at authority objects), authored
under `schemas/contracts/`:

| Schema | `$id` | Owner | Contract |
|---|---|---|---|
| permission-grant | `…/contracts/permission-grant/v1.schema.json` | CMP-PERM | CTR-PERMISSION-GRANT |
| approval-record | `…/contracts/approval-record/v1.schema.json` | CMP-APPROVAL | CTR-APPROVAL-RECORD |
| tool-declaration | `…/contracts/tool-declaration/v1.schema.json` | CMP-TOOLREG | CTR-TOOL-DECLARATION |
| audit-chain (record) | `…/contracts/audit-record/v1.schema.json` | CMP-AUDITW | CTR-AUDIT-RECORD |

**Runner:** the PH-1 SHA-256-pinned transactional migration runner (`CTR-MIGRATION`) — one transaction,
`schema_migrations` version recorded only on success; a migration forced to fail mid-apply leaves no partial
schema and no version row. Incompatible schema/state downgrade fails closed (`01O §2.29`). The substrate added
no migration; RPH3 introduces the **first** post-PH-2 migrations (in the two separate PH-3 stores, not
runtime `0004_*` — that runtime slot stays free unless a future PH-3 change genuinely needs the runtime DB).

## 4. Migration ordering & rollback

- **Order:** each PH-3 store's migration is independent (no cross-store FK; task references are by `task_id`
  value, validated against the read-only runtime reader). Within a store, migrations apply in version order.
- **Rollback:** failed activation leaves the prior state active (Section 1 §9 pattern); append-only audit
  migration rollback = "the transaction did not commit." Dev DBs are gitignored/disposable; product stores are
  covered by the PH-7 snapshot manager (Factory-state only; GitHub excluded).
- **Fail-closed:** any migration integrity failure (SHA mismatch, partial apply) blocks startup.

## 5. Deployment / runtime notes

- **Watchdog** deploys as a separately supervised OS process/service (`01M §3.1`); optional Windows
  auto-launch is disabled by default (`01M-AC-32`; rationale `01M-DEC-36`).
- **No secrets/network/telemetry** at PH-3 (offline). The secret/network brokers are PH-5.
- **Installer/updater** (PH-8) package the PH-3 modules + the two new stores' migrations; signed/staged/
  snapshot-protected update applies them transactionally.

## 6. Traceability & registry sync

Schemas/migrations above are reflected in `SCHEMA-REGISTRY.md` (updated this pass): permission-grant /
approval-record / tool-declaration / audit-record contract schemas + the two PH-3 store migrations. No PH-2
migration is altered. Contracts remain v1 in `CONTRACT-REGISTRY`. ODI-RPH3-01 is resolved; no open design
item remains for RPH3 persistence.
