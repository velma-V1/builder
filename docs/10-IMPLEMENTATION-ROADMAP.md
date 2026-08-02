# Factory Master Implementation Roadmap

**Status:** Approved planning order (single plan of record for building Factory)
**Recorded:** July 24, 2026
**Governing inputs:** `05-BUILD-PLAN-MAP` (build order), `01 §10` (eight sections), `01A §12` / `05` (shell milestone), `01B` (self-hosting stages), `docs/01R` (resolutions R1–R5 + decisions A–C), `HANDOFF §7`.
**In force:** R1 (Orchestrator = sole authoritative writer; Watchdog = read-only supervisor), R2 (workstreams are the default unit), R3 (improvements approval-only), Decisions A (autonomy), B (deletion approval-required), C (WSL2+Docker only).

Product implementation has not started. This roadmap orders the phases, binds each to its governing Stages/supplements, defines inter-phase gates, and allocates workstreams. Task-level decomposition lives in each phase plan and its task specifications.

## 1. Phases

`phase ≡ build Section` (or the Shell milestone). Nine phases:

| Phase ID | Name (build Section) | Governing supplements |
|---|---|---|
| **PH-1** | Requirements & Contracts (S1) | Section 1 spec/plan; `01 §14–17`; `01R` R5 |
| **PH-S** | Minimum Builder Shell (milestone) | `01A §12`; `06 §11`; `01L`; `01B` St.0 |
| **PH-2** | Orchestrator: Task Queue & State Machine (S2) | `01L §3.1`; `01D §3.1`; `02 §4/§6/§7`; `01R` R1 |
| **PH-3** | Watchdog, Permissions, Approval, Audit & Tools (S3) | `01M`; `01K`; `01 §3/§11`; `01R` R1, Dec A/B |
| **PH-4** | Model & Coding-Tool Routing & Quotas (S4) | `01J`; `03`; `01A`; `06 §6–7` |
| **PH-5** | Git, Worktree & Sandbox Isolation (S5) | `01I`; `01E`; `04`; `01R` Dec C |
| **PH-6** | Three Parallel Major-Stage Workstreams (S6) | `01D`; `01C §13`; `01L §3.1`; `01R` R2 |
| **PH-7** | Testing, Evidence, Integration & Recovery (S7) | `01G`; `01C`; `01M`; `01D §3.8`; `04` |
| **PH-8** | Complete Dashboard, Packaging & Installation (S8) | `01L`; `01P`; `01O`; `01N`; `PD §14–15` |
| *(deferred)* | Self-improvement (`01C/01H`, R3), Research (`01Q`) | post-core-v1 |

## 2. Phase objectives

- **PH-1** — authoritative contract/schema substrate every later subsystem consumes.
- **PH-S** — early usable Builder shell (frame + explorer + Monaco + terminal + Ollama health + Aider bridge) so development can migrate inside (`01B`).
- **PH-2** — the deterministic **Orchestrator**: sole authoritative writer, task/workstream state machine, durable journal, fenced leases.
- **PH-3** — the independent **Watchdog** supervisor + permission/approval/audit/tool-gateway enforcement (security spine); autonomy-envelope enforcement (Decision A).
- **Phase 3B implementation note (2026-08-02)** — independent worker verification, durable evidence
  and manifests, explicit approval-bound promotion/rollback, restart reconciliation, lifecycle API,
  and required dashboard controls are implemented on draft PR #18. Linux verification passes for
  implementation commit `475c528`, but native-Windows launcher and junction checks have not run at
  the current head. Independent review has unresolved merge-blocking findings, so Phase 3B is not
  verified, exited, or merge-ready. This is not a release or promotion decision.
- **PH-4** — local-first deterministic routing over Ollama/Aider with resource scheduling and no silent substitution.
- **PH-5** — repeatable, recoverable isolation: task branches/worktrees, non-root WSL2+Docker sandboxes (Windows-native excluded, Decision C), brokers, quarantined staging.
- **PH-6** — up to three concurrent full-lifecycle workstreams with conflict detection and integration gates.
- **PH-7** — independent verification (ETM/verdicts), serialized integration, evidence/promotion, recovery/snapshots.
- **PH-8** — complete Dashboard + graphs, packaging, guided installer/updater, stable release verification on Windows 11 Home (±activation).

## 3. Entry gates
A phase may start only when (a) its blocking prerequisites are exited with evidence; (b) its design spec + phase plan are `APPROVED`; (c) its input contracts/schemas are activated; (d) the R1–R5 amendments are recorded (done, `01R`).

## 4. Exit gates
A phase exits only when every acceptance criterion in its governing supplement(s) passes with a complete `01G` Evidence Traceability Manifest chain, verdict `PASS`, evidence package finalized, no unresolved critical/high defect, and the operator approves the phase-exit promotion. Post-implementation-start verification changes obey `01G §3.2`.

## 5. Blocking prerequisites
`PH-1 → {PH-S, PH-2}` · `PH-2 → PH-3` · `PH-3 → {PH-4, PH-5}` · `{PH-3,PH-4,PH-5} → PH-6` · `{PH-5,PH-6} → PH-7` · `{all} → PH-8`. **PH-S** additionally needs *minimal slices* of file-op (PH-3/5), Ollama+Aider adapters (PH-4), terminal (PH-3), Dashboard frame (PH-8), built as a thin vertical slice during `01B` Stage 0 bootstrap.

## 6. Component dependencies (key edges)
`Orchestrator ← contract system, journal, leases`. `Watchdog ← Orchestrator (observes, separate process), snapshot, journal`. `permission/approval/audit ← Orchestrator`. `router ← tool gateway, Resource Scheduler, Ollama/Aider adapters`. `sandbox ← Resource Scheduler, secret broker, network broker, cache, Git manager`. `workstream/lane engine ← state machine, Git manager, sandbox, router`. `Promotion Service ← verification engine, evidence store, Git manager, approval`. `ETM ← verification engine, evidence store, model-exec records`. `Dashboard/graph/repo-index ← all authoritative records (read-only)`. (Full graph → `docs/planning/DEPENDENCY-MAP.md`.)

## 7. Contract dependencies
`ENVELOPE → {7 families}`; `{TASK,OWNERSHIP,PERMISSION,EVIDENCE} → TASK-WS-SM`; `CANONICAL → ACTIVATION-STORE → RUNTIME-STATE-DB`; `EVIDENCE → ETM → EVIDENCE-PACKAGE → PROMOTION-PACKAGE`; `VERDICT` gates promotion; `BASELINE-MANIFEST → PROMOTION-PACKAGE`; `AUDIT-RECORD` underlies all privileged actions. (Full → `docs/planning/CONTRACT-REGISTRY.md`.)

## 8. Critical path
**PH-1 → PH-2 → PH-3 → PH-5 → PH-6 → PH-7 → PH-8 (stable release).** PH-4 is off the longest chain (parallel to PH-5 after PH-3, converging at PH-6). PH-S branches from PH-1 early and is not on the critical path but is a required self-hosting enabler.

## 9. Parallel-safe work (≤3 workstreams; `01D §3.4` independence)
- After PH-1 + PH-3: **PH-4 ∥ PH-5** are independent (disjoint components/owned paths) → two workstreams; **PH-S** thin slice may run as the third.
- Within a phase: PH-1 Task-1 seven schemas; PH-4 Ollama vs Aider adapters — parallel-safe once shared interfaces are frozen.
- Parallelism is admitted only after `docs/planning/WORKSTREAM-MAP.md` proves independence (not path-disjointness alone).

## 10. Serialized work
PH-1 internal Tasks 1→5; the runtime-state DB schema + state machine (PH-2); the Promotion Service and any protected-ref change (PH-7); all shared-contract/schema/migration changes; integration of multiple workstreams (PH-6/7 coordinator, `01 §8`, `01D §3.8`).

## 11. Integration points
IP-1 (PH-S) Dashboard↔file-op↔Ollama↔Aider bootstrap · IP-2 (PH-4/5 join) routed bounded Aider-on-Ollama task · IP-3 (PH-6) three-workstream demonstration + coordinator · IP-4 (PH-7) serialized integration + cross-component regression + reconciliation · IP-5 (PH-8) clean-machine install without Codex/VS Code/OpenHands/hosted.

## 12. Verification milestones
Per-phase acceptance pass with ETM; VM-1 Section 1 `verify_section1` (`01G` verdicts); VM-2 PH-3 security spine; VM-3 PH-4 no-silent-substitution + local-only; VM-4 PH-6 three-workstream integration; VM-5 PH-7 verification engine + ETM + evidence-complete promotion; VM-6 PH-8 release verification.

## 13. Recovery milestones
RM-1 (PH-2) journal + startup reconciliation + fenced leases · RM-2 (PH-5) sandbox-boundary-failure recovery + destroy/quarantine · RM-3 (PH-7) candidate-tested snapshot, scope-drift recovery, repeated-failure quarantine, drills · RM-4 (PH-8) release failure-path simulations.

## 14. Release & self-hosting milestones
`01B` cutovers: after PH-S+file-op → editing inside (St.1); after PH-3 terminal/tests → commands/tests inside (St.2); after PH-4 → AI coding inside (St.3); after PH-5 → git/review/recovery inside (St.4); after PH-7 → Factory self-hosting (St.5). Release: PH-8 produces the release candidate + `01O §6` verdict; stable requires zero unresolved critical/high defects and the VELMA validation build achievable (`PD §24`).

## 15. Operator approvals
(1) R1–R5 recorded (done, `01R`); (2) PH-1 schema freeze; (3) each phase-exit promotion; (4) each self-hosting cutover (St.1–5); (5) prerequisite/model installs (`01O §2.4/§2.16`); (6) any merge to `main` / release (`01 §12`, `01O`); (7) any protected-boundary contract change (`01 §17`). Improvements never auto-apply (R3). One decision at a time, recorded before reliance (`05` drift rules).

## 16. Completion definition
Factory is complete when all eight sections + the Shell milestone pass their acceptance criteria with finalized evidence and `PASS` verdicts; the self-hosting transition reaches `01B` Stage 5/§6; a stable release verdict holds on unactivated Windows 11 Home (`01O §6`, `01N`); and the operator can complete the VELMA validation build in clear steps without losing orientation (`PD §24`). Readiness is measured by evidence, not by the existence of generated sections.

---

## Per-phase specifications

Fields: scope · exclusions · authoritative requirements · components · contracts · schemas · tasks (count/shape) · dependencies · permitted parallel lanes · integration gate · required tests · evidence outputs · rollback boundary · promotion gate.

### PH-1 · Requirements & Contracts
Scope: seven contract families + envelope, safe ingestion, canonicalization/hash, semantic/impact validation, policy/change/activation, immutable runtime cache. Exclusions: runtime queue, continuous Watchdog, adapters, worktrees, containers, lanes, dashboard, installer. Auth-reqs: Section 1 spec/plan, `01 §14–17`, `01R` R5. Components: contract system, config system, schema/migration system. Contracts: ENVELOPE, 7 families, CANONICAL, ROUTE-REGISTRY (authored), ACTIVATION-STORE, CONFIG/MIGRATION (partial). Schemas: `schemas/common/*`, `schemas/contracts/*/v1`, `migrations/contracts/0001`. Tasks: 5 (schemas → ingestion → semantic/impact → policy/activation/cache → verification) + R5 edits. Deps: none. Parallel lanes: 1 (serialized; 7 schemas parallel within Task 1). Integration gate: linked-contract-set test. Tests: unit/integration/security/failure-path, ≥95% coverage, Windows-Home path, `01G` verdicts. Evidence: `verify_section1` + ETM + `docs/verification/section-1-...`. Rollback boundary: failed activation leaves prior active; versions immutable. Promotion gate: 13 criteria PASS + schema-freeze approval.

### PH-S · Minimum Builder Shell
Scope: launchable Dashboard frame, explorer, Monaco, controlled terminal, safe file-op boundary, Ollama health, Aider bridge, task/diff/test/approval/checkpoint panels, IDE adapter disabled. Exclusions: full graphs, installer, complete monitoring, full S3/4/5 components. Auth-reqs: `01A §12`, `06 §11`, `01L`, `01B` St.0. Components: Dashboard(min), file-op(min), Ollama adapter(min), Aider bridge(min), terminal(min). Contracts: none new. Schemas: none authoritative. Tasks: 3–4. Deps: PH-1 + minimal slices of PH-3/4/5. Parallel lanes: up to 1. Integration gate: IP-1. Tests: `06 §11` shell proofs; one bounded Aider+Ollama task; no-bypass; adapter-disabled; runs without Codex/VS Code/OpenHands/hosted. Evidence: shell acceptance package. Rollback boundary: additive; disable reverts to bootstrap. Promotion gate: `01A §13` (1–7) + approval to begin St.1.

### PH-2 · Orchestrator: Task Queue & State Machine
Scope: Orchestrator engine (sole writer, R1), task/workstream state machine (`01L §3.1`), queue/dependencies/priority/cancellation, durable journal, fenced leases, runtime-state DB, idempotent restart, core memory. Exclusions: routing, sandboxes, lanes, verification engine, dashboard polish. Auth-reqs: `01L §3.1`, `01D §3.1`, `02 §4/§6/§7`, `01M §3.6`, `01R` R1. Components: Orchestrator, task engine, workstream SM, journal, leases, memory(core). Contracts: RUNTIME-STATE-DB, TASK-WS-SM, LEASE-FENCING, RECOVERY-JOURNAL, MEMORY-RECORD(partial). Schemas: `migrations/runtime/*`. Tasks: 4–5. Deps: PH-1 + R1 recorded. Parallel lanes: 1 (serialized core). Integration gate: state-machine + journal. Tests: legal-transition table, atomic transition/rollback, generation-only-on-activation, fencing rejects stale writers, idempotent restart, external deadlock detectability. Evidence: state-machine + recovery (RM-1). Rollback boundary: journal-authoritative; failed transition rolls back; migrations transactional. Promotion gate: `05 S2` + `01L §3.1`/`01M §3.6` PASS.

### PH-3 · Watchdog, Permissions, Approval, Audit & Tools
Scope: independent read-only Watchdog + narrow interface; permission enforcement; approval engine/queue; tamper-evident audit writer + validator; tool registry + gateway; safe file-op; diagnostic Safe Mode; **autonomy-envelope enforcement (Decision A)**. Exclusions: routing, sandboxes, lanes, verification engine. Auth-reqs: `01M`, `01K`, `01 §3/§11`, `01R` R1/Dec A/B. Components: Watchdog, permission, approval, audit writer/validator, tool registry/gateway, file-op, diagnostics(Safe Mode). Contracts: APPROVAL-RECORD, PERMISSION-GRANT, TOOL-DECLARATION, AUDIT-RECORD. Schemas: permission-grant, approval-record, tool-declaration, audit-chain. Tasks: 4–5 (+ autonomy-envelope). Deps: PH-2. Parallel lanes: 1–2. Integration gate: security-spine (VM-2). Tests: `01M`(32)+`01K`(25); **deletion approval-gated (Dec B)**; autonomy-boundary tests (Dec A); append-only chain + break detection; Safe-Mode no-autonomous-write. Evidence: security-spine + audit-integrity. Rollback boundary: Watchdog holds no writable state; permission/approval reversible; audit append-only. Promotion gate: `01M`+`01K` PASS + approval to begin St.2.

### PH-4 · Model & Coding-Tool Routing & Quotas
Scope: Ollama adapter, Aider adapter, deterministic router, Resource Scheduler, model-execution records/fingerprints, quota ledger, health checks, no-silent-substitution, privacy/cloud enforcement. Exclusions: worktrees, sandbox lifecycle, lanes, verification engine. Auth-reqs: `01J`, `03`, `01A`, `06 §6–7`. Components: router, Resource Scheduler, model-exec records, Ollama adapter, Aider adapter, quota ledger. Contracts: ROUTE-REGISTRY(activate), MODEL-FINGERPRINT, MODEL-EXEC-RECORD. Schemas: fingerprint, exec-record, quota-ledger. Tasks: 4–5. Deps: PH-3. Parallel lanes: 2 (Ollama ∥ Aider; runs ∥ PH-5). Integration gate: routed bounded Aider-on-Ollama task (IP-2). Tests: `01J`(18)+`03`; deterministic routing, no-silent-substitution, fallback=new record + reverify, local-only, reservations, ≤1 GPU-heavy, no GLM-4.7 (VM-3). Evidence: routing/quota + local-operation. Rollback boundary: model-neutral state; no roster change without approval. Promotion gate: `01J §5` PASS + approval to begin St.3.

### PH-5 · Git, Worktree & Sandbox Isolation
Scope: branch/worktree lifecycle from approved baseline; **non-root WSL2+Docker sandboxes only (Decision C)**; secret broker; network broker; cache manager; quarantined staging; policies; exact change tracking; safe Monaco/Aider write integration. Exclusions: lanes/workstream engine, verification engine, Promotion finalize, dashboard. Auth-reqs: `01I`, `01E`, `04`, `01M §3.11`, `01R` Dec C. Components: Git manager, sandbox, secret broker, network broker, cache, staging. Contracts: BASELINE-MANIFEST, COMMIT-TRAILER, NETWORK-APPROVAL, SECRET-REF, PROMOTION-PACKAGE(staging partial). Schemas: sandbox-env-identity, network-approval, secret-ref, baseline-manifest, ownership-lease. Tasks: 4–5. Deps: PH-3 (runs ∥ PH-4). Parallel lanes: 2. Integration gate: sandbox → staging → inspection. Tests: `01E`(32)+`01I`(18)+`04 §7`; no host-write, escape/privilege denial, secret non-embed/revoke, network denial/redirect containment, staging-only exit, no auto force-push/protected-write, sandbox-failure recovery (RM-2); **Windows-native execution excluded**. Evidence: isolation + git-governance. Rollback boundary: sandboxes disposable; verified checkpoints; corruption preserves refs/reflog. Promotion gate: `01E`+`01I` PASS + approval to begin St.4.

### PH-6 · Three Parallel Major-Stage Workstreams
Scope: workstream + lane lifecycle (`01D §3.1`); ≤3 concurrent; workstream contracts; shared-contract ownership; integration baselines; conflict detection beyond files; scheduler priority/interruption; integration coordinator (diagnose/assign, never edit source); optional Worker/Reviewer lanes secondary. Exclusions: full verification engine (PH-7), dashboard polish. Auth-reqs: `01D`, `01C §13`, `01L §3.1`, `01R` R2. Components: lane SM, workstream engine, integration coordinator(core). Contracts: WORKSTREAM, LANE-LIFECYCLE. Schemas: workstream-contract, lane-lifecycle, integration-package. Tasks: 4–5. Deps: PH-3, PH-4, PH-5. Parallel lanes: 3. Integration gate: IP-3. Tests: `01D`(27); workstream-cap, independence-before-parallel, isolated checkouts, single write-owner, conflict detection, no baseline drift, checkpointed interruption, 3-failure quarantine, coordinator-never-edits-source. Evidence: parallel-execution + integration. Rollback boundary: per-workstream verified checkpoints; partial work preserved unpromoted. Promotion gate: `01D §6` PASS.

### PH-7 · Testing, Evidence, Integration & Recovery
Scope: evidence store; ETM system + verification engine (verdicts); serialized integration coordinator (complete); Promotion Service (finalize); snapshot manager; retention system; scope-drift + repeated-failure recovery; recovery drills; release-candidate verification packet. Exclusions: dashboard polish, installer/packaging (PH-8). Auth-reqs: `01G`, `01C`, `01M`, `01D §3.8`, `04`, `01E §3.8`, `01R` R5. Components: evidence store, ETM, verification engine, Promotion Service, snapshot manager, retention, integration coordinator(complete). Contracts: ETM, EVIDENCE-PACKAGE, VERDICT, PROMOTION-PACKAGE(finalize), SNAPSHOT-MANIFEST, RETENTION-POLICY. Schemas: ETM, evidence-package, verdict, snapshot-manifest, retention-policy. Tasks: 5. Deps: PH-5, PH-6. Parallel lanes: 1–2 (Promotion serialized). Integration gate: IP-4. Tests: `01G`(30)+`01M`(recovery)+`01C`(retention); ETM completeness blocks promotion, anti-weakening, flaky numeric policy, candidate-tested snapshot, scope-drift recovery, repeated-failure limits, drills/failure sims (VM-5/RM-3). Evidence: full verification + recovery packages. Rollback boundary: single active rolling snapshot (Factory-state only, GitHub excluded); failed activation preserves prior. Promotion gate: `01G/01C/01M` PASS + approval to begin St.5.

### PH-8 · Complete Dashboard, Packaging & Installation
Scope: complete Dashboard + selectable panels + four graph views; repository-intelligence + graph mapping; guided installer + updater + packaging + diagnostics; release verification; clean-machine install; final docs/release package; autonomy-control surface (Decision A). Exclusions: OpenHands, research subsystem, self-improvement subsystem (deferred). Auth-reqs: `01L`, `01P`, `01O`, `01N`, `PD §14–15`. Components: Dashboard(complete), repo-index, graph-mapping, installer, updater, packaging, diagnostics(complete), release verification. Contracts: GRAPH-INDEX, RELEASE-MANIFEST, CONFIG(finalize), MIGRATION(finalize). Schemas: graph-index, release-manifest, support-profile, update/migration. Tasks: 5. Deps: all prior. Parallel lanes: up to 3 (independence-proven). Integration gate: IP-5. Tests: `01L`(21)+`01P`(10)+`01O`(17); panel/graph integrity, unactivated-Home install/lifecycle/failure-path, signed staged updates, executable+state rollback, severity gate, release verdict (VM-6/RM-4). Evidence: release package (provenance/SBOM/hashes) + release verdict. Rollback boundary: executable rollback window + Factory-state snapshot; incompatible downgrade fails closed; GitHub repos untouched. Promotion gate: `01O §6` stable verdict (zero critical/high) + operator release approval.
