# Component Specification — Workstream/Task State Machine (CMP-WSSM)

**Instance authority:** L25.1 planning record · **Phase:** PH-2 · **Governing:** `01L §3.1`, `01R` R1.
Parent index: `00-COMPONENT-MAP.md` #5. Baselines inherited; only deltas stated.

```yaml
component_id:          CMP-WSSM
name:                  Workstream/Task State Machine
implementation_phase:  PH-2
responsibility: >
  Owns the authoritative task/workstream state set and the legal-transition table from 01L §3.1.
  Provides a pure, side-effect-free decision function the Orchestrator consults before applying any
  transition. Holds no state and touches no database.
non_responsibilities:
  - Does not apply transitions or write state (that is CMP-ORCH, the sole writer).
  - Does not own the lane lifecycle (that is CMP-LANESM, PH-6 — a separate dimension, 01D §3.1).
  - Does not invent transitions or reason codes; the table is transcribed verbatim from 01L §3.1.
authoritative_state:   none (pure policy).
inputs:                [ prev_state: TaskState, new_state: TaskState ]
outputs:               [ is_legal: bool ]
interfaces:
  - "TransitionPolicy.is_legal(prev: TaskState, new: TaskState) -> bool"
  - "ALLOWED_TRANSITIONS: Mapping[TaskState, frozenset[TaskState]]"
  - "TaskState (StrEnum, 13 values); TERMINAL_STATES: frozenset[TaskState]"
dependencies:          [ ]   # foundational; depends on nothing
owned_contracts:       [ CTR-TASK-WS-SM ]
permitted_authority:   BASE-P; read-only pure function usable by any component.
prohibited_authority:  BASE-X; no client (model, Dashboard, lane) may bypass it to invent a transition
                       (01L §3.1 "no client ... may invent a transition").
trust_boundary:        BASE-T; treats any (prev,new) pair as untrusted input to be judged.
failure_modes:
  - unknown prev_state -> is_legal returns False (fail closed)
  - same-state no-op (prev == new) -> is_legal returns False (a transition must change state)
degradation_behavior:  none applicable (pure function).
recovery_behavior:     none applicable (stateless).
security_requirements: BASE-S; the transition table is a governing control — changed only via the
                       architecture/versioned-policy process, never at runtime.
resource_requirements: negligible.
required_tests:
  - every documented 01L §3.1 transition is legal (parametrized, exhaustive over the table)
  - every non-documented (prev,new) pair including all (s,s) no-ops is illegal
    (itertools.product(TaskState, TaskState) minus the table minus no-ops -> all False)
```

## Notes

The exhaustive legal/illegal test is the completeness guarantee: it proves the implementation encodes the
`01L §3.1` table exactly, with nothing added and nothing missing. `ALLOWED_TRANSITIONS` is a literal
transcription so the source document and the code can be diffed directly (PLAN-S2 Task 2.1).
