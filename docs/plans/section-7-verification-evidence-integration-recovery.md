# PH-7 (Section 7) — Testing, Evidence, Integration & Recovery — Implementation Plan

**Status:** Approved planning order (L25.1) · **Governing:** `01G`, `01C`, `01M`, `01D §3.8`, `04`, `01E §3.8`, `01R` R5. Roadmap spec: `docs/10` PH-7. In force with `01R`.

## Task decomposition
### Task 7.1 — Evidence store + integrity
- Owned paths: `src/factory/evidence/store/**`. Deliverables: finalized integrity-protected evidence packages; retention linkage. Contracts: CTR-EVIDENCE-PACKAGE. Tests (evidence-integrity #31): integrity detection; finalized packages immutable; proportionate hashing. Evidence: evidence-store ETM. Completion: `01G §6/§2.18`.
### Task 7.2 — ETM system + verification engine + verdict logic (R5)
- Owned paths: `src/factory/verification/**`. Deliverables: per-criterion ETM (`01G §3.1`); verification engine; five-verdict logic (`01G §3.3`); anti-weakening (`01G §3.2`); flaky numeric policy (`01G §3.5`). Contracts: CTR-ETM, CTR-VERDICT. Tests: broken ETM link blocks promotion; package `PASS` only on complete coverage; anti-weakening/anti-gaming rejection; flaky ≤2 retries + `UNSTABLE` + quarantine. Evidence: verification ETM (VM-5). Completion: `01G` acceptance.
### Task 7.3 — Serialized integration coordinator (complete) + regression
- Owned paths: `src/factory/integration/**` (complete). Deliverables: serialized shared-change integration; cross-component + regression execution; scope-drift recovery. Tests (IP-4): serialized integration; regression/failure-path; scope-drift returns to last safe checkpoint. Evidence: integration ETM. Completion: `01D §3.8`, `04 §3-4`.
### Task 7.4 — Promotion Service + Promotion Package (finalize)
- Owned paths: `src/factory/promotion/**`. Deliverables: sole protected-ref writer (local/offline); complete Promotion Package validation. Contracts: CTR-PROMOTION-PACKAGE(finalize). Tests: sole-writer; offline-gate parity; package completeness; direct ref mutation → security event. Evidence: promotion ETM. Completion: `01I §3.2`, `01E §3.8`.
### Task 7.5 — Snapshot manager + retention + recovery drills (RM-3)
- Owned paths: `src/factory/recovery/snapshot/**`, `src/factory/retention/**`. Deliverables: single active rolling snapshot + candidate lifecycle (Factory-state only, GitHub excluded); rolling raw-session retention; recovery drills + failure simulations. Contracts: CTR-SNAPSHOT-MANIFEST, CTR-RETENTION-POLICY. Tests (snapshot #19, isolated-restore #20, crash #16): candidate restore-tested in isolation; failed candidate leaves active unchanged; **no GitHub overwrite**; retention hold blocks purge; Watchdog-loss/lease-fencing/restart-exhaustion sims. Evidence: recovery ETM (RM-3). Completion: `01M §3.9`, `01C §3-8`.

## Acceptance & handoff
Acceptance: `01G`(30)+`01M`(recovery)+`01C`(retention) PASS (VM-5/RM-3). Rollback boundary: single active rolling snapshot; failed activation preserves prior. Promotion gate: PH-7 exit + begin `01B` St.5 (Factory self-hosting). Handoff → PH-8.
