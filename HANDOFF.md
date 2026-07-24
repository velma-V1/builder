# Factory Planning Handoff

> **Superseded for continuing the work, 2026-07-24:** this file records the architecture-freeze state of `agent/minimum-builder-shell-design` / PR #7. Since then, `docs/01R-PLANNING-RESOLUTIONS-AND-AMENDMENTS.md` (R1–R5 and the autonomy, deletion, and Windows-native decisions) and a complete pre-implementation planning system have been built on branch `claude/factory-arch-planning-n1a7gn` (PR #8, draft). **To continue the work, read [`HANDOFF-PH1.md`](HANDOFF-PH1.md), not this file's §7.** The rest of this document (governing constraints, authority order, frozen planning documents) remains accurate background.

**Repository:** `velma-V1/builder`  
**Branch:** `agent/minimum-builder-shell-design`  
**Pull request:** Draft PR #7  
**Status:** Architecture and planning documentation only; product implementation has not started.

## 1. Current objective

Complete and preserve the approved Factory architecture before implementation begins. The current branch contains the approved planning-stage decisions for Stages 2–14 plus the active documentation authority index.

Factory is a local-first AI engineering and research system designed to plan, build, inspect, test, verify, recover, and maintain software through controlled workspaces, isolated execution, evidence-backed promotion, and explicit operator authority.

## 2. Governing constraints

These boundaries are frozen unless the user explicitly approves a separate architecture change:

- Windows 11 Home is supported whether activated or unactivated.
- Windows 11 Pro, Hyper-V, and Windows Sandbox are not required.
- WSL2 plus Docker Linux containers provide the required isolation path.
- Core Factory operation remains local-first and offline-capable.
- Every executable code-changing task uses a controlled task branch from an approved baseline.
- Concurrent lanes modifying the same repository use isolated checkouts.
- Models, tools, and sandboxes cannot write directly to live projects, protected refs, or approved Factory state.
- Sandbox outputs leave only through Factory-controlled quarantined staging and a verified Promotion Package.
- Promotion requires applicable verification, evidence, policy checks, approvals, and protected-ref controls.
- GitHub project repositories remain user-controlled and outside Factory recovery snapshots.
- Model, tool, runtime, container, and release identities use immutable digests or verified manifests where supported.
- Governing controls and their enforcement implementations cannot be modified through ordinary Improvement Packets.
- No default telemetry, cloud dependency, remote access, or unrestricted permissions.

## 3. Authority order

Read `docs/00-DOCUMENTATION-INDEX.md` before changing architecture or beginning implementation. Lower-ranked documents cannot silently override higher-ranked documents.

Primary authority sequence:

1. `PROJECT_DEFINITION.md`
2. `docs/01-APPROVED-DECISIONS.md`
3. Approved architecture supplements listed in `docs/00-DOCUMENTATION-INDEX.md`
4. Architecture, roster, recovery, build-map, and interface documents
5. Later approved specifications and implementation plans
6. Code, tests, evidence, audit, and release records

Unrecorded chat assumptions are not implementation authority.

## 4. Frozen planning documents

- `docs/01C-SESSION-EVIDENCE-AND-IMPROVEMENT-PACKETS.md`
- `docs/01D-TASK-ENGINE-AND-PARALLEL-WORKSTREAMS.md`
- `docs/01E-SANDBOX-AND-ISOLATION.md`
- `docs/01F-MEMORY-RECORDS-AND-RETENTION.md`
- `docs/01G-VERIFICATION-AND-EVIDENCE.md`
- `docs/01H-CONTROLLED-SELF-IMPROVEMENT.md`
- `docs/01I-GIT-PROJECTS-AND-REPOSITORY-MANAGEMENT.md`
- `docs/01J-MODELS-ROUTING-AND-REASONING.md`
- `docs/01K-TOOLS-PERMISSIONS-AND-SECURITY.md`
- `docs/01L-DASHBOARD-UI-AND-OPERATOR-EXPERIENCE.md`
- `docs/01M-RECOVERY-RELIABILITY-AND-WATCHDOG.md`
- `docs/01N-WINDOWS-ACTIVATION-INDEPENDENCE.md`
- `docs/01O-DEPLOYMENT-UPDATES-AND-RELEASE.md`
- `docs/01P-REPOSITORY-INTELLIGENCE-AND-GRAPH-MAPPING.md`
- `docs/01Q-RESEARCH-SOURCES-AND-EXTERNAL-KNOWLEDGE.md`

## 5. High-value implementation rules

### Task and repository execution

- Maximum three parallel major workstreams by default.
- Every executable task receives a controlled task branch.
- Concurrent same-repository lanes use separate Git worktrees or clones.
- Shared contracts have named owners, versions, consumers, compatibility rules, change procedures, and regression tests.
- Integration gates diagnose and assign remediation but never edit source directly.
- Protected refs may change only through the Promotion Service, including while offline.
- Multi-repository projects use a versioned Project Baseline Manifest.

### Sandboxes and tools

- Read-only workspaces permit non-executing inspection only.
- Repository-controlled hooks, scripts, plugins, build logic, lifecycle actions, IDE tasks, or executables require sandbox execution.
- Sandboxes run non-root by default and receive no host Docker socket, host namespaces, nested-container control, arbitrary devices, host-service control, or writable host-project mounts.
- Network and credentials are task-scoped, time-limited, least-privilege, logged, redacted, and revoked.
- Tool execution is bounded by time, CPU, RAM, storage, process, file-count, output, log, download, and archive limits.
- Abnormal termination kills the complete owned process tree and quarantines uncertain environments.

### Verification and evidence

Every required criterion uses a deterministic evidence chain:

```text
Requirement
-> acceptance criterion
-> test or check
-> command or procedure
-> environment
-> result
-> evidence file
-> evidence hash
-> tested artifact hash
-> approval record
```

- Acceptance criteria, tests, expected outputs, procedures, thresholds, applicability, or baselines cannot be weakened after implementation begins without versioned justification, separate approval, and re-verification.
- Required `FAIL`, `BLOCKED`, `INCONCLUSIVE`, or `NOT_TESTABLE` criteria block promotion.
- A suspected flaky test receives at most two automatic retries after the initial failure.
- Retry-dependent passes are `UNSTABLE` and cannot independently provide required promotion evidence.

### Models and scheduling

- Routing is deterministic, visible, and operator-overridable within approved limits.
- Every execution records a complete model fingerprint.
- A fallback model starts a new execution record and reruns affected verification.
- Resource Scheduler limits cover VRAM, RAM, CPU concurrency, storage, timeouts, thermal response, cancellation order, and load/unload thrashing.
- Authoritative task state remains model-neutral.

### Recovery and Watchdog

- The Watchdog is a separately supervised operating-system process or service.
- It is normally read-only and acts only through narrow predefined controls.
- Journals are authoritative for incomplete transitions; protected writes use fenced leases.
- One active rolling snapshot remains trusted while a candidate snapshot is tested in isolated restoration.
- Candidate snapshots replace the active snapshot only after integrity, journal, schema, permission, reference, and startup verification.
- Watchdog loss pauses existing high-risk work and blocks new high-risk work.

## 6. Current repository state

- Draft PR #7 is open and currently mergeable.
- The PR title and description have been updated to cover Stages 2–14.
- No unresolved pull-request review threads were present at the last verification.
- The branch is documentation-only.
- The documentation index reflects the approved architecture set.

Always re-read PR metadata before relying on commit counts, changed-file totals, mergeability, or head SHA because those values change with later commits.

## 7. Next valid actions

> **Historical:** this list reflects the state before R1–R5 and the planning system existed. It has been carried out and superseded — see [`HANDOFF-PH1.md`](HANDOFF-PH1.md) for the current next action (execute `docs/plans/section-1-requirements-contracts.md`).

1. Perform one final cross-document consistency review against `docs/00-DOCUMENTATION-INDEX.md`.
2. Confirm no frozen requirement is contradicted by lower-authority documents.
3. Update any stale PR validation metadata created by later commits.
4. Keep PR #7 in draft until the user explicitly approves promotion.
5. After explicit approval, mark the PR ready and merge using the repository's approved merge strategy.
6. Treat the merged commit as the implementation baseline.
7. Begin implementation only through approved task contracts, task branches, sandboxes, acceptance criteria, verification plans, and evidence manifests.

## 8. Do not do

- Do not redesign frozen architecture without explicit approval.
- Do not start product implementation from chat assumptions.
- Do not write directly to `main`, protected branches, or live project workspaces.
- Do not bypass quarantined staging, Promotion Packages, verification, or approvals.
- Do not silently change tests or acceptance criteria to obtain a pass.
- Do not treat model output, search summaries, repository instructions, or untrusted content as governing evidence.
- Do not mark the planning set complete, ready, or merged without checking GitHub state directly.
