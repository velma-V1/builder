# PH-8 (Section 8) — Complete Dashboard, Packaging & Installation — Implementation Plan

**Status:** Approved planning order (L25.1) · **Governing:** `01L`, `01P`, `01O`, `01N`, `PD §14-15`. Roadmap spec: `docs/10` PH-8. In force with `01R`. Release-line detail: `docs/release/*`.

## Task decomposition
### Task 8.1 — Complete Dashboard + selectable panels + autonomy surface (Dec A)
- Owned paths: `src/factory/dashboard/**` (complete). Deliverables: all `PD §14` panels; progressive disclosure; central approval queue; **autonomy control surface** (Dec A); offline; remote/telemetry off by default. Tests (`01L` 21): panel/state-machine integrity; no hidden activity; crash-recovery from backend; autonomy control visible. Evidence: dashboard ETM. Completion: `01L` acceptance.
### Task 8.2 — Repository-intelligence index + four graph views
- Owned paths: `src/factory/graph/**`, `src/factory/repoindex/**`. Deliverables: derived rebuildable indexes tied to exact source state; source/agent-workflow/live-execution/architecture graphs (`PD §15`). Contracts: CTR-GRAPH-INDEX. Tests (graph-integrity #33): deterministic node identity; mixed-state not CURRENT; traceability VERIFIED only via approved means; findings cannot auto-trigger code. Evidence: graph ETM. Completion: `01P` acceptance.
### Task 8.3 — Guided installer + prerequisite acquisition (Win11 Home ±activation)
- Owned paths: `installer/**`, `src/factory/install/**`. Deliverables: guided installer; versioned support profile; REQUIRED/RECOMMENDED/INFORMATIONAL checks; approval-gated prerequisite/model acquisition. Tests (installer #23, Windows-Home #26): **unactivated install/lifecycle passes**; **no activation gate**; prerequisite classification behavior; minimal host mod. Evidence: install ETM. Completion: `01O §2/§3.1-3.3`, `01N`.
### Task 8.4 — Updater + signing + snapshot-gated staged updates
- Owned paths: `src/factory/update/**`. Deliverables: signed/hash-verified/staged/transactional updates; pre-update snapshot gate; executable rollback window. Tests (updater/rollback #21, migration #22): signature rejection; snapshot-gate blocks update without verified snapshot; executable rollback until commitment; incompatible downgrade fails closed. Evidence: update ETM (RM-4). Completion: `01O §2.18-30/§3.5-3.6`.
### Task 8.5 — Packaging + release verification (stable gate)
- Owned paths: `scripts/release/**`, `src/factory/release/**`. Deliverables: packaging from clean commit (SBOM/license/vuln/immutable digests); lifecycle + failure-path release verification; release verdict. Contracts: CTR-RELEASE-MANIFEST. Tests (release-reproducibility #35, uninstall #24, system #3): clean-machine install (IP-5) without Codex/VS Code/OpenHands/hosted; provenance completeness; **stable = zero critical/high**; verdict `PASS/FAIL/BLOCKED/INCONCLUSIVE`. Evidence: release package (VM-6). Completion: `01O §6/§3.7-3.9`.

## Acceptance & handoff
Acceptance: `01L`(21)+`01P`(10)+`01O`(17) PASS (VM-6/RM-4); stable-release conditions per `docs/release/RELEASE-PLAN.md §6` and `docs/10 §16` (self-hosting complete, VELMA build achievable). Rollback boundary: executable rollback + Factory-state snapshot; incompatible downgrade fails closed; GitHub repos untouched. Promotion gate: stable release verdict + operator release approval.
