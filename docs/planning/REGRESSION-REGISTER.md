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
| REGR-0002 | 2026-07-24 | Pass 8 | THR-PH2-02 | security control without verification: append-only journal triggers (`task_state_events`) specified in the Task 2.2 migration DDL but untested | added security test SEC-PH2-02 (direct `UPDATE`/`DELETE` on `task_state_events` must raise) to PLAN-S2 Task 2.2 + VEP-PH2 §2 (T-PH2-SEC2) + SEC-PH2 §5 | **OPEN** — clear when SEC-PH2-02 is implemented and passes during PH-2 implementation (Task 2.2/2.6) |
| REGR-0003 | 2026-07-24 | Pass 9 | (migration verification) | migration without verification: PH-2 defines 3 runtime migrations but the runner's transactional-safety behavior (`01O §2.19`: version recorded only on success; failed migration leaves no partial schema) had no explicit test | added migration-runner test (T-PH2-MIG1) to PLAN-S2 Task 2.2 + VEP-PH2 §2 | **OPEN** — clear when T-PH2-MIG1 is implemented and passes during PH-2 implementation (Task 2.2/2.6) |

### REGR-0002 detail (repair-first record)

- **Failure / finding:** append-only enforcement of `task_state_events` is a declared security control
  (THR-PH2-02, ASSET-PH2-JOURNAL) but had no explicit verification — violates "no security control without
  verification."
- **Root cause:** the Task 2.2 test list covered the `mode=ro` reader authorizer but not the DDL-level
  `BEFORE UPDATE/DELETE` triggers (a distinct control that also blocks a *writable* connection).
- **Affected area:** `docs/plans/section-2-task-queue-and-state-machine.md` (Task 2.2 tests),
  `docs/planning/PH2-VERIFICATION-EVIDENCE-PROMOTION.md` (§2), `docs/planning/PH2-SECURITY-TRUST-BOUNDARIES.md`
  (§5 SEC-PH2-02).
- **Reverted state:** none needed (planning-doc addition, not a code revert).
- **Repair applied:** added SEC-PH2-02 test specification in all three places; mapped to THR-PH2-02.
- **Files changed:** the three docs above.
- **Tests re-run / verification re-run:** planning-consistency audit re-run (path/reference checks) — passes.
- **Result:** control now has a verification path.
- **Evidence location:** this register + the SEC-PH2 §7 repair note + commit history.
- **Regression flag:** OPEN — the actual test does not exist yet (no PH-2 product code); it will be authored
  and must pass in PH-2 implementation, at which point this flag is CLEARED with an ETM pointer.
- **Remaining risk:** low — the control (triggers) is already in the migration DDL; only its *test* was
  missing, now specified.

## 4. Update rules

Append a row for every repair performed under the repair-first rule. Never delete a row; when a regression
flag is verified, change it to `CLEARED` with an evidence pointer (do not remove the row). At the start of
each pass, review all `OPEN` flags and clear any whose regression verification has since passed.
