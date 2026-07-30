# PH-2 Deployment & Migration Plan

**Document ID:** DEP-PH2
**Repository path:** `docs/planning/PH2-DEPLOYMENT-MIGRATION.md`
**Status:** Active — PH-2-scoped deployment/migration plan (planning Pass 9)
**Authority level:** Plan (subordinate to `01O`, `01N`, `docs/release/*`)
**Owner:** PH-2 planning · **Established:** 2026-07-24
**Governing:** `01O §2.18-19/§2.29` (versioned state, transactional migrations, incompatible-downgrade
fails closed), `docs/release/UPDATE-AND-MIGRATION-PLAN.md §1` (transactional SHA-verified runner), `01N`
(activation independence), PLAN-S2, VEP-PH2, FRR-PH2, SEC-PH2, the PH-1 migration-runner precedent
(`migrations/contracts/0001_activation_store.sql`).

## 0. Scope & single-authority boundary — what PH-2 deploys and does NOT

Deployment/migration **for PH-2 only**. PH-2 (Orchestrator queue + state machine) ships **no installer, no
package, no release artifact, no update mechanism, no backup subsystem, and no maintenance tasks** — those are
**PH-8**, already owned by the authoritative planning records below. PH-2's **only** deployment surface is its
**runtime-state schema migrations** (`migrations/runtime/0001..0003`), consumed by the PH-8 update/migration
architecture.

| Deployment domain | Owner (authoritative) | Phase |
|---|---|---|
| Installer, prerequisite detection (WSL2/Docker/GPU), support profile, activation independence | `docs/release/INSTALLER-PLAN.md`, `01O §2.2-13/§3.1-3.3`, `01N` | PH-8 |
| Packaging, SBOM, signing, reproducible build, release channels/gates, release verdict | `docs/release/RELEASE-PLAN.md`, `01O §2.31-42/§3.9` | PH-8 |
| Update discovery/approval/staging, executable rollback window, signature/trust, pre-update snapshot | `docs/release/UPDATE-AND-MIGRATION-PLAN.md`, `01O §2.18-30` | PH-8 |
| Backup/restore/retention, recovery snapshots | `01M §3.9`, `docs/release/ROLLBACK-PLAN.md`, `01C` | PH-7/PH-8 |
| Maintenance (routine/security/dependency/log/audit) | `01C`, `01H`, `01O` | PH-8 / post-core |
| Repository intelligence / graph indexes (deployment observability) | `01P` | PH-8 |

**This plan authors PH-2's migration slice in full and defers the above to their owners — authoring a full
installer/packaging/release/backup/maintenance architecture now would plan PH-8 eight phases early against
components that do not exist, which this pass forbids.** Deferred, not skipped.

## 1. PH-2 platform baseline (minimal footprint)

| Requirement | PH-2 value |
|---|---|
| Development OS | offline dev environment (this session: Linux; target dev path Windows 11 Home ± activation, `01N`) |
| Release OS | N/A for PH-2 (no release; PH-8 owns the Windows 11 Home release baseline) |
| Windows activation | irrelevant to PH-2 — no activation query anywhere (`01N`); PH-2 has no Windows-specific code |
| WSL2 / Docker / container runtime | **not required by PH-2** (offline Python + SQLite); bind at PH-5 |
| GPU / driver / model runtime | **not required by PH-2** (no models); Ollama binds at PH-4 |
| Python runtime | 3.12 via `uv` (PH-1 pins; PH-2 adds none) |
| Node / Tauri / React / WebView | **not required by PH-2** (no UI); Dashboard is PH-S/PH-8 |
| Network | **offline — none** (`PD §13`); PH-2 makes no network access |
| Storage / filesystem | < 50 MB repo; one SQLite DB file (gitignored, disposable) |
| Signing | N/A (PH-2 produces no release artifact) |
| Logging / audit | the append-only journal (`task_state_events`) is PH-2's audit surface (tamper-evident lineage matures at PH-3) |
| Backup / recovery | journal-authoritative + git commits (FRR-PH2); Factory recovery snapshots are PH-7 |

**Required deps:** PyYAML/jsonschema/rfc8785 (PH-1) + stdlib `sqlite3`; PH-2 adds none. **Optional deps:**
none. **Forbidden for PH-2:** network, cloud, GPU, Docker/WSL2, models, tools, installer (all bind later).
**Internet-required steps:** none (offline). **Operator-approval steps:** the PH-2 exit gate only (no
install/update approvals in PH-2).

## 2. PH-2 migration architecture (the genuine PH-2 deployment deliverable)

PH-2 adds three runtime-state migrations, each following the **PH-1 runner pattern** (SHA-256 verified before
apply · executed in one transaction · version row recorded only after success — `01O §2.19`,
`UPDATE-AND-MIGRATION-PLAN §1`). All three are **initial-creation, forward-only** migrations (no data
transformation, no destructive operation, no downgrade path in v1).

Standing values: **owned data** = the tables the migration creates; **preconditions** = prior migration
version present; **compatibility** = additive (each later migration only ADDs tables, never alters 0001);
**transformation** = none (create-only); **data/evidence/audit preservation** = trivially preserved (nothing
pre-exists; `task_state_events` created by 0001 is append-only thereafter); **backup/checkpoint** = the git
commit + (at runtime) the pre-update snapshot owned by PH-8; **dry-run** = re-runnable on a scratch DB;
**approval** = PH-2 exit gate; **rollback** = transactional (a failed migration leaves no partial schema and
no version row); **forward-recovery** = re-run the SHA-verified migration; **completion** = version row
written. Only deltas below.

| Migration ID | File | Src→Tgt | Owned data | Verification |
|---|---|---|---|---|
| MIG-PH2-0001 | `migrations/runtime/0001_state.sql` | 0→1 | `schema_migrations`, `tasks`, `task_state_events` (+ append-only triggers) | SEC-PH2-02/03; MIG-runner test (REGR-0003) |
| MIG-PH2-0002 | `migrations/runtime/0002_leases.sql` | 1→2 | `fencing_counters`, `leases` | SEC-PH2-03/04 |
| MIG-PH2-0003 | `migrations/runtime/0003_memory.sql` | 2→3 | `memory_records` | SEC-PH2-03/05 |

### Migration safety rules (PH-2, verified)

- **No destructive migration without explicit authority:** all three are create-only; no `DROP`/`ALTER`/data
  deletion. (Dec B: no auto-delete anywhere.)
- **No incompatible downgrade:** v1 defines no downgrade; a future incompatible downgrade must fail closed
  (`01O §2.29`) — enforced when PH-8 adds the update path, not needed in PH-2.
- **No schema/contract mismatch:** schema identity is the pinned SHA-256 + version number; a mismatched
  migration file is refused before apply (SEC-PH2-03).
- **No broken audit chain / evidence traceability:** `0001` creates the append-only `task_state_events`;
  `0002`/`0003` only add tables, never touch it — the journal is never rewritten by a migration.
- **Migration path-safety:** migration files are fixed, in-repo, pinned by SHA — **no user-/model-supplied
  path, no archive extraction, no traversal surface** (contrast PH-8 installer/update path-safety, owned
  there).

## 3. PH-2 configuration footprint

PH-2's only configuration is: the **runtime DB path** (operator/config-supplied at construction, not
model-supplied) and the **pinned migration SHA-256 constants** (code constants, not runtime config). **No
environment variables, no insecure defaults, no configuration capable of bypassing security/approval/
verification/audit** (PH-2 has no such config surface). The full Configuration Registry (PAL gap **G-01**)
is owned by PH-4/PH-8; PH-2 introduces no entries requiring it.

## 4. Deployment/packaging/installer/update/release/maintenance/backup — PH-2 disposition

| Framework section | PH-2 disposition |
|---|---|
| Deployment types (clean/in-place/repair/side-by-side/uninstall/offline) | **N/A for PH-2** — no deployable artifact; owned by INSTALLER-PLAN/RELEASE-PLAN (PH-8) |
| Packaging (SBOM/signing/reproducible build/manifests) | **N/A for PH-2** — no package; owned by RELEASE-PLAN §3 (PH-8) |
| Installer steps (prereq/WSL2/Docker/GPU/storage/config-gen) | **N/A for PH-2**; owned by INSTALLER-PLAN (PH-8) |
| Update architecture (discovery/staging/rollback window/signature) | **N/A for PH-2**; owned by UPDATE-AND-MIGRATION-PLAN (PH-8). PH-2's migrations are *consumed by* this at PH-8. |
| Release types/gates/verdict | **N/A for PH-2** — PH-2 has a *phase-exit* gate (PROM-PH2, VEP-PH2 §5), not a *release*; owned by RELEASE-PLAN §6 (PH-8) |
| Maintenance tasks | **N/A for PH-2**; owned by `01C`/`01H` (PH-8/post-core) |
| Backup/restore/retention | **N/A for PH-2** beyond git + journal; owned by `01M §3.9`/ROLLBACK-PLAN (PH-7/8) |

**Linkage PH-2 → PH-8:** PH-8's update/migration architecture (UPDATE-AND-MIGRATION-PLAN §1) consumes the
`migrations/runtime/*` produced here; PH-2 must therefore emit migrations that satisfy the transactional +
SHA-verified + forward-only + version-on-success rules — which §2 specifies and §5 verifies.

## 5. PH-2 migration tests & traceability

| Migration behavior | Test | Maps to |
|---|---|---|
| SHA-mismatch migration refused | SEC-PH2-03 (`test_runtime_state_store`) | THR-PH2-03, `01O §2.19` |
| append-only journal survives migrations | SEC-PH2-02 (`test_read_only_state_access`) | THR-PH2-02 |
| **runner records version only on success; failed migration leaves no partial schema (transactional)** | **MIG-runner test (REGR-0003, added this pass) in `test_runtime_state_store`** | REQ-PH2-09, `01O §2.19` |
| all migrations apply in order to a clean DB | T-PH2-SYS1 (`verify_section2` clean-env run) | REQ-PH2-09 |

**Traceability:** Migration → data owner (§2 table) → verification (§5 test) → evidence (EV-PH2-ETM);
Platform requirement → deployment: PH-2 requires only Python+SQLite → no deployment step (offline);
Package → component/task: **none for PH-2** (no package). No orphan migration (each maps to a test); no
migration without verification (after REGR-0003); no update without rollback planning (PH-2 has no update;
its migrations are transactionally reversible); no release without gates (PH-2 has no release).

## 6. Repair applied this pass (repair-first rule)

**Finding:** PH-2 defines three migrations but the transactional-safety behavior of the runner (record
version only after success; a failed migration leaves no partial schema and no version row — `01O §2.19`)
had **no explicit test** — "no migration without verification." **Deterministic repair:** added a migration-
runner test to `PLAN-S2` Task 2.2 and `VEP-PH2` §2/§3, recorded as `REGR-0003` (OPEN) in
`REGRESSION-REGISTER.md`. No other inconsistency found.

## 7. Consistency review (this pass)

Cross-checked against `01O §2.18-19/§2.29` (versioned/transactional/downgrade-fail-closed — PH-2 conforms),
`01N` (activation independence — PH-2 queries no activation), INSTALLER-PLAN/RELEASE-PLAN/UPDATE-AND-MIGRATION-
PLAN (PH-8 owners — PH-2 defers, produces only migrations they consume), PLAN-S2 (migration files + runner),
VEP-PH2 (REQ-PH2-09), SEC-PH2 (SEC-PH2-02/03), FRR-PH2 (RB-PH2-MIG transactional rollback), SCHEMA-REGISTRY
(runtime migrations owned by PH-2): **one repair applied (§6); after it, no inconsistency remains; no platform
requirement conflicts with authority; no security/isolation weakening.**

## 8. Update rules

Regenerated if PLAN-S2, the schema registry, `01O`, or the `docs/release/*` owners change. Actual migration
results are produced at implementation time (Task 2.6) — not pre-filled. Superseded by pointer, never deleted.
