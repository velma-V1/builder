# PH-2 Security, Permissions & Trust-Boundary Plan

**Document ID:** SEC-PH2
**Repository path:** `docs/planning/PH2-SECURITY-TRUST-BOUNDARIES.md`
**Status:** Active — PH-2-scoped security plan (planning Pass 8)
**Authority level:** Plan (subordinate to `01K`, `01E`, `01M`, RISK-REGISTER)
**Owner:** PH-2 planning · **Established:** 2026-07-24
**Governing:** `01K` (tools/permissions/security, tamper-evident audit), `01E` (sandbox/isolation — PH-5),
`01M §1` (writer/supervisor separation), `01R` R1, `02 §6/§7`, PLAN-S2, the six PH-2 component specs,
VEP-PH2, FRR-PH2, RISK-REGISTER.

## 0. Scope & single-authority boundary — what PH-2 does and does NOT secure

Security **for PH-2 only**. PH-2 (Orchestrator queue + state machine) is offline Python + SQLite with **no
sandbox, no container, no WSL2/Docker, no tools, no models, no network, and no approval-token/permission-grant
engine**. Those are built and secured in later phases, and their security architecture is already **owned** by:

| Security domain | Owner (authoritative) | Phase |
|---|---|---|
| Permission-grant + approval-token engine, tool gateway, tool registry, tamper-evident audit chain, Safe Mode, emergency stop | `01K`; CMP-PERM/APPROVAL/TOOLREG/TOOLGW/AUDITW/AUDITV; CTR-PERMISSION-GRANT/APPROVAL-RECORD/TOOL-DECLARATION/AUDIT-RECORD | PH-3 |
| Model role security, prompt-injection defense, tool-call validation | `01J`/`03`; CMP-ROUTER | PH-4 |
| Sandbox isolation, secret broker, network broker, path-safety at execution, container/WSL2/Docker boundaries | `01E`; CMP-SANDBOX/SECRET/NETBROKER; CTR-NETWORK-APPROVAL/SECRET-REF | PH-5 |
| Full path-safety (symlink/junction/ADS/reserved-name/traversal) | PH-1 `PathAuthority` (implemented) + PH-3/5 execution paths | PH-1/3/5 |

**This plan authors PH-2's genuine security surface in full and defers the above to their owners — it does
not author speculative sandbox/token/tool/model/network specs for components PH-2 does not contain (doing so
would redesign PH-3/4/5 ahead of their phases, which this pass forbids).** Deferred, not skipped.

## 1. PH-2 security model

- **Principles:** default-deny · least-privilege · **fail-closed** · **single authoritative writer (R1)** ·
  untrusted-until-validated · **no secret in memory** · tamper-evident append-only journal · integrity-pinned
  schema.
- **Trusted component:** CMP-ORCH — the only component holding a writable DB connection.
- **Untrusted inputs (validated before effect):** every transition request (validated by expected-state +
  legality), every fencing token (validated against the persisted counter + process epoch), every memory
  record (explicit `verify`, structural no-secret constraint).
- **Security boundary (PH-2):** the single-writer invariant + the `mode=ro` reader authorizer + the
  append-only journal triggers + the SHA-256-pinned migration runner. Crossing any fails closed.
- **Trust boundary (PH-2):** the `apply_transition` / `LeaseManager` / `MemoryStore` entry points — inputs are
  data to be judged, never authority.
- **Privilege boundary (PH-2):** structural, not token-based — exactly one process writes; all other readers
  are `mode=ro`. Token-scoped runtime permissions are a **PH-3** concern (`01K`); PH-2 issues no tokens.

## 2. PH-2 protected assets

Standing values: **owner** = CMP-ORCH (sole writer, R1); **authorized writers** = CMP-ORCH transaction only;
**authorized readers** = any component via `mode=ro` + authorizer; **confidentiality** = no secrets stored
(local, non-secret operational state); **deletion** = append-only / approval-required (Dec B), never
auto-deleted; **audit** = the journal is itself the audit trail (`01K §3.2` tamper-evident lineage matures at
PH-3). Only deltas below.

| Asset ID | Asset | Type | Integrity requirement | Threats | Security controls | Verification |
|---|---|---|---|---|---|---|
| ASSET-PH2-DB | runtime-state DB (`tasks`) | SQLite state | only via atomic tx; no second writer | state tampering, direct write | single-writer; `mode=ro` reader + authorizer; `BEGIN IMMEDIATE` | SEC-PH2-01 |
| ASSET-PH2-JOURNAL | `task_state_events` (journal/audit) | append-only log | no UPDATE/DELETE; monotonic sequence | audit/journal tampering | `BEFORE UPDATE/DELETE` triggers `RAISE(ABORT)`; append-only | **SEC-PH2-02** |
| ASSET-PH2-FENCE | `fencing_counters` + `leases` | lock state | tokens strictly increasing, persistent | approval-replay / stale-writer | persistent fencing tokens + process epoch | SEC-PH2-04 |
| ASSET-PH2-MIG | migration integrity (`schema_migrations`) | schema provenance | only pinned-SHA migrations applied | schema tampering | SHA-256 verify before apply; transactional | SEC-PH2-03 |
| ASSET-PH2-MEM | `memory_records` | authoritative records | insert-only correction; no secret field | secret exposure, silent rewrite | `memory_class` DB-constrained; no value field; supersede-by-insert | SEC-PH2-05 |

**No orphan asset:** every asset maps to ≥1 threat, control, and test below.

## 3. Permission / approval / sandbox / tool / model / network — PH-2 disposition

| Framework section | PH-2 disposition |
|---|---|
| Permission levels & capabilities | **Structural only:** one writer (CMP-ORCH), readers `mode=ro`. No runtime permission grants in PH-2. Full model owned by `01K`/CMP-PERM (PH-3). |
| Approval-token architecture | **N/A for PH-2 — no tokens issued.** PH-2 has no approval-gated runtime action; the operator approval is the phase-exit gate only. Token architecture owned by `01K`/CTR-APPROVAL-RECORD/CTR-PERMISSION-GRANT (PH-3). The one PH-2 "non-replayable authority" analog is the **fencing token** (§2 ASSET-PH2-FENCE), which is non-replayable by construction. |
| Sandbox architecture | **N/A for PH-2 — no sandbox.** Owned by `01E`/CMP-SANDBOX (PH-5). |
| Path-safety architecture | PH-2 touches only fixed internal paths: the config/operator-supplied DB path and the pinned migration files. **No model-/repo-supplied paths, no archive extraction, no symlink following of untrusted input.** Full path-safety owned by PH-1 `PathAuthority` (implemented) + PH-3/5 execution. |
| Tool security architecture | **N/A for PH-2 — no tools invoked.** Owned by `01K`/CMP-TOOLREG/TOOLGW (PH-3). |
| Model security architecture | **N/A for PH-2 — no models invoked.** Owned by `01J`/CMP-ROUTER (PH-4). |
| Network security architecture | **Offline; no network.** PH-2 makes no network access. Owned by `01E`/CMP-NETBROKER (PH-5). |

## 4. PH-2 threat model (credible threats against PH-2 assets)

Standing: **actor** = a buggy/compromised in-process component or a malformed request (PH-2 has no external
attack surface — offline, no network/models/tools); **residual risk** = low given fail-closed controls;
**acceptance authority** = operator at the phase-exit gate (`01G §3.4` for any residual). Only deltas below.

| Threat ID | Threat | Target asset | Attack path | Prevention (control) | Detection | Test | Risk link |
|---|---|---|---|---|---|---|---|
| THR-PH2-01 | state tampering / direct write bypassing the sole writer | ASSET-PH2-DB | a component opens a writable connection and mutates state | only CMP-ORCH holds a writable conn; readers `mode=ro` + authorizer denies writes | authorizer raises | SEC-PH2-01 | RISK-ARCH-02 |
| THR-PH2-02 | audit/journal tampering (UPDATE/DELETE events) | ASSET-PH2-JOURNAL | code attempts to rewrite/delete an event row | `BEFORE UPDATE/DELETE` triggers `RAISE(ABORT)` | trigger abort | **SEC-PH2-02 (added this pass)** | RISK-ARCH-02, RISK-VERIF-01 |
| THR-PH2-03 | schema tampering (swap/modify a migration) | ASSET-PH2-MIG | altered migration file applied | SHA-256 pinned verify before apply; transactional | SHA mismatch → refuse | SEC-PH2-03 | RISK-DEP-01 |
| THR-PH2-04 | approval-replay / stale-writer (fencing) | ASSET-PH2-FENCE | a delayed former lease owner writes after supersession | persistent increasing tokens + process-epoch invalidation | `validate_token` False | SEC-PH2-04 | RISK-REC-02 |
| THR-PH2-05 | secret exposure via memory | ASSET-PH2-MEM | a secret placed in a memory record | `memory_class` constrained; no free-form value field (structural) | field-set test fails at build | SEC-PH2-05 | RISK-DATA-02 |
| THR-PH2-06 | state corruption masquerading as valid | ASSET-PH2-DB/JOURNAL | stored `current_state` ≠ replayed history | reconciliation quarantine (`01M §5`) | replay mismatch → `QUARANTINED` | SEC-PH2-06 | RISK-REC-02 |
| THR-PH2-07 | contract tampering (malformed/illegal transition) | ASSET-PH2-DB | illegal or expected-state-mismatched request | legality + expected-state checks; fail closed + `accepted=0` audit event | audit event recorded | SEC-PH2-07 | RISK-ARCH-01 |

**Deferred threats (owned by risk register / later phases, NOT PH-2 attack surface):** sandbox/container
escape, prompt/tool injection, supply-chain/package tampering, credential/approval-token theft (no tokens),
network exfiltration, malicious model output — PH-3/4/5 per RISK-ISO/SEC/MODEL/DOCKER/WIN. **No unmitigated
critical PH-2 threat.**

## 5. PH-2 security tests

Fields: threat covered · initial state · action · expected allow/deny · expected audit · expected final state ·
regression. Each maps to a PLAN-S2 test file. Standing: env ENV-DEV; regression = re-run in Task 2.6 + on any
change.

| Sec Test ID | Threat | File | Action → expected result |
|---|---|---|---|
| SEC-PH2-01 | THR-PH2-01 | `security/test_read_only_state_access.py` | `mode=ro` reader attempts INSERT/UPDATE/DELETE/CREATE/DROP/ALTER → **deny** (authorizer raises) |
| SEC-PH2-02 | THR-PH2-02 | `security/test_read_only_state_access.py` (added assertion) | direct UPDATE/DELETE on `task_state_events` (even via writable conn) → **deny** (trigger `RAISE(ABORT)`) |
| SEC-PH2-03 | THR-PH2-03 | `unit/test_runtime_state_store.py` | apply a migration whose bytes don't match the pinned SHA-256 → **deny** (refuse, no version row) |
| SEC-PH2-04 | THR-PH2-04 | `unit/test_fencing.py` | write with superseded / prior-epoch token → **deny** (`validate_token` False) |
| SEC-PH2-05 | THR-PH2-05 | `unit/test_memory_records.py` | `MemoryRecord` field-set asserted exactly (no value field) → structural **deny** of secret-bearing field |
| SEC-PH2-06 | THR-PH2-06 | `unit/test_journal_reconciliation.py` | stored state ≠ replayed history → **quarantine** (`QUARANTINED`) |
| SEC-PH2-07 | THR-PH2-07 | `unit/test_transition_policy.py` + `unit/test_runtime_state_store.py` | illegal / expected-state-mismatch transition → **deny** + `accepted=0` audit event |

## 6. Security traceability

**Asset → Threat → Control → Test → Evidence:** each §2 asset row → its threat(s) in §4 → the named control →
the §5 test → ETM row (EV-PH2-ETM, VEP-PH2 §4). Complete for all five assets.

**Boundary → Control → Verification → Recovery:** single-writer boundary → `mode=ro`+authorizer → SEC-PH2-01 →
n/a (deny, no state change); journal boundary → append-only triggers → SEC-PH2-02 → reconciliation
(REC-PH2-JOURNAL); schema boundary → SHA-pin → SEC-PH2-03 → RB-PH2-MIG; fencing boundary → token+epoch →
SEC-PH2-04 → REC-PH2-LEASE.

**Security-failure → Rollback → Evidence:** a detected security violation is a **deny**, not a state change —
so no rollback is needed for THR-PH2-01/02/04/05/07 (the write never happens); THR-PH2-03 → RB-PH2-MIG;
THR-PH2-06 → quarantine (FRR-PH2 F-PH2-04). Every deny is evidenced by the test's assertion + (for
transitions) the `accepted=0` audit event.

**Permission/Approval/Sandbox → Component/Task/Tool/Model:** N/A for PH-2 (no tokens/tools/models/sandbox) —
owned by PH-3/4/5 (§0/§3). No orphan permission (the only PH-2 "permission" is the structural single-writer,
owned by CMP-ORCH).

## 7. Repair applied this pass (repair-first rule)

**Finding:** the append-only journal triggers (control for THR-PH2-02, ASSET-PH2-JOURNAL) were specified in
the Task 2.2 migration DDL but had **no explicit test** in PLAN-S2 / VEP-PH2 — i.e. a security control without
verification, which this pass forbids. **Deterministic repair:** added security test **SEC-PH2-02** (direct
UPDATE/DELETE on `task_state_events` must raise) to `PLAN-S2` Task 2.2 and to `VEP-PH2` §2/§3, mapped to
THR-PH2-02. **Recorded** as `REGR-0002` in `REGRESSION-REGISTER.md` with an **OPEN** regression flag (cleared
when the test is implemented and passes during PH-2 implementation). No other inconsistency found.

## 8. Consistency review (this pass)

Cross-checked against `01K` (tamper-evident audit, least-privilege, default-deny — PH-2 honors via
single-writer + `mode=ro` + append-only + no-tokens-needed), `01E`/`01M §1` (sandbox + writer/supervisor
separation — PH-2 builds no sandbox and no Watchdog, correctly deferred), the component specs
(`security_requirements` fields align), VEP-PH2 (SEC tests are the security lens on the same files), FRR-PH2
(deny-not-rollback consistent with the failure plan), RISK-REGISTER (THR-PH2-01..07 map to existing risk
rows; no new risk beyond the register): **one repair applied (§7); after it, no inconsistency remains; no
security weakening; fail-closed throughout.**

## 9. Update rules

Regenerated if PLAN-S2, the component specs, `01K`, `01E`, or `01M` change. Actual security-test results are
produced at implementation time (Task 2.6) — not pre-filled. Superseded by pointer, never deleted.
