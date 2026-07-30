# PH-4 (Section 4) — Model & Coding-Tool Routing & Quotas — Implementation Plan

**Status:** Approved planning order (L25.1) · **Governing:** `01J`, `03`, `01A`, `06 §6-7`. Roadmap spec: `docs/10` PH-4. In force with `01R`. Runs ∥ PH-5 (Workstream Map Set A).

## Task decomposition
### Task 4.1 — Ollama runtime adapter
- Owned paths: `src/factory/models/ollama_adapter/**`. Deliverables: health/version, exact-model discovery, call/cancel/failure, resource-aware routing, usage records; extends the PH-S minimal adapter. Tests: health check; exact-ID verification; local-only operation. Evidence: Ollama ETM. Completion: `06 §7`.
### Task 4.2 — Aider coding-worker adapter
- Owned paths: `src/factory/workers/aider_adapter/**`. Deliverables: bounded `submit_task/stream/request_revision/cancel/collect_package` interface; owned-paths + route + limits enforcement. Tests: bounded task edits only owned paths; cannot self-assign/expand scope/certify. Evidence: Aider ETM. Completion: `06 §6`, `01A §2`.
### Task 4.3 — Model router + approved registry (deterministic, no silent substitution)
- Owned paths: `src/factory/routing/**`. Deliverables: deterministic visible operator-overridable routing; approved-model/worker registry; privacy/cloud enforcement. Contracts: CTR-ROUTE-REGISTRY(activate), CTR-MODEL-FINGERPRINT, CTR-MODEL-EXEC-RECORD. Tests (model-routing #29, fallback #30): deterministic routing + reason; **no silent substitution**; **no GLM-4.7**; fallback = new execution record + reruns affected verification. Evidence: routing ETM (VM-3). Completion: `01J §2/§5`, `03 §7`.
### Task 4.4 — Resource Scheduler + quota ledger
- Owned paths: `src/factory/scheduler/**`. Deliverables: executable reservations/admission (VRAM/RAM/CPU/storage/timeouts/thermal), ≤1 GPU-heavy, anti-thrash; quota/usage ledger. Tests (resource-pressure #27, scheduler #28): overcommit prevention; ≤1 GPU-heavy on 12 GB; checkpointed pause; missing sensor → REDUCED_MONITORING. Evidence: scheduler ETM. Completion: `01J §3.3`, `01D §2.12`.
### Task 4.5 — Health checks, fallback provenance, privacy gate
- Owned paths: `src/factory/routing/health/**`. Deliverables: important-task health-check triggers; fallback provenance boundary; privacy-before-hosted. Tests: health-check conditions (`01J §3.4`); fallback closes/checkpoints failed attempt + new record; privacy evaluated before hosted use. Evidence: fallback/health ETM. Completion: `01J §3.2/§3.4`, `03 §9`.

## Acceptance & handoff
Acceptance: `01J §5`(18)+`03` PASS (VM-3); local-only operation proven with hosted absent. Rollback boundary: model-neutral state; no roster change without approval. Promotion gate: PH-4 exit + begin `01B` St.3. Handoff → PH-6 (workstreams consume routing), IP-2 with PH-5.
