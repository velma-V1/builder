# PH-5 (Section 5) — Git, Worktree & Sandbox Isolation — Implementation Plan

**Status:** Approved planning order (L25.1) · **Governing:** `01I`, `01E`, `04`, `01M §3.11`, `01R` Dec C. Roadmap spec: `docs/10` PH-5. In force with `01R`. Runs ∥ PH-4 (Workstream Map Set A).

**Decision C applied:** all execution isolation is **WSL2 + Docker Linux containers only**; no Windows-native execution path is implemented or accepted.

## Task decomposition
### Task 5.1 — Branch/worktree lifecycle from approved baseline
- Owned paths: `src/factory/git/**`. Deliverables: controlled task branches from approved baseline; worktree/clone isolation; verified checkpoints; checkpoint commits (owned paths only). Contracts: CTR-BASELINE-MANIFEST, CTR-COMMIT-TRAILER. Tests (`01I` 18): branch/isolation; **no auto force-push/history-rewrite**; no protected-ref write; unexplained local changes block start. Evidence: git ETM. Completion: `01I §2/§3`.
### Task 5.2 — Non-root WSL2+Docker sandbox lifecycle
- Owned paths: `src/factory/sandbox/**`. Deliverables: per-workstream disposable sandboxes; non-root; hard resource limits; base-image versioning; disposal. Tests (sandbox-escape #7, privilege #8, Docker #): **no writable host-project mount**; no privileged/host-socket/host-namespace/nested control; **no Windows-native path** (Dec C); boundary-failure → destroy + security clearance (`04 §7`). Evidence: sandbox ETM (RM-2). Completion: `01E §2/§3.1-3.2`.
### Task 5.3 — Secret broker + network broker
- Owned paths: `src/factory/secret/**`, `src/factory/network/**`. Deliverables: ephemeral scoped credential injection + redaction; default-deny task-scoped network. Contracts: CTR-SECRET-REF, CTR-NETWORK-APPROVAL. Tests (secret #11, network-denial #12): secrets never embedded, revoked before disposal; network denied without contract, redirects can't escape, no inbound. Evidence: broker ETM. Completion: `01E §3.3-3.4`.
### Task 5.4 — Cache manager + quarantined staging
- Owned paths: `src/factory/cache/**`, `src/factory/staging/**`. Deliverables: immutable/content-addressed caches; staging as the only sandbox-output exit (inventory/hash/scan/scope-compare). Contracts: CTR-PROMOTION-PACKAGE(staging partial). Tests (cache-integrity #13, process-tree #14): cache immutable/credential-free; staging-only exit; inspection detects escapes/secrets/scope-violations; complete process-tree termination. Evidence: cache/staging ETM. Completion: `01E §3.5/§3.7`.

## Acceptance & handoff
Acceptance: `01E`(32)+`01I`(18)+`04 §7` PASS; Windows-native exclusion enforced (Dec C). Rollback boundary: sandboxes disposable; verified checkpoints; corruption preserves refs/reflog, no guessing. Promotion gate: PH-5 exit + begin `01B` St.4. Handoff → PH-6 (worktrees/sandboxes), PH-7 (staging → Promotion Service).
