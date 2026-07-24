# Factory Documentation Index

**Status:** Active source map  
**Last updated:** July 24, 2026

## Authority order

When documents appear to conflict, use this order:

1. `PROJECT_DEFINITION.md` — governing purpose, boundaries, priorities, controls, and success criteria.
2. `docs/01-APPROVED-DECISIONS.md` — later decisions that explicitly resolve or supersede previously open items.
2R. `docs/01R-PLANNING-RESOLUTIONS-AND-AMENDMENTS.md` — approved planning resolutions (R1–R5) and decisions (autonomy, deletion, isolation). Explicitly supersedes the named clauses in `PROJECT_DEFINITION.md §21`, `01 §2/§3/§15`, `02 §4/§14`, and `05` Section 6 as listed in that file; this amendment record governs those clauses.
3. `docs/01A-LOCAL-BUILDER-STACK-DECISION.md` — approved Ollama, Aider, Dashboard, Monaco, file-explorer, IDE-independence, and OpenHands deferral decision. This file explicitly supersedes conflicting earlier runtime or IDE assumptions.
4. `docs/01B-SELF-HOSTING-TRANSITION-DECISION.md` — approved capability-by-capability migration from bootstrap tools into the local Builder.
5. `docs/01C-SESSION-EVIDENCE-AND-IMPROVEMENT-PACKETS.md` — approved disposable-session evidence, raw-log retention, monthly analysis, and user-controlled Improvement Packet rules.
6. `docs/01D-TASK-ENGINE-AND-PARALLEL-WORKSTREAMS.md` — approved three-workstream execution, controlled task branches, isolated lane checkouts, lane lifecycle, shared-contract ownership, immutable integration baselines, logical-conflict detection, deterministic scheduling, verified checkpoints, and evidence-backed integration remediation.
7. `docs/01E-SANDBOX-AND-ISOLATION.md` — approved non-executing read-only inspection, non-root isolation, prohibited privileges, scoped network and secret controls, trusted caches, untrusted-repository inspection, quarantined staging exports, Promotion Packages, bounded resources, and separately retained sandbox evidence.
8. `docs/01F-MEMORY-RECORDS-AND-RETENTION.md` — approved temporary and permanent memory boundaries, provenance, namespaces, supersession, retrieval authority, integrity, and record-retention rules.
9. `docs/01G-VERIFICATION-AND-EVIDENCE.md` — approved acceptance criteria, mandatory Evidence Traceability Manifests, verification anti-weakening controls, exact verdict and promotion semantics, deterministic unrelated-failure exceptions, numeric flaky-test policy, reproducibility, and artifact integrity.
10. `docs/01H-CONTROLLED-SELF-IMPROVEMENT.md` — approved evidence-provenance classification, complete packet lifecycle and staleness rules, protected control-plane implementations, deterministic impact and independence classifications, urgent-defect routing, hardened automatic rollback, monitoring, and complexity control.
11. `docs/01I-GIT-PROJECTS-AND-REPOSITORY-MANAGEMENT.md` — approved task-branch hierarchy, optional stage integration branches, local and offline protected-ref enforcement, Promotion Service authority, multi-repository baseline manifests, standardized commit trailers, releases, and destructive-operation rules.
12. `docs/01J-MODELS-ROUTING-AND-REASONING.md` — approved deterministic model routing, complete model fingerprints, model-neutral state, separate fallback execution provenance, executable Resource Scheduler limits, health-check triggers, benchmarks, and cloud-optional boundaries.
13. `docs/01K-TOOLS-PERMISSIONS-AND-SECURITY.md` — approved tool registry, least privilege, scoped approvals, secret handling, path safety, execution quotas, complete process-tree termination, tamper-evident audit chains, quarantine, sandbox-record separation, and emergency controls.
14. `docs/01L-DASHBOARD-UI-AND-OPERATOR-EXPERIENCE.md` — approved primary Dashboard, formal workstream state machine, complete approval cards, controlled terminal and Monaco editing, passive editor-adapter boundary, exact active execution identity, offline operation, and operator controls.
15. `docs/01M-RECOVERY-RELIABILITY-AND-WATCHDOG.md` — approved independently supervised Watchdog process, narrow intervention controls, monotonic heartbeats, staged resource thresholds, deterministic failure identity, durable journals, fenced leases, capability-scoped degradation, emergency reserve, and candidate-tested rolling snapshots.
16. `docs/01N-WINDOWS-ACTIVATION-INDEPENDENCE.md` — approved full Windows 11 Home operation regardless of activation status and explicit removal of activation from all Factory prerequisites and release gates.
17. `docs/01O-DEPLOYMENT-UPDATES-AND-RELEASE.md` — approved Windows 11 Home support profile, prerequisite classification, governed runtime-artifact acquisition, signed transactional updates, executable and state rollback, lifecycle failure testing, release provenance, uninstall ownership, and persistent-data protection rules.
18. `docs/01P-REPOSITORY-INTELLIGENCE-AND-GRAPH-MAPPING.md` — approved repository indexing, deterministic graph identity, schema versioning, stable-source publication, isolated semantic tooling, graph states, and verified traceability rules.
19. `docs/01Q-RESEARCH-SOURCES-AND-EXTERNAL-KNOWLEDGE.md` — approved research planning, claim-level evidence mapping, retained-evidence integrity, scoped network access, redaction, freshness states, and licensing-review boundaries.
20. `docs/02-FACTORY-ARCHITECTURE.md` — approved high-level Factory architecture and component boundaries.
21. `docs/03-MODEL-ROSTER.md` — approved local and hosted model assignments.
22. `docs/04-RECOVERY-POLICY.md` — checkpoint, rollback, drift, retry, and restart behavior.
23. `docs/05-BUILD-PLAN-MAP.md` — ordered planning and implementation sections.
24. `docs/06-BUILDER-INTERFACE-AND-LOCAL-TOOLCHAIN.md` — approved primary interface and local coding-tool boundaries.
25. Approved section specifications and implementation plans created later.
26. Code, tests, evidence, audit records, and release records produced from those plans.

A lower-ranked document cannot silently override a higher-ranked document. A later approved decision may supersede a specific earlier requirement only when the supersession is explicit.

## Current repository state

The repository contains the complete product definition, approved architecture records, the Section 1 specification and implementation plan, the approved local Builder interface and toolchain direction, the approved transition to a self-hosted local development workflow, and approved policies for evidence retention, isolated parallel-lane execution, lane lifecycle and checkpointing, shared-contract and integration-baseline governance, deterministic scheduling and conflict detection, non-executing repository inspection, prohibited sandbox privileges, scoped network and secret handling, trusted caches, quarantined staging and Promotion Packages, separately retained sandbox evidence, mandatory criterion-to-artifact traceability, verification anti-weakening, exact promotion verdicts, deterministic unrelated-failure handling, numeric flaky-test quarantine, evidence-provenance-aware Improvement Packets, packet staleness and lifecycle enforcement, protected control-plane implementations, urgent defect remediation, hardened automatic rollback, memory authority, task-branch and protected-ref governance, multi-repository consistency, deterministic model fingerprints and fallback provenance, executable model resource scheduling, bounded tool execution, tamper-evident audit chains, formal workstream transitions, complete approval context, passive editor integration, independently supervised Watchdog operation, fenced recovery, durable reconciliation, emergency storage protection, candidate-tested snapshots, Windows activation-independent operation, versioned deployment support, governed prerequisite and runtime-artifact acquisition, signed transactional updates, executable and state rollback, lifecycle failure testing, release provenance, uninstall ownership, repository intelligence, graph integrity, research, source evidence, external knowledge, privacy, and licensing-review boundaries. Product implementation has not started.

## Required future structure

```text
builder/
├── README.md
├── PROJECT_DEFINITION.md
├── docs/
│   ├── 00-DOCUMENTATION-INDEX.md
│   ├── 01-APPROVED-DECISIONS.md
│   ├── 01R-PLANNING-RESOLUTIONS-AND-AMENDMENTS.md
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
│   ├── 01N-WINDOWS-ACTIVATION-INDEPENDENCE.md
│   ├── 01O-DEPLOYMENT-UPDATES-AND-RELEASE.md
│   ├── 01P-REPOSITORY-INTELLIGENCE-AND-GRAPH-MAPPING.md
│   ├── 01Q-RESEARCH-SOURCES-AND-EXTERNAL-KNOWLEDGE.md
│   ├── 02-FACTORY-ARCHITECTURE.md
│   ├── 03-MODEL-ROSTER.md
│   ├── 04-RECOVERY-POLICY.md
│   ├── 05-BUILD-PLAN-MAP.md
│   ├── 06-BUILDER-INTERFACE-AND-LOCAL-TOOLCHAIN.md
│   ├── 10-IMPLEMENTATION-ROADMAP.md
│   ├── 11-CONTROLLED-GLOSSARY-AND-CROSSWALKS.md
│   ├── specifications/
│   ├── plans/
│   ├── planning/
│   ├── release/
│   ├── templates/
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