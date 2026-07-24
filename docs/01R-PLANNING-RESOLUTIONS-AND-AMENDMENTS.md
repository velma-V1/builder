# Approved Planning Resolutions and Amendments

**Status:** Approved amendment record — supersedes the specific earlier clauses listed below
**Recorded:** July 24, 2026
**Authority:** Approved by the user during the seven-pass pre-implementation planning review and registered in `docs/00-DOCUMENTATION-INDEX.md`. Each supersession below is explicit, per the index change-control rule.

This record consolidates the resolutions (R1–R5) and decisions (A–C) approved before implementation begins. Where a named clause elsewhere conflicts with a statement here, **this record governs for that clause only**; every other governing requirement remains unchanged. Original text is preserved in place with a pointer to this record.

## R1 — Orchestrator / Watchdog split

**Supersedes:** `docs/01-APPROVED-DECISIONS.md §3` and `§15`, and `docs/02-FACTORY-ARCHITECTURE.md §4`, wherever they name "the watchdog" as the authoritative state writer.

**Authoritative statement:** The deterministic control-plane engine is the **Orchestrator**. The Orchestrator is the **sole authoritative writer** to the runtime-state database and owns every authoritative state transition. The **Watchdog** is a separate, independently supervised, normally read-only reliability supervisor (per `docs/01M`); it holds no writable authoritative-state connection and acts only through its narrow predefined control interface. Every prior "the watchdog is the sole authoritative writer" clause now refers to the Orchestrator. The Watchdog's supervisory authority is otherwise unchanged.

## R2 — Workstreams are the default execution unit

**Supersedes:** `docs/01-APPROVED-DECISIONS.md §2` ("three permanent parallel execution lanes … one Worker model; one Reviewer model"); realigns `docs/02-FACTORY-ARCHITECTURE.md §10` and `docs/05-BUILD-PLAN-MAP.md` Section 6.

**Authoritative statement:** Factory's default execution model is **up to three parallel major-stage workstreams** (design → implement → test → verify → handoff), per `docs/01C §13` and `docs/01D §1`. The permanent Worker/Reviewer paired-lane split is a **temporary special case** for a single unusually large, complex, or high-risk stage. The hosted Worker/Reviewer lanes remain **optional secondary capacity** (already per `docs/01A §11`, `02 §10`, `03 §4`). The maximum-three-parallel-unit cap and the isolated-checkout rule are unchanged.

## R3 — Improvements are approval-only

**Supersedes:** `PROJECT_DEFINITION.md §21` (automatic acceptance permission).

**Authoritative statement:** Factory may **automatically generate improvement proposals** and **test them in isolated sandboxes**, but it **never automatically applies** an improvement; application always requires user approval through the protected change process. The **only** automatic change is pre-approved rollback/restoration to a verified state (`docs/01H §2.20/§4.5`). §21's condition list is retained as *proposal-eligibility* criteria and its exclusion list as hard bars. This aligns §21 with `docs/01C §10`, `01F §15`, and `01H §1/§2.30`. Governing controls and their enforcement implementations change only through the separate architecture-change process, never ordinary Improvement Packets.

## R4 — Planning write base (operational; satisfied)

Planning artifacts are authored on branch `claude/factory-arch-planning-n1a7gn`, recreated from `agent/minimum-builder-shell-design` (the full governing corpus). Draft PR #7 is untouched. This record and its companion planning files are written on that base.

## R5 — Section 1 reconciliation (to apply when the Section 1 spec/plan are materialized)

The Section 1 specification (`docs/specifications/2026-07-23-section-1-requirements-contracts-design.md`) and implementation plan (`docs/plans/section-1-requirements-contracts.md`) must conform to the higher-authority supplements:

- **Verdicts:** adopt the `docs/01G §3.3` five-value set `PASS` / `FAIL` / `BLOCKED` / `INCONCLUSIVE` / `NOT_TESTABLE` (replacing the plan's `VERIFIED` / `UNVERIFIED` / `FAILED` / `NOT TESTABLE`).
- **Task risk class:** add `risk_class` to the Task Contract schema (`docs/01M §3.11`).
- **Evidence Traceability Manifest:** Section 1 verification emits a `docs/01G §3.1`-conformant ETM, not only a requirement-to-test matrix.
- **Deletion:** remove the Section 1 §4.5 automatic deletion of disposable artifacts (see Decision B).

## Decision A — Autonomy control assignment (resolves the open placement of `PROJECT_DEFINITION §8`)

The selectable **1%–100% autonomy** control is realized as a permission/approval-envelope parameter:

- **Permission enforcement** (`docs/01K`, Section 1 Permission Contract) scopes which automatic actions each autonomy level permits;
- **Approval engine** (`docs/01L §3.2`) determines which actions still require an approval card at that level;
- **Orchestration** (the Orchestrator) enforces the active level per task and records it in authoritative state;
- **Dashboard** (`docs/01L`) exposes the autonomy control and shows its current effect.

Protected decisions and permission boundaries remain in force at every level (`PD §8`). The autonomy level is carried on the Task and Permission contracts; its verification path is autonomy-boundary tests; its evidence obligation is the recorded level per task; its rollback treatment is that a level change is reversible and audited; its readiness gates are G5/G6. Primary implementation phase: **PH-3**; Dashboard surface: **PH-8**.

## Decision B — File deletion remains approval-required (confirms conservative C05)

`docs/01-APPROVED-DECISIONS.md §11` governs: the Factory must request user approval before deleting files. The Section 1 §4.5 automatic-deletion exception for disposable artifacts is **not adopted** and is removed from the Section 1 plan (R5). Automatic create/edit/install inside an approved disposable sandbox remain permitted; deletion of any file requires approval.

## Decision C — Windows-native execution excluded from v1

The v1 isolation path is **WSL2 + Docker Linux containers only**. **Restricted Windows-native execution is excluded from v1.**

**Supersedes for v1:** `PROJECT_DEFINITION §18` ("The final isolation design has not yet been selected" and the "Restricted Windows-native execution" option) and `docs/02-FACTORY-ARCHITECTURE.md §14` ("unless the approved task requires a restricted Windows-native environment" — that exception does not apply in v1). `docs/05-BUILD-PLAN-MAP.md` Section 5 sandboxes are WSL2 + Docker only. A future Windows-native path requires a separate approved architecture decision.

## Effect on authority order

This record is an approved-decisions amendment registered directly after `docs/01-APPROVED-DECISIONS.md` in the authority order. Its explicit supersessions apply to the named clauses only; every other governing requirement in `PROJECT_DEFINITION.md`, `01`, `02`, `05`, and all supplements remains in force. Product implementation has not started.
