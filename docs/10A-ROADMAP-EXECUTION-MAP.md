# Roadmap Execution Map

**Document ID:** ROADMAP-10A
**Repository path:** `docs/10A-ROADMAP-EXECUTION-MAP.md`
**Status:** Active — execution-environment companion to the Master Implementation Roadmap
**Authority level:** Plan (subordinate companion to `docs/10-IMPLEMENTATION-ROADMAP.md`)
**Owner:** Roadmap pass (PH-2 planning, Pass 3)
**Established:** 2026-07-24
**Governing inputs:** `docs/10` (phase order/gates/critical path — authoritative), `docs/05` (section outputs),
`docs/planning/DEPENDENCY-MAP.md` (dependency graph/cycle check — authoritative), `docs/planning/WORKSTREAM-MAP.md`
(parallel sets/independence — authoritative), `docs/01R` (R1–R5, Dec A–C), `01E`/`01K`/`01J`/`03`/`01M`.

## 1. Purpose and single-authority boundary

`docs/10` remains the **single plan of record** for phase order, entry/exit gates, critical path, and
operator approvals. This companion adds only what `docs/10` does not carry: the **per-phase execution
environment** each phase runs in (branch, worktree, sandbox, models, tools, permissions, secrets, resources,
expected runtime/memory/storage, expected outputs/evidence), plus a consolidated **implementation-order
validation record**. It restates no phase-order or dependency decision — those are cited to their owners.
Where this map and `docs/10`/`DEPENDENCY-MAP`/`WORKSTREAM-MAP` disagree, the owner document wins and this
map is corrected.

All values below are **planning expectations**, not measured results. Resource envelopes derive from the
initial operating target (`README.md` "Initial operating target": Ryzen 7 7800X3D, RTX 4070 Super 12 GB VRAM,
32 GB RAM) and the `01M §3.3` staged-threshold policy; actuals are captured per phase in each verification
report's environment table (precedent: the S1 report).

## 2. Standing execution invariants (apply to every phase unless a row overrides)

- **Branch:** each phase implements on a controlled phase/task branch from an approved baseline
  (`01D §2.4/§3.3`); never on `main`. PH-1 used `claude/builder-handoff-pr8-inc9p8`; PH-2 planning uses
  `claude/ph2-orchestrator-planning`. Product-implementation branch names are assigned by the operator at
  each phase's entry gate (not pre-assigned here — assigning them now would be an unapproved decision).
- **Worktree:** isolated checkout per concurrent lane; worktree preferred, clone permitted (`01D §2.8`).
  Single-lane phases need no separate worktree.
- **Sandbox:** WSL2 + Docker Linux container only (Decision C); non-root; no Windows-native execution.
  Planning/authoring passes (PH-1 through PH-2 as run so far) execute in the dev environment, not a sandbox,
  because they produce no executing product code — sandboxing binds from PH-4/PH-5 onward when the Factory
  runs models/commands.
- **Models/Tools:** none required for PH-1/PH-2 (pure Python + SQLite, offline). Ollama/Aider bind at PH-4.
- **Permissions/Secrets:** no network, no secrets, no cloud for PH-1/PH-2 (offline, local files + SQLite).
  Secret broker / network broker bind at PH-5; approvals engine at PH-3.
- **Internet:** disabled by default at all phases (`README` non-negotiables); enabled only per task-scoped
  approval from PH-5 onward.
- **Evidence:** every phase emits an `01G §3.1` ETM + a `docs/verification/section-*.md` report + a
  regenerable `artifacts/verification/*` manifest (gitignored), per the S1 precedent.

## 3. Per-phase execution map

Legend: **S/W/G** = sandbox / worktree / GPU needed. Resource columns are planning envelopes for one active
lane on the target machine.

| Phase | Branch (base) | S | W | G | Models / Tools | Perms / Secrets / Net | Runtime (order) | RAM env | Storage env | Expected outputs | Expected evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **PH-1** ✅ | task branch / promoted | no | no | no | none (py+sqlite) | none / none / off | ~1 min suite | < 1 GB | < 50 MB (repo) | `src/factory/contracts`, `schemas`, `migrations/contracts/0001` | S1 report `PASS`, 96.85% cov |
| **PH-S** | task branch / PH-1 base | no† | no | no | Ollama+Aider (min health only) | file-op scope / none / off | UI-interactive | 1–2 GB | < 200 MB | Dashboard frame, explorer, Monaco, terminal, file-op boundary | shell acceptance pkg (`06 §11`) |
| **PH-2** | task branch / PH-1 base | no | no | no | none (py+sqlite) | none / none / off | seconds–1 min | < 1 GB | < 50 MB | `src/factory/orchestrator`, `src/factory/memory/core`, `migrations/runtime/0001..0003` | state-machine/journal/fencing/queue ETMs |
| **PH-3** | task branch / PH-2 base | yes | 1–2 | no | none (enforcement) | permission/approval/audit engines / none / off | seconds–1 min | 1–2 GB | < 100 MB | Watchdog(process), permission/approval/audit, tool gateway, file-op, Safe Mode | security-spine ETM (VM-2) |
| **PH-4** | task branch / PH-3 base | yes | 2 (∥PH-5) | ≤1 | **Ollama (qwen3:8b/14b), Aider** | route/quota / none / local-only | model-bound (GPU) | up to 12 GB VRAM + ~16 GB RAM | model cache (gitignored) | router, Resource Scheduler, adapters, quota ledger | routing/no-substitution ETM (VM-3) |
| **PH-5** | task branch / PH-3 base | yes | 2 (∥PH-4) | no | none (isolation) | secret broker, network broker, mounts / brokered / brokered | container-bound | 2–4 GB | disposable sandboxes | Git/worktree mgr, sandbox mgr, brokers, cache, staging | isolation/git-governance ETM |
| **PH-6** | task branch / {3,4,5} | yes | 3 | ≤1 | Ollama/Aider (via router) | full task-contract scope / brokered / brokered | multi-lane | up to full envelope | 3× lane checkouts | lane engine, workstream SM, integration coordinator | 3-workstream integration ETM (VM-4) |
| **PH-7** | task branch / {5,6} | yes | 1–2 | ≤1 | via router | promotion/evidence scope / brokered / brokered | verification-bound | 2–6 GB | evidence store + snapshot | evidence store, ETM engine, verification engine, Promotion Service, snapshot mgr | full verification+recovery pkg (VM-5/RM-3) |
| **PH-8** | task branch / all | yes | ≤3 | no | via router | release/install scope / signing refs / brokered | build+install-bound | 2–4 GB | release artifacts + SBOM | complete Dashboard, graphs, installer, updater, packaging | release pkg + verdict (VM-6/RM-4) |

† PH-S runs Ollama health checks and a bounded Aider task; those specific proofs execute against the local
runtime but the shell scaffolding itself is not sandboxed until it drives executing project work.

## 4. Implementation-order validation record

Validated this pass against `docs/10 §5`, `DEPENDENCY-MAP §1/§4/§5`, `WORKSTREAM-MAP §2`:

| Check | Result | Basis |
|---|---|---|
| Every phase has prerequisites (except roots) | PASS | PH-1 is the only root; all others cite blocking prereqs (`10 §5`) |
| Every prerequisite exists / is defined | PASS | all prereqs are defined phases in `10 §1` |
| Every dependency resolves | PASS | `DEPENDENCY-MAP §1` edges all land on defined phases |
| No dependency cycles | PASS | `DEPENDENCY-MAP §4` acyclic; only forward ref is PH-S thin-slice (bootstrap, bounded) |
| No impossible execution order | PASS | topological order PH-1→2→3→{4,5}→6→7→8 is realizable |
| Every contract/schema prereq exists at phase start | PASS | contract chain `10 §7` / `DEPENDENCY-MAP §3`; PH-2 consumes PH-1 CANONICAL→RUNTIME-STATE-DB edge |
| Every verification path exists | PASS | per-phase VM milestones `10 §12`; template exists (gap G-06 = generalizing S1 report, non-blocking) |
| Every evidence path exists | PASS | ETM template + per-phase reports (§2 invariant) |
| Every rollback path exists | PASS | per-phase rollback boundary in `10` phase specs; PH-2 = journal-authoritative |
| Every approval path exists | PASS | `10 §15` operator approvals + approval/promotion templates |
| No orphan phase / unreachable phase | PASS | every phase is on a path from PH-1 to the release (PH-8) |
| Integration points defined | PASS | `10 §11` IP-1..IP-5; `WORKSTREAM-MAP §4` |

**Dependency analysis artifacts** (owners, not duplicated here): complete dependency graph + critical path →
`DEPENDENCY-MAP §1/§5`; parallel/blocked work → `WORKSTREAM-MAP §2/§3`; shared components/state/contracts →
`DEPENDENCY-MAP §2/§3`; integration/synchronization points → `10 §11`; promotion checkpoints → `10 §15`.

## 5. Consistency review (this pass)

Cross-checked against repository authority, PAL-000, CL-000, `docs/10`, `DEPENDENCY-MAP`, `WORKSTREAM-MAP`,
`CONTRACT-REGISTRY`, `SCHEMA-REGISTRY`, `VERIFICATION-MATRIX`, `RISK-REGISTER`. **No inconsistency found; no
repair required.** The one modeling choice worth recording: product-implementation branch names for PH-S and
PH-3…PH-8 are intentionally left unassigned (operator assigns at each entry gate) rather than invented here —
assigning them now would be an unapproved decision and a future stale-assumption risk.

## 6. Update / retirement rules

Regenerated whenever `docs/10`, `DEPENDENCY-MAP`, or `WORKSTREAM-MAP` change, or when a phase's real execution
environment is fixed at its entry gate (replace the planning envelope row with the approved actual). Never
overrides its owner documents. Superseded by pointer, never deleted.
