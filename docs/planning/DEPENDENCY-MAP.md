# Cross-Phase & Component Dependency Map

**Status:** Derived/non-overriding reference (L25.D)
**Recorded:** July 24, 2026
**Sources:** `docs/10` (roadmap A6–A10), Pass-4 component map, `01D §3.4` (conflict classes), `02`. In force with `01R`.

Regenerated on any interface/dependency change. Must remain acyclic (`01D §3.4`, `01P §2.19`).

## 1. Phase dependency ordering
```
PH-1 ──┬── PH-S (thin vertical slice; forward-needs minimal PH-3/4/5)
       └── PH-2 ── PH-3 ──┬── PH-4 ─┐
                          └── PH-5 ─┴── PH-6 ── PH-7 ── PH-8
```
Blocking prerequisites: `PH-1→{PH-S,PH-2}` · `PH-2→PH-3` · `PH-3→{PH-4,PH-5}` · `{PH-3,PH-4,PH-5}→PH-6` · `{PH-5,PH-6}→PH-7` · `{all}→PH-8`.

## 2. Component dependency edges (key)
| Component | Depends on |
|---|---|
| Orchestrator | contract system, recovery journal, lease system |
| Watchdog | Orchestrator (observes; separate process), snapshot mgr, journal |
| permission / approval / audit writer | Orchestrator |
| model router | tool gateway, Resource Scheduler, Ollama adapter, Aider adapter |
| Resource Scheduler | Orchestrator, Watchdog (thresholds) |
| sandbox mgr | Resource Scheduler, secret broker, network broker, cache, Git mgr |
| Git/workspace mgr | Orchestrator, sandbox mgr, Promotion Service |
| workstream/lane engine | workstream state machine, Git mgr, sandbox mgr, router |
| integration coordinator | workstream engine, verification engine, Promotion Service |
| ETM system | verification engine, evidence store, model-exec records |
| Promotion Service | verification engine, evidence store, Git mgr, approval engine |
| snapshot mgr | Orchestrator, journal, audit validator |
| Dashboard / graph / repo-index | all authoritative records (read-only) |

## 3. Contract dependency edges
`ENVELOPE → {7 families}` · `{TASK,OWNERSHIP,PERMISSION,EVIDENCE} → TASK-WS-SM` · `CANONICAL → ACTIVATION-STORE → RUNTIME-STATE-DB` · `EVIDENCE → ETM → EVIDENCE-PACKAGE → PROMOTION-PACKAGE` · `VERDICT` gates promotion · `BASELINE-MANIFEST → PROMOTION-PACKAGE` · `AUDIT-RECORD` underlies all privileged actions.

## 4. Cycle check
Component graph and contract graph are **acyclic**. The only forward reference is PH-S → minimal slices of PH-3/4/5 — a controlled thin-slice coupling (bootstrap), not a cycle; its minimal-slice boundary is defined in the PH-S plan.

## 5. Critical path
**PH-1 → PH-2 → PH-3 → PH-5 → PH-6 → PH-7 → PH-8.** PH-4 is off the longest chain (parallel to PH-5 after PH-3, converging at PH-6).

## 6. Parallel-eligibility (feeds the Workstream Map)
| Pair | Independent? | Basis |
|---|---|---|
| PH-4 ∥ PH-5 (after PH-3) | Yes | disjoint components + owned paths; shared interface = permission/tool-gateway (frozen in PH-3) |
| PH-S ∥ early PH-2/PH-3 | Conditional | thin slice; independent once minimal file-op/adapter interfaces are frozen |
| PH-8 dashboard ∥ installer ∥ packaging | Yes | disjoint components; consume read-only authoritative records |
| Any pair sharing a shared contract/schema/migration | No | serialized integration (`01 §8`, `01D §3.8`) |
