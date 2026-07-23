# Factory Documentation Index

**Status:** Active source map  
**Last updated:** July 22, 2026

## Authority order

When documents appear to conflict, use this order:

1. `PROJECT_DEFINITION.md` — governing purpose, boundaries, priorities, controls, and success criteria.
2. `docs/01-APPROVED-DECISIONS.md` — later decisions that explicitly resolve or supersede previously open items.
3. `docs/02-FACTORY-ARCHITECTURE.md` — approved high-level Factory architecture and component boundaries.
4. `docs/03-MODEL-ROSTER.md` — approved local and hosted model assignments.
5. `docs/04-RECOVERY-POLICY.md` — checkpoint, rollback, drift, retry, and restart behavior.
6. `docs/05-BUILD-PLAN-MAP.md` — ordered planning and implementation sections.
7. Approved section specifications and implementation plans created later.
8. Code, tests, evidence, audit records, and release records produced from those plans.

A lower-ranked document cannot silently override a higher-ranked document.

## Current repository state

The repository currently contains the complete product definition and approved architecture records. Implementation code has not started.

## Required future structure

```text
builder/
├── README.md
├── PROJECT_DEFINITION.md
├── docs/
│   ├── 00-DOCUMENTATION-INDEX.md
│   ├── 01-APPROVED-DECISIONS.md
│   ├── 02-FACTORY-ARCHITECTURE.md
│   ├── 03-MODEL-ROSTER.md
│   ├── 04-RECOVERY-POLICY.md
│   ├── 05-BUILD-PLAN-MAP.md
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