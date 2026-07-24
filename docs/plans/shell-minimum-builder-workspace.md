# PH-S — Minimum Builder Shell — Implementation Plan

**Status:** Approved planning order (L25.1) · **Milestone between PH-1 and PH-2**
**Recorded:** July 24, 2026 · **Governing:** `01A §12`, `06 §11`, `01L`, `01B` St.0. Roadmap spec: `docs/10` PH-S. In force with `01R`.

Scope/exclusions/gates per `docs/10 §PH-S`. This plan decomposes the milestone into tasks. All writes pass the safe file-op boundary; the shell is a client of the control plane and gains no authority (`06 §3`).

## Task decomposition
### Task S.1 — Dashboard frame + built-in file explorer + Monaco
- Owned paths: `src/factory/dashboard/frame/**`, `src/factory/dashboard/explorer/**`, `src/factory/dashboard/editor/**`. Deliverables: launchable frame; project-tree with Git/ownership/protected status; Monaco open/edit/tabs/diff. Interfaces: read-only state subscription; controlled write-request submit. Deps: PH-1 contracts (Ownership/Permission). Tests: tree loads with correct status flags; Monaco save routes through control boundary (no direct write); read-only/protected-file enforcement. Evidence: shell-frame ETM. Completion: `06 §11` open/edit/diff/save proofs.
### Task S.2 — Safe file-operation boundary + controlled terminal
- Owned paths: `src/factory/fileops/**`, `src/factory/dashboard/terminal/**`. Deliverables: minimal safe file-op service (path canonicalization, ownership check); controlled terminal view. Deps: PH-1; minimal permission slice. Tests: path-safety (traversal/symlink/reserved-name blocked); terminal shows sandbox output; no bypass. Evidence: file-op + terminal ETM. Completion: no-bypass proven.
### Task S.3 — Ollama health + Aider bounded-task bridge (minimal)
- Owned paths: `src/factory/models/ollama_adapter/**`, `src/factory/workers/aider_bridge/**`. Deliverables: Ollama health/model-status; one bounded Aider+Ollama coding task under permission. Deps: PH-1; minimal permission/route slice. Tests: Ollama health check; one bounded Aider task edits only owned paths; runs without hosted providers. Evidence: bounded-task ETM. Completion: `01A §13` #3 (bounded Aider task) proven.
### Task S.4 — Task/diff/test/approval/checkpoint panels + disabled IDE adapter
- Owned paths: `src/factory/dashboard/panels/**`, `config/ide-adapter.yaml`. Deliverables: panels; IDE-adapter config present but disabled by default. Deps: S.1–S.3. Tests: panels reflect authoritative state; **IDE adapter disabled by default**; removing every external IDE leaves the shell functional. Evidence: shell acceptance package. Completion: `01A §13` #5–6.

## Acceptance & handoff
Acceptance: `01A §13` (1–7) and `06 §11` proofs; runs without Codex/VS Code/OpenHands/hosted (IP-1). Rollback boundary: shell additive; disable reverts to bootstrap tools. Promotion gate: operator approval to begin `01B` St.1 cutover. Handoff: `docs/templates/handoff/SECTION-HANDOFF.template.md` → PH-2/PH-3/PH-4 consume the minimal adapters/file-op as they build full versions.
