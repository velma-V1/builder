# Parallel-Workstream Map

**Status:** Derived/non-overriding reference (L25.D)
**Recorded:** July 24, 2026
**Sources:** `01R` R2, `01C §13`, `01D §1/§2/§3.4`, `docs/planning/DEPENDENCY-MAP.md`. In force with `01R`.

Default maximum **three** parallel major-stage workstreams (R2). Parallel activation is authorized only after this map records an independence proof per `01D §3.4` (file-path disjointness alone is not sufficient). Regenerated on any scope/ownership change; a parallel set is invalid until independence is re-proven.

## 1. Workstream declaration template (`01D §2.4`)
Each active workstream declares: owner · scope · inputs · outputs · owned contracts · completion gate · isolated checkout (worktree preferred, clone permitted) · resource reservation.

## 2. Approved parallel sets (v1)

### Set A — PH-4 ∥ PH-5 (after PH-3)
- **WS-A1 (routing):** owns model router, Resource Scheduler, model-exec records, Ollama/Aider adapters, quota ledger; owned paths `src/factory/routing/**`, `src/factory/models/**`; consumes frozen `tool-gateway`/`permission` interfaces from PH-3.
- **WS-A2 (isolation):** owns Git mgr, sandbox mgr, secret/network brokers, cache, staging; owned paths `src/factory/git/**`, `src/factory/sandbox/**`.
- **Independence proof (`01D §3.4`):** no shared components; no shared owned paths; no shared success/rollback metrics; no shared persistent state (routing writes model-exec records; isolation writes sandbox/staging records — disjoint); no shared migration ordering; no shared security boundary beyond the PH-3 permission interface, which is **frozen** before Set A starts; no shared resource bottleneck at admission (Resource Scheduler mediates GPU: ≤1 GPU-heavy). **Result: INDEPENDENT — parallel admission allowed.**

### Set B — PH-8 tri-split
- **WS-B1** Dashboard + graphs (`src/factory/dashboard/**`), **WS-B2** installer + updater (`installer/**`, `src/factory/update/**`), **WS-B3** packaging + release verification (`scripts/release/**`).
- **Independence proof:** disjoint components/paths; all consume read-only authoritative records; shared release-manifest contract is produced by WS-B3 and consumed by WS-B2 → **serialize the release-manifest hand-off** (WS-B3 before WS-B2 final), otherwise independent. **Result: INDEPENDENT with one serialized hand-off.**

## 3. Serialized (never parallel against the same artifact)
PH-1 Tasks 1→5; runtime-state DB schema + state machine (PH-2); Promotion Service + any protected-ref change (PH-7); all shared-contract/schema/migration changes; multi-workstream integration (PH-6/7 coordinator).

## 4. Integration gates
Cross-stage dependency approval · interface/contract compatibility · integration testing · conflict resolution (`01D §3.4` beyond files) · final system verification · promotion. The integration coordinator diagnoses and assigns remediation but **never edits source** (`01D §3.8`).

## 5. Lane checkout assignment
Every concurrent lane modifying the same repository receives its own worktree (preferred) or clone (`01D §2.8`); a branch alone is not sufficient isolation.
