# Controlled Glossary and Crosswalks

**Status:** Derived reference (L25.D) — aggregates authoritative definitions; never overrides a source
**Recorded:** July 24, 2026
**Rule:** Where a term's source document changes, this file is regenerated. It defines terms of record and provides crosswalks; it holds no independent authority over the sources it cites.

## 1. Controlled glossary

| Term | Definition (of record) | Authoritative source |
|---|---|---|
| **task** | One bounded unit of execution with owned paths, permitted routes, limits, evidence, and completion conditions. | Section 1 §4.3; `01 §13` |
| **stage** | A supplement-level architecture-decision topic (internal "Stage 2–14"). **Distinct from** build Sections and from `PD §6`'s 20 lifecycle "work stages." | `HANDOFF §1`; §2 crosswalk below |
| **phase** | A unit of sequenced delivery in this roadmap = one build **Section** (or the Shell milestone). `phase ≡ Section`. | `docs/10`; `05` |
| **workstream** | The **default execution unit**: one of up to three concurrent major stages, each completing design→implement→test→verify→handoff. | `01C §13`; `01D §1`; `01R` R2 |
| **lane** | The isolated-checkout execution/concurrency unit *under* workstreams (its own worktree/clone); has its own lifecycle. Distinct from "workstream." | `01D §3.1` |
| **Worker/Reviewer pair** | Optional/secondary hosted-model pattern (one Worker + one Reviewer). Not the default unit (superseded by workstreams). | `01A §11`; `01R` R2 |
| **branch** | A controlled Git task branch created from an approved baseline for each executable task. | `01I §2.8`; `01D §2.4` |
| **worktree** | A separate physical Git checkout giving a concurrent lane isolated workspace state. | `01D §2.8`; `01I §3.1` |
| **sandbox** | A disposable non-root WSL2+Docker environment for all code-changing/executing work. **v1: WSL2+Docker only** (Windows-native excluded). | `01E`; `01R` Dec C |
| **checkpoint** | A verified safe point (repo base, worktree/branch, owned paths, passing tests, reproducible state, tested rollback). | `04 §2`; `01D §3.6` |
| **baseline** | The approved commit (or integration branch + commit) from which task branches begin; recorded and immutable during execution. | `01D §3.3`; `01I §2.8` |
| **evidence package** | A finalized, integrity-protected verification package (`01G §6`) embedding the ETM. | `01G §6`; `01C §2` |
| **Evidence Traceability Manifest (ETM)** | The mandatory per-criterion machine-readable chain requirement→criterion→check→command→env→result→evidence hash→artifact hash→approver. | `01G §3.1` |
| **Promotion Package** | The machine-readable manifest required to move sandbox output into approved state (identities, diffs, hashes, evidence, approvals, rollback). | `01E §3.8` |
| **approval** | A bound, expiring, revocable operator decision with complete context, recorded for audit. | `01L §3.2`; `01K §2.6` |
| **promotion** | Advancing verified work into approved/protected state through the Promotion Service and all gates. | `01I §3.2`; `01E §3.7` |
| **Promotion Service** | The only component permitted to update a protected ref (local or offline), after gates pass. | `01I §3.2` |
| **release** | A uniquely versioned, provenance-complete, signed artifact set with a `01O §6` verdict. | `01O` |
| **recovery snapshot** | The single active rolling snapshot of **Factory state only** (GitHub project repos excluded), candidate-tested before activation. | `01C §12`; `01M §3.9` |
| **Improvement Packet** | An evidence-based proposal to change Factory; **never auto-applied** — application requires approval. | `01C §9`; `01H`; `01R` R3 |
| **Orchestrator** | The deterministic control-plane engine; **sole authoritative writer** to the runtime-state DB; owns every state transition. | `02 §4`; `01R` R1 |
| **Watchdog** | The separate, independently supervised, normally read-only reliability supervisor acting only through a narrow control interface. | `01M`; `01R` R1 |
| **autonomy level** | The selectable 1–100% permission/approval envelope enforced by permissions + approvals + Orchestrator, surfaced by the Dashboard. | `PD §8`; `01R` Dec A |

## 2. Stage ↔ Section ↔ Phase crosswalk

Three distinct decomposition schemes exist; this table binds them.

- **Sections 1–8** = build/implementation order (`05`, `01 §10`).
- **Stages 2–14** = supplement architecture-decision topics (`01D`–`01P`; from each doc's "Approved Stage N decisions" heading). `01C` is a pre-Stage-2 foundational supplement; `01Q` is Stage 14; `01N` is a non-sequential "Stage 12 correction."
- **`PD §6` "20 work stages"** = the finished Factory's *runtime* lifecycle for building user projects (requirements→…→reporting) — a different axis, not a build order.

| Supplement | Internal Stage | Topic | Primarily built in Phase/Section |
|---|---|---|---|
| `01C` | (foundational) | session evidence & Improvement Packets | PH-7 (retention), deferred (self-improvement) |
| `01D` | Stage 2 | task engine & parallel workstreams | PH-2 / PH-6 |
| `01E` | Stage 3 | sandbox & isolation | PH-5 |
| `01F` | Stage 4 | memory records & retention | PH-2 (memory) / PH-7 (retention) |
| `01G` | Stage 5 | verification & evidence | PH-7 |
| `01H` | Stage 6 | controlled self-improvement | deferred (post-core) |
| `01I` | Stage 7 | git projects & repository management | PH-5 |
| `01J` | Stage 8 | models routing & reasoning | PH-4 |
| `01K` | Stage 9 | tools permissions & security | PH-3 |
| `01L` | Stage 10 | dashboard & workstream state machine | PH-2 (state machine) / Shell+PH-8 (UI) |
| `01M` | Stage 11 | recovery reliability & Watchdog | PH-3 (Watchdog) / PH-7 (snapshots/recovery) |
| `01N` | (Stage 12 correction) | Windows activation independence | PH-8 |
| `01O` | Stage 12 | deployment, updates & release | PH-8 |
| `01P` | Stage 13 | repository intelligence & graph mapping | PH-8 |
| `01Q` | Stage 14 | research, sources & external knowledge | deferred (post-core) |

## 3. State-vocabulary crosswalk

Multiple state machines exist for **different objects**; they are not interchangeable. The authoritative task/workstream state machine is `01L §3.1`; all other lifecycles must remain consistent with it where they intersect.

| State set | Object | States | Source |
|---|---|---|---|
| Task/workstream (authoritative) | tasks & workstreams | `QUEUED, PLANNING, RUNNING, AWAITING_APPROVAL, VERIFYING, BLOCKED, PAUSED, FAILED, QUARANTINED, STOPPING, CANCELLED, COMPLETE, ROLLED_BACK` | `01L §3.1` |
| Lane lifecycle | lanes | `PROPOSED, APPROVED, READY, ACTIVE, BLOCKED, PAUSED, VERIFICATION, HANDOFF, INTEGRATED, CLOSED, FAILED, QUARANTINED` | `01D §3.1` |
| Contract file status | contract files | `DRAFT, VALIDATED, APPROVAL_REQUIRED, APPROVED, SUPERSEDED, REJECTED, RETIRED` | Section 1 §6 |
| Improvement Packet lifecycle | packets | `PROPOSED→REVIEWED→EXPERIMENT_AUTHORIZED→TESTING→VERIFIED\|FAILED\|INCONCLUSIVE→APPLY_AUTHORIZED→MONITORING→ACCEPTED\|ROLLED_BACK\|QUARANTINED→ARCHIVED`; `STALE` | `01H §4.2` |
| Reconciliation outcome | tasks after restart | `RESUMABLE, BLOCKED, FAILED, QUARANTINED, COMPLETED, CANCELLED` | `01M §5` |
| Recovery result | recovery episodes | `RECOVERED, DEGRADED, BLOCKED, ESCALATED, STOPPED` | `04 §9` |
| Verification verdict | criteria & packages | `PASS, FAIL, BLOCKED, INCONCLUSIVE, NOT_TESTABLE` | `01G §3.3`; `01R` R5 |
| Graph state | graph indexes | `COMPLETE, PARTIAL, STALE, UNSUPPORTED, CORRUPT, REBUILDING` | `01P §3.5` |
| Research freshness | research conclusions | `CURRENT, REVIEW_DUE, STALE, SUPERSEDED, CONFLICTING, INCONCLUSIVE, SOURCE_UNAVAILABLE` | `01Q §3.5` |
| Resource state | scheduler | `NORMAL, WARNING, PAUSE, CRITICAL_CONTAINMENT, REDUCED_MONITORING` | `01M §3.3` |

**Consistency rule:** Section 2 (PH-2) implements the `01L §3.1` set as authoritative; the lane lifecycle (`01D §3.1`) is a separate dimension that must not contradict it (`01D §3.1`); a lane cannot be `ACTIVE` when its task is paused/cancelled/failed/quarantined/rolled-back.
