# Factory Documentation Index

**Status:** Active source map  
**Last updated:** July 23, 2026

## Authority order

When documents appear to conflict, use this order:

1. `PROJECT_DEFINITION.md` — governing purpose, boundaries, priorities, controls, and success criteria.
2. `docs/01-APPROVED-DECISIONS.md` — later decisions that explicitly resolve or supersede previously open items.
3. `docs/01A-LOCAL-BUILDER-STACK-DECISION.md` — approved Ollama, Aider, Dashboard, Monaco, file-explorer, IDE-independence, and OpenHands deferral decision. This file explicitly supersedes conflicting earlier runtime or IDE assumptions.
4. `docs/02-FACTORY-ARCHITECTURE.md` — approved high-level Factory architecture and component boundaries.
5. `docs/03-MODEL-ROSTER.md` — approved local and hosted model assignments.
6. `docs/04-RECOVERY-POLICY.md` — checkpoint, rollback, drift, retry, and restart behavior.
7. `docs/05-BUILD-PLAN-MAP.md` — ordered planning and implementation sections.
8. `docs/06-BUILDER-INTERFACE-AND-LOCAL-TOOLCHAIN.md` — approved primary interface and local coding-tool boundaries.
9. Approved section specifications and implementation plans created later.
10. Code, tests, evidence, audit records, and release records produced from those plans.

A lower-ranked document cannot silently override a higher-ranked document. A later approved decision may supersede a specific earlier requirement only when the supersession is explicit.

## Current repository state

The repository contains the complete product definition, approved architecture records, the Section 1 specification and implementation plan, and the approved local Builder interface and toolchain direction. Product implementation has not started.

## Required future structure

```text
builder/
├── README.md
├── PROJECT_DEFINITION.md
├── docs/
│   ├── 00-DOCUMENTATION-INDEX.md
│   ├── 01-APPROVED-DECISIONS.md
│   ├── 01A-LOCAL-BUILDER-STACK-DECISION.md
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