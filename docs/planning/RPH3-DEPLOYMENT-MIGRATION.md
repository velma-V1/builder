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

Every data structure required by **XSC-RPH3** (cross-store protocol) and **WIR-RPH3** (Watchdog receiver) is
inventoried here. The security-spine store carries the domain records **and** the per-domain **operation-intent**
tables + the WIR **intervention journal**; the audit store enforces `UNIQUE(op_key, record_kind)` (an
operation may carry an `INTENT` and a `COMPLETION` audit record — see XSC-RPH3 §2 cardinality).

| Store | Migration | Tables | Owner (sole writer) |
|---|---|---|---|
| security-spine | `migrations/security/0001_security_spine.sql` | domain records: `permission_grants`, `approval_records`, `approval_queue`, `tool_registry`, `tool_declarations`, `tool_quarantine`; **operation-intent** tables: `permission_intents`, `approval_intents`, `tool_registry_intents`; **receiver journal**: `intervention_journal` | per-table single writer: CMP-PERM (`permission_*`), CMP-APPROVAL (`approval_*`), CMP-TOOLREG (`tool_*`), WIR (`intervention_journal`) |
| audit | `migrations/audit/0001_audit_chain.sql` | `audit_records` (append-only, `sequence`, `predecessor_hash`, `record_hash`, optional `signature`, `op_key`, `record_kind` CHECK in (`INTENT`,`COMPLETION`)) + **`UNIQUE(op_key, record_kind)`** (≤1 INTENT + ≤1 COMPLETION per op) + `BEFORE UPDATE/DELETE` triggers `RAISE(ABORT)` | CMP-AUDITW |

### 3.1 Operation-intent / journal table shape (XSC-RPH3 · WIR-RPH3)

`permission_intents` / `approval_intents` / `tool_registry_intents` / `intervention_journal` share this shape
(each owned by its domain's sole writer):

| Column | Type / rule |
|---|---|
| `op_key` | TEXT **PRIMARY KEY**, immutable (= XSC `K`); the join key across all three stores |
| `operation_class` | INTEGER CHECK in (1,2,3) (XSC class) |
| `domain` | TEXT (permission / approval / tool / watchdog) |
| `target_ref` | TEXT (one task_id / grant_id / service_id / resource_ref; single-target only) |
| `requested_action` | TEXT (the verb, e.g. `issue_grant`, `PAUSE_TASK`, `RESTART_SERVICE`) |
| `status` | TEXT CHECK in (`PENDING`,`COMMITTED`,`ABORTED`,`UNCERTAIN`,`QUARANTINED`) |
| `reconciliation_state` | TEXT CHECK in (`NONE`,`ROLL_FORWARD`,`ROLL_BACK`,`QUARANTINE`) |
| `audit_seq` | INTEGER NULL — FK-by-value to `audit_records.sequence` (set at completion audit) |
| `failure_code` | TEXT NULL — failure / uncertainty code on ABORTED/UNCERTAIN |
| `quarantine_state` | TEXT NULL — set for Class-3 UNCERTAIN→QUARANTINED subjects |
| `created_ts` / `updated_ts` / `completed_ts` | INTEGER (monotonic) — created, last transition, completion |

**Indexes:** `INDEX(status)` (startup reconciliation scan of non-terminal rows), `INDEX(operation_class,status)`
(per-class reconciliation), `INDEX(target_ref)` (affected-work lookup, INV-3). Audit store:
**`UNIQUE(op_key, record_kind)`** (the exactly-once / at-most-once guard — permits one `INTENT` + one
`COMPLETION` per `K`, rejects duplicates of either) + `INDEX(op_key)` (join) + existing `sequence` PK.
**Class-3 rule:** a `COMPLETION` insert is rejected unless an `INTENT` for the same `op_key` already exists
(completion cannot precede intent).

**Ownership & sole-writer rules.** Each `*_intents` table is written **only** by its owning domain writer
(same authorizer partition as the domain records, DEP-RPH3 §4A); `intervention_journal` is written **only** by
the WIR. No cross-domain writes; consumers read via `mode=ro`. The audit store is written **only** by
CMP-AUDITW.

**Retention & cleanup.** `COMMITTED` intents are superseded by the committed domain record + the audit record;
they may be pruned after a bounded horizon (default: retention-policy window) — pruning an intent never
touches its audit record. `ABORTED` intents are retained for a bounded audit window then pruned. `QUARANTINED`
intents are **held** (not pruned) until operator/approval-gated recovery clears them. **Audit records are
never pruned** by this process (append-only; governed by `CTR-RETENTION-POLICY`, PH-7).

**Crash-recovery & migration order.** Both migrations apply under the PH-1 SHA-256-pinned transactional runner
(§ below), each in one transaction (no partial schema). At startup, the domain writers run XSC-RPH3 §5
reconciliation over the intent tables **before serving any request**; the audit chain is verified
(CMP-AUDITV) first. Migration order within the security-spine store: domain + intent + journal tables are
created in the single `0001_security_spine.sql` transaction (no inter-table ordering hazard); the audit store
migration is independent (no cross-store FK — the link is `op_key` by value).

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

## 4A. Security-spine store ownership enforcement (technical)

The security-spine store is one SQLite file shared by three domains, but write authority is **partitioned by
table with exactly one writer per domain** and enforced structurally (correction #7). This is the R1-analogue
for the PH-3 store.

**Per-domain private writer services (no exported raw connections).** Each domain's writable SQLite connection
is encapsulated inside a private writer/repository module and is **never returned or exported** (mirrors PH-2's
un-exported `_OrchestratorStateWriter`). Consumers receive typed **read-only** query methods only.

| Domain writer | Permitted write tables | Exposed to consumers |
|---|---|---|
| CMP-PERM (`permission._grant_writer`) | `permission_grants`, `permission_intents` | read-only `get_grant`, `is_valid` |
| CMP-APPROVAL (`approval._record_writer`) | `approval_records`, `approval_queue`, `approval_intents` | read-only `get_record`, `is_valid` |
| CMP-TOOLREG (`tools._registry_writer`) | `tool_registry`, `tool_declarations`, `tool_quarantine`, `tool_registry_intents` | read-only `lookup` |
| WIR (`watchdog._receiver_journal`) | `intervention_journal` | read-only reconciliation reads |

**SQLite authorizer enforcement (where practical).** Every connection installs `sqlite3` `set_authorizer`:
- a domain **writer** connection **denies** `INSERT/UPDATE/DELETE` on any table outside its permitted set
  (e.g. CMP-PERM's writer cannot mutate `approval_*` or `tool_*`);
- a **consumer/read** connection is opened `mode=ro` and additionally denies all write ops
  (reuses the PH-1/PH-2 `_reader_authorizer` pattern proven in `tests/orchestrator/security/`);
- `append-only` audit tables carry `BEFORE UPDATE/DELETE` triggers `RAISE(ABORT)` (audit store).

**Transaction & lock ordering.** One operation writes **exactly one domain's tables in one short
`BEGIN IMMEDIATE` transaction**; a flow needing two domains is decomposed into per-domain committed steps
coordinated by XSC-RPH3 idempotency (never a single cross-domain write transaction), so no component ever
holds two domain write locks at once. When ordering across stores is required, the fixed order is
**security-spine domain write → audit append (commit point) → domain commit** (XSC-RPH3 §3); this global order
prevents deadlock and satisfies audit-before-success.

**Cross-domain read rules.** A component MAY read another domain's tables through that domain's read-only
query API or a `mode=ro` connection (e.g. CMP-TOOLGW reads grants + approvals + registry to authorize a call);
it MUST NOT obtain a writable handle to another domain. Reads never bypass the authorizer.

**Structural tests (prove isolation).** (a) each domain writer connection is denied writes to every other
domain's tables (authorizer); (b) a consumer connection cannot write any table; (c) no domain module exports a
writable connection object (introspection/structural test); (d) audit tables reject `UPDATE`/`DELETE`;
(e) a cross-domain write attempted through a read API raises. These are `security` category tests feeding
`SEC-RPH3-*` and VR-RPH3-08/09/14.

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
