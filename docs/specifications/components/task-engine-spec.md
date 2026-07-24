# Component Specification — Task Engine (CMP-TASKENG)

**Instance authority:** L25.1 planning record · **Phase:** PH-2 · **Governing:** `02 §6`, `01L §3.1`,
`05 S2`, `01D §3.4` (dependency independence), `01F` (core memory boundary via CMP-MEM). Parent index:
`00-COMPONENT-MAP.md` #3. Baselines inherited; only deltas stated.

```yaml
component_id:          CMP-TASKENG
name:                  Task Engine (queue / dependencies / cancellation)
implementation_phase:  PH-2
responsibility: >
  Computes which tasks are ready to run from a dependency graph and current task states, orders them
  deterministically, and provides the cancellation state-transition mechanics. All state changes it
  effects go through CMP-ORCH.apply_transition; it never writes state directly.
non_responsibilities:
  - Does not halt a running worker/process (no workers exist until PH-3/PH-5) — provides state mechanics only.
  - Does not parse Task Contracts or build the dependency graph from scratch: it REUSES PH-1
    ReferenceResolver.resolve_dependency_graph (cycle rejection stays a PH-1 concern).
  - Does not implement priority pre-emption / starvation timing (01D §3.5 scheduler policy is PH-6).
authoritative_state:   none (reads task states via reader; writes via CMP-ORCH).
inputs:
  - dependency_graph: Mapping[str, frozenset[str]]  (from PH-1 resolver)
  - states: Mapping[str, TaskState]
  - cancellation requests (task_id, reason, actor)
outputs:
  - ready task IDs (deterministically ordered)
  - STOPPING / CANCELLED transition events (via CMP-ORCH)
interfaces:
  - "TaskScheduler.ready_tasks(dependency_graph, states) -> tuple[str, ...]"
  - "request_cancellation(writer, task_id, reason, actor) -> StateTransitionEvent   # -> STOPPING"
  - "finalize_cancellation(writer, task_id, actor) -> StateTransitionEvent          # STOPPING -> CANCELLED"
dependencies:          [ CMP-ORCH (apply_transition), CMP-WSSM (legality), PH-1 ReferenceResolver ]
owned_contracts:       [ ]   # consumes CTR-TASK-WS-SM and CTR-TASK; owns none
permitted_authority:   BASE-P.
prohibited_authority:  BASE-X; readiness is advisory — only CMP-ORCH transitions actually change state.
trust_boundary:        BASE-T.
failure_modes:
  - cancellation of an already-terminal task -> illegal transition, rejected by CMP-ORCH (fail closed)
  - dependency referencing an unknown task -> not ready (never crashes)
degradation_behavior:  BASE-D.
recovery_behavior:     BASE-R; readiness is recomputed from authoritative state after restart, never cached
                       across a restart as truth.
security_requirements: BASE-S.
resource_requirements: negligible.
required_tests:
  - task with an incomplete dependency is not ready; task with no deps is always ready
  - ready ordering is deterministic + stable across repeated identical calls
    (dependency-count ascending, then task_id ascending — never insertion order)
  - request/finalize cancellation drives QUEUED/RUNNING... -> STOPPING -> CANCELLED
  - idempotent restart does not re-admit a task whose transition already committed
```
