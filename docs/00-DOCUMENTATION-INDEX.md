# Factory Documentation Index

**Status:** Active source map  
**Last updated:** July 23, 2026

## Authority order

When documents appear to conflict, use this order:

1. `PROJECT_DEFINITION.md` — governing purpose, boundaries, priorities, controls, and success criteria.
2. `docs/01-APPROVED-DECISIONS.md` — later decisions that explicitly resolve or supersede previously open items.
3. `docs/01A-LOCAL-BUILDER-STACK-DECISION.md` — approved Ollama, Aider, Dashboard, Monaco, file-explorer, IDE-independence, and OpenHands deferral decision. This file explicitly supersedes conflicting earlier runtime or IDE assumptions.
4. `docs/01B-SELF-HOSTING-TRANSITION-DECISION.md` — approved capability-by-capability migration from bootstrap tools into the local Builder.
5. `docs/01C-SESSION-EVIDENCE-AND-IMPROVEMENT-PACKETS.md` — approved disposable-session evidence, raw-log retention, monthly analysis, and user-controlled Improvement Packet rules.
6. `docs/01D-TASK-ENGINE-AND-PARALLEL-WORKSTREAMS.md` — approved major-stage workstreams, lane ownership, resource coordination, integration, and real-time model-testing rules.
7. `docs/01E-SANDBOX-AND-ISOLATION.md` — approved execution isolation, network, credentials, mounts, resource limits, promotion, and disposal rules.
8. `docs/01F-MEMORY-RECORDS-AND-RETENTION.md` — approved temporary and permanent memory boundaries, provenance, namespaces, supersession, retrieval authority, integrity, and record-retention rules.
9. `docs/01G-VERIFICATION-AND-EVIDENCE.md` — approved acceptance criteria, risk-based testing, baselines, reproducibility, verdicts, artifact integrity, and promotion-evidence rules.
10. `docs/01H-CONTROLLED-SELF-IMPROVEMENT.md` — approved proposal qualification, experimental testing, staged activation, rollback, monitoring, model-roster protection, and complexity-control rules.
11. `docs/01I-GIT-PROJECTS-AND-REPOSITORY-MANAGEMENT.md` — approved project records, controlled Git workspaces, branches, commits, pull requests, releases, and destructive-operation rules.
12. `docs/01J-MODELS-ROUTING-AND-REASONING.md` — approved deterministic model routing, model-neutral state, handoffs, fallback, health checks, benchmarks, and cloud-optional boundaries.
13. `docs/01K-TOOLS-PERMISSIONS-AND-SECURITY.md` — approved tool registry, least privilege, scoped approvals, secret handling, path safety, quarantine, audit, and emergency controls.
14. `docs/01L-DASHBOARD-UI-AND-OPERATOR-EXPERIENCE.md` — approved primary Dashboard, workstream visibility, approvals, controlled terminal and editing, offline operation, and operator controls.
15. `docs/01M-RECOVERY-RELIABILITY-AND-WATCHDOG.md` — approved independent monitoring, reconciliation, restart, containment, degraded operation, recovery drills, restore testing, and fail-closed reliability rules.
16. `docs/02-FACTORY-ARCHITECTURE.md` — approved high-level Factory architecture and component boundaries.
17. `docs/03-MODEL-ROSTER.md` — approved local and hosted model assignments.
18. `docs/04-RECOVERY-POLICY.md` — checkpoint, rollback, drift, retry, and restart behavior.
19. `docs/05-BUILD-PLAN-MAP.md` — ordered planning and implementation sections.
20. `docs/06-BUILDER-INTERFACE-AND-LOCAL-TOOLCHAIN.md` — approved primary interface and local coding-tool boundaries.
21. Approved section specifications and implementation plans created later.
22. Code, tests, evidence, audit records, and release records produced from those plans.

A lower-ranked document cannot silently override a higher-ranked document. A later approved decision may supersede a specific earlier requirement only when the supersession is explicit.

## Current repository state

The repository contains the complete product definition, approved architecture records, the Section 1 specification and implementation plan, the approved local Builder interface and toolchain direction, the approved transition to a self-hosted local development workflow, and approved policies for evidence retention, Improvement Packets, parallel major-stage execution, sandbox isolation, memory authority, verification, controlled self-improvement, Git and project management, model routing, tools and permissions, the Dashboard operator experience, and recovery, reliability, and Watchdog behavior. Product implementation has not started.

## Required future structure

```text
builder/
├── README.md
├── PROJECT_DEFINITION.md
├── docs/
│   ├── 00-DOCUMENTATION-INDEX.md
│   ├── 01-APPROVED-DECISIONS.md
│   ├── 01A-LOCAL-BUILDER-STACK-DECISION.md
│   ├── 01B-SELF-HOSTING-TRANSITION-DECISION.md
│   ├── 01C-SESSION-EVIDENCE-AND-IMPROVEMENT-PACKETS.md
│   ├── 01D-TASK-ENGINE-AND-PARALLEL-WORKSTREAMS.md
│   ├── 01E-SANDBOX-AND-ISOLATION.md
│   ├── 01F-MEMORY-RECORDS-AND-RETENTION.md
│   ├── 01G-VERIFICATION-AND-EVIDENCE.md
│   ├── 01H-CONTROLLED-SELF-IMPROVEMENT.md
│   ├── 01I-GIT-PROJECTS-AND-REPOSITORY-MANAGEMENT.md
│   ├── 01J-MODELS-ROUTING-AND-REASONING.md
│   ├── 01K-TOOLS-PERMISSIONS-AND-SECURITY.md
│   ├── 01L-DASHBOARD-UI-AND-OPERATOR-EXPERIENCE.md
│   ├── 01M-RECOVERY-RELIABILITY-AND-WATCHDOG.md
│   ├── 02-FACTORY-ARCHITECTURE.md
│   ├── 03-MODEL-ROSTER.md
│   ├── 04-RECOVERY-POLICY.md
│   ├── 05-BUILD-PLAN-MAP.md
│   ├── 06-BUILDER-INTERFACE-AND-LOCAL-TOOLCHAIN.md
│   ├── specifications/
│   ├── plans/
│   ├── decisions/
│   └── verification/
├── src/
├── tests/
├── config/
├── schemas/
├── scripts/
├── docker/
└── installer/
```

Directories are created only when their first approved file is added. Empty placeholder directories are not committed.

## Change-control rule

Every material decision must be recorded in the correct document before implementation relies on it. Unrecorded conversation assumptions are not implementation authority.