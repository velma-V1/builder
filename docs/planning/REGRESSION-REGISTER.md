# Regression Register

**Document ID:** REGR-000
**Repository path:** `docs/planning/REGRESSION-REGISTER.md`
**Status:** Active — repair/regression ledger (established planning Pass 7)
**Authority level:** Derived index (records repairs + mandatory regression flags; overrides no source)
**Owner:** Every pass/task that performs a repair · **Established:** 2026-07-24
**Governing:** repair-first rule (`docs/planning/PH2-FAILURE-RECOVERY-ROLLBACK.md §2`, `04 §4`, `01G §3.2`).

## 1. Purpose

The single record of every deterministic repair applied after a failure — planning contradiction or, later,
implementation/test failure — and the mandatory regression verification each repaired area must receive.
Under the repair-first rule, an area is flagged here **even after the repair succeeds**, so a later pass or
session re-verifies it rather than trusting that it was fixed once.

## 2. Row schema

Each entry records: **Regr ID · Date · Pass/Task · Failure ID · Original failure · Root cause · Affected area
(files/components/tasks) · Reverted state · Repair applied · Files changed · Tests re-run · Verification
re-run · Result · Evidence location · Regression flag (OPEN/CLEARED) · Remaining risk.** A `Regression flag`
is `OPEN` until the required regression verification has actually been run and passed in a later
pass/session, then `CLEARED` with a pointer to the evidence.

## 3. Register

**No repairs recorded.** Across PH-2 planning Passes 1–7, every consistency audit and realignment produced no
contradiction requiring deterministic repair (each pass verdict was `PASS_WITH_NONBLOCKING_GAPS` or
`READY_...`, with "Repairs Attempted: none"). Two non-repair items are noted for continuity:

- The Pass-4 CMP-ORCH ↔ CMP-JOURNAL/CMP-LEASE ownership overlap was a **layering clarification** resolved by
  R1, not a repair (no document was inconsistent once R1 is applied). Not a regression row.
- The stale-branch line in `HANDOFF-PH1.md §4` was corrected in commit `4920a2b` **before** this register
  existed and outside the pass framework; recorded here for completeness, flag `CLEARED` (the fix is a
  one-line doc correction, self-verifying by inspection).

| Regr ID | Date | Pass/Task | Failure ID | Affected area | Repair | Regression flag |
|---|---|---|---|---|---|---|
| REGR-0001 | 2026-07-24 | pre-framework | (doc) | `HANDOFF-PH1.md §4` stale branch ref | corrected to `claude/builder-handoff-pr8-inc9p8` (commit `4920a2b`) | CLEARED (inspection) |

## 4. Update rules

Append a row for every repair performed under the repair-first rule. Never delete a row; when a regression
flag is verified, change it to `CLEARED` with an evidence pointer (do not remove the row). At the start of
each pass, review all `OPEN` flags and clear any whose regression verification has since passed.
