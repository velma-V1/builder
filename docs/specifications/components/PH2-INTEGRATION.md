# PH-2 Component Integration Review

**Instance authority:** L25.1 planning record · **Phase:** PH-2 · **Scope:** the six PH-2 components
(CMP-ORCH, CMP-WSSM, CMP-TASKENG, CMP-JOURNAL, CMP-LEASE, CMP-MEM). System-wide dependency/parallel/critical
-path graphs remain owned by `docs/planning/DEPENDENCY-MAP.md` and `docs/planning/WORKSTREAM-MAP.md`; this
document holds only the intra-PH-2 integration matrices required by Pass 4.

## 1. Component interaction map

```
                 ┌────────────────────────── CMP-ORCH (sole writer, owns runtime DB) ──────────────────────────┐
                 │  consults            embeds writes of                         embeds writes of               │
                 ▼                          ▼                                        ▼                           ▼
            CMP-WSSM (pure)          CMP-JOURNAL (events)                     CMP-LEASE (fencing)          CMP-MEM (records)
                 ▲                          ▲                                                                    
                 │ legality                 │ reconcile_startup (read-only)
            CMP-TASKENG (readiness/cancellation) ── request/finalize transitions ──► CMP-ORCH.apply_transition
                 ▲
                 │ dependency_graph
        PH-1 ReferenceResolver (reused, read-only)
```

## 2. Interface matrix

| Consumer → Provider | Interface used |
|---|---|
| CMP-ORCH → CMP-WSSM | `TransitionPolicy.is_legal` |
| CMP-TASKENG → CMP-ORCH | `_OrchestratorStateWriter.apply_transition` |
| CMP-TASKENG → CMP-WSSM | `TaskState`, legality (indirect via ORCH) |
| CMP-TASKENG → PH-1 resolver | `ReferenceResolver.resolve_dependency_graph` (read-only) |
| CMP-JOURNAL → CMP-ORCH | `OrchestratorStateReader.get_task/get_events` |
| CMP-LEASE → CMP-ORCH | shared DB connection + transaction |
| CMP-MEM → CMP-ORCH | shared DB connection + transaction |

## 3. Dependency matrix (intra-PH-2, acyclic)

| Component | Depends on |
|---|---|
| CMP-WSSM | — (foundational) |
| CMP-ORCH | CMP-WSSM, CMP-SCHEMA (PH-1 migration pattern) |
| CMP-JOURNAL | CMP-ORCH, CMP-WSSM |
| CMP-LEASE | CMP-ORCH |
| CMP-MEM | CMP-ORCH |
| CMP-TASKENG | CMP-ORCH, CMP-WSSM, PH-1 ReferenceResolver |

Cycle check: topological order WSSM → ORCH → {JOURNAL, LEASE, MEM, TASKENG}. **Acyclic.**

## 4. Ownership matrix (single owner per responsibility — resolves the map's apparent overlap)

| Responsibility | Single owner | Note |
|---|---|---|
| Authoritative write authority + runtime DB as a whole | CMP-ORCH | R1 sole writer |
| Legal-transition policy (pure) | CMP-WSSM | stateless |
| task_state_events sub-schema + reconciliation logic | CMP-JOURNAL | writes only inside ORCH tx |
| fencing_counters/leases sub-schema + token logic | CMP-LEASE | writes only inside ORCH tx |
| memory_records sub-schema (PROJECT_AUTHORITY) | CMP-MEM | writes only inside ORCH tx |
| readiness/ordering/cancellation mechanics | CMP-TASKENG | advisory; transitions via ORCH |

**No duplicate ownership:** sub-components own their *domain schema + logic*; CMP-ORCH owns the *write
transaction*. The map's "CMP-ORCH owns journal/leases" and "CMP-JOURNAL/CMP-LEASE own journal/leases" is this
layering, not a conflict (R1 is the tiebreaker: exactly one writer).

## 5. State-ownership matrix

| State/table | Written by | Read by |
|---|---|---|
| `tasks`, `task_state_events` | CMP-ORCH (tx) on behalf of CMP-TASKENG/CMP-JOURNAL | CMP-JOURNAL, readers (mode=ro) |
| `fencing_counters`, `leases` | CMP-ORCH (tx) on behalf of CMP-LEASE | CMP-LEASE.validate_token |
| `memory_records` | CMP-ORCH (tx) on behalf of CMP-MEM | CMP-MEM.get |

## 6. Contract & schema usage matrix

| Component | Contracts | Schemas / migrations |
|---|---|---|
| CMP-ORCH | CTR-RUNTIME-STATE-DB | `migrations/runtime/0001_state.sql` |
| CMP-WSSM | CTR-TASK-WS-SM | (none; pure code) |
| CMP-JOURNAL | CTR-RECOVERY-JOURNAL | `0001_state.sql` (task_state_events) |
| CMP-LEASE | CTR-LEASE-FENCING | `0002_leases.sql` |
| CMP-MEM | CTR-MEMORY-RECORD (partial) | `0003_memory.sql` |
| CMP-TASKENG | (consumes CTR-TASK, CTR-TASK-WS-SM) | (none) |

All three migrations follow the PH-1 SHA-256-pinned transactional runner pattern (`CTR-MIGRATION`).

## 7. Failure / recovery / rollback dependency map

- **Failure domain:** all six share one SQLite DB. A DB-level failure fails all writes closed (no partial
  state) — this is intended (single failure domain = single authoritative store, `02 §6`).
- **Recovery dependency:** CMP-JOURNAL reconciliation must run (via CMP-ORCH reader) before CMP-TASKENG
  admits any task after restart; CMP-LEASE invalidates prior-epoch leases at the same point.
- **Rollback boundary:** journal-authoritative; every transition is atomic, so rollback = "the transaction
  did not commit." Migrations are transactional. No cross-component rollback coordination is needed because
  there is exactly one writer and one DB.

## 8. Security / trust boundary map

- **Trust boundary:** every transition request, token, and memory write is untrusted until validated
  (expected-state + legality for transitions; counter comparison for tokens; explicit verify for memory).
- **Security boundary:** the single-writer invariant, the append-only journal triggers, and the read-only
  (`mode=ro` + authorizer) reader are the three core controls; violating any fails closed.

## 9. Integration order (build/verify sequence within PH-2)

CMP-WSSM (Task 2.1) → CMP-ORCH store (Task 2.2) → CMP-JOURNAL (Task 2.3) → CMP-LEASE (Task 2.4) →
CMP-TASKENG + CMP-MEM (Task 2.5) → end-to-end lifecycle + verification (Task 2.5 integration + Task 2.6).
This matches PLAN-S2's task order and its end-to-end lifecycle test.

## 10. Implementation validation (this pass)

Every PH-2 component is buildable (all dependencies resolve to PH-1 (implemented) or earlier PH-2 tasks);
every interface is defined in a component spec; every contract exists in `CONTRACT-REGISTRY`; every schema
exists or is defined in PLAN-S2; every verification path is a named test set; every rollback path is
journal-authoritative; no orphan/unreachable component; no undocumented interaction. **Result: PASS.**
