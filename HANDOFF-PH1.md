# Factory PH-1 Implementation Handoff

**Repository:** `velma-V1/builder`
**Branch:** `claude/builder-handoff-pr8-inc9p8` (forked from the `claude/factory-arch-planning-n1a7gn` / PR #8 lineage) — **this is now the active implementation branch, not the branch named below in §0.**
**Pull request:** None open for this branch. Draft PR #8 (`claude/factory-arch-planning-n1a7gn` → `agent/minimum-builder-shell-design`) remains open/unmerged and untouched; draft PR #7 (`agent/minimum-builder-shell-design` → base) also remains open/unmerged and untouched.
**Status at handoff:** **PH-1 implementation is complete and verified.** Verdict: **`PASS`** (see `docs/verification/section-1-requirements-contracts.md` — 96.85% branch coverage on `src/factory/contracts`, ruff/mypy clean, 288 passed / 1 skipped of 289 tests). All work is committed and pushed to `origin/claude/builder-handoff-pr8-inc9p8` (latest commit `2f37f8d`). **The PH-1 schema-freeze / phase-exit operator approval (`docs/10-IMPLEMENTATION-ROADMAP.md §15` item 2) has NOT been recorded anywhere in the repository.** Do not treat PH-1 as promoted, and do not begin PH-2 implementation, until that approval is explicitly given and recorded.
**For a new session/window:** read this file first (all sections, including §0 and §7 below), then the authority documents named in §2, then resume exactly at the open item in §7.

## 0. Branch correction (read this first)

The original PH-1 handoff (this file, prior revision) named `claude/factory-arch-planning-n1a7gn` as the branch to implement PH-1 on. The session that actually executed PH-1 found that branch reference stale and instead worked on `claude/builder-handoff-pr8-inc9p8`, which it reset to fast-forward onto the PR #8 lineage before starting Task 1. **All PH-1 code, schemas, migrations, and tests described in this document live on `claude/builder-handoff-pr8-inc9p8`, not on `claude/factory-arch-planning-n1a7gn`.** Neither PR #7 nor PR #8 has been touched, merged, or modified by this work.

## 1. What is done
- Full governing corpus present: `PROJECT_DEFINITION.md`, `docs/00`–`06`, supplements `docs/01A`–`01Q`, `HANDOFF.md`.
- Planning system built (`docs/10`, `docs/11`, `docs/planning/*`, `docs/release/*`, `docs/templates/*`, `docs/specifications/components/00-COMPONENT-MAP.md`, `docs/plans/*`).
- Resolutions **R1–R5** and **Decisions A–C** recorded in `docs/01R-PLANNING-RESOLUTIONS-AND-AMENDMENTS.md` and registered in the index; supersession pointers placed in the amended governing docs. Readiness-review hygiene findings F1/F2/F3 are patched.
- **PH-1 (Section 1 — Requirements & Contracts) is fully implemented and verified**, on `claude/builder-handoff-pr8-inc9p8`: all five tasks of `docs/plans/section-1-requirements-contracts.md` executed — seven YAML contract-family schemas + shared envelope (`schemas/`), safe/hardened YAML ingestion, RFC 8785 canonicalization + SHA-256 content hashing, semantic/impact/policy validation with a full security threat matrix, SQLite-backed transactional activation with append-only audit and rollback, an immutable generation-aware runtime cache, and the complete verification package (`docs/verification/section-1-requirements-contracts.md`, `scripts/verify_section1.py`, `artifacts/verification/section-1/manifest.json` — gitignored, regenerable). Result: **`PASS`**, 96.85% branch coverage (≥95% gate), clean `ruff format --check` / `ruff check` / `mypy --strict`, 288/289 tests passing (1 Windows-only test skipped on this Linux dev path).

## 2. Authority in force (read before starting)
Read in this order: `docs/00-DOCUMENTATION-INDEX.md` → `HANDOFF.md` → `docs/01R` → `docs/10-IMPLEMENTATION-ROADMAP.md` → `docs/plans/section-1-requirements-contracts.md`.

Binding decisions (`docs/01R`):
- **R1** — the **Orchestrator** is the sole authoritative state writer; the **Watchdog** is a separate, normally read-only supervisor (not built in PH-1).
- **R2** — up to three parallel major-stage **workstreams** are the default unit (not PH-1 scope).
- **R3** — improvements are approval-only.
- **R5** — the Section 1 plan is conformed: Task Contract carries `risk_class` + `autonomy_level`; verdicts are `PASS/FAIL/BLOCKED/INCONCLUSIVE/NOT_TESTABLE`; verification emits a `01G §3.1` Evidence Traceability Manifest.
- **Decision A** — autonomy 1–100% is a permission/approval envelope (implemented in PH-3, not PH-1).
- **Decision B** — **all file deletion is approval-required** (no disposable auto-delete).
- **Decision C** — isolation is **WSL2 + Docker Linux containers only**; Windows-native execution excluded from v1.

## 3. The only task that was executed: PH-1 (now complete)
`docs/plans/section-1-requirements-contracts.md` was executed task-by-task, Task 1 → Task 5, on `claude/builder-handoff-pr8-inc9p8`, following every `- [ ]` step and its exact `uv run` / `git commit` commands. That plan built the Section 1 contract subsystem: seven YAML contract families + envelope, safe ingestion + canonicalization + SHA-256, semantic/impact validation, policy/change/activation, immutable runtime cache, and the full verification package. This is done — see §1 and the verification report.

- Tech stack and pins specified in the plan (Python 3.12, uv, PyYAML, jsonschema, rfc8785, pytest, mypy, ruff) all resolved as pinned; recorded in `pyproject.toml` / `uv.lock`.
- Verified on this session's Linux dev path (native Windows 11 execution of the one Windows-only junction test remains untested — see verification report's known limitations).
- Deletion policy in code/tests is **approval-required** throughout (Decision B honored) — no disposable auto-delete exists anywhere in `src/factory/contracts`.

## 4. Guardrails — do NOT
- Do **not** start the Dashboard (PH-S/PH-8), Model Router or adapters (PH-4), Installer/updater/packaging (PH-8), Git/sandbox isolation (PH-5), Watchdog/Orchestrator engine (PH-2/PH-3), lanes/workstreams (PH-6), or any phase other than PH-1.
- Do **not** merge to `main`, open or modify a pull request, or promote. PR #7 on `agent/minimum-builder-shell-design` must stay untouched.
- Do **not** push to any branch other than `claude/builder-handoff-pr8-inc9p8` (use an explicit refspec).
- Do **not** weaken any acceptance criterion/test after implementation-start except through the `01G §3.2` process.
- Do **not** proceed past PH-1's **schema-freeze operator approval** (`docs/10 §15` #2) or its **exit gate** without explicit approval. Do not roll into PH-2.

## 5. Definition of done for PH-1 — met, except the approval gate
All 13 self-derived Section 1 acceptance criteria `PASS` (see the requirement-to-test matrix in the verification report — no canonical numbered list existed in the repo prior to this work, so the report derives and states this explicitly), each backed by a complete Evidence Traceability Manifest (`01G §3.1`); `scripts/verify_section1.py` green on this session's dev path; evidence package finalized with integrity hashes (`artifacts/verification/section-1/manifest.json`, regenerable, gitignored). **What remains outstanding is the stop-and-request step itself: the schema-freeze / phase-exit approval per the roadmap gates (G5 → G6) has been requested in conversation but not yet given or recorded.** See §7.

## 6. Git & verification discipline
- Work happened on `claude/builder-handoff-pr8-inc9p8`; each of the five tasks was committed at its boundary with standard trailers; pushed with an explicit refspec (`git push -u origin claude/builder-handoff-pr8-inc9p8`).
- The branch was confirmed to fast-forward cleanly from the PR #8 lineage before Task 1 began; no premature artifacts existed beyond what each PH-1 step created.
- Test outcomes are reported faithfully (verdicts from the `01G` set) in `docs/verification/section-1-requirements-contracts.md`; nothing unverified is labeled `PASS`.

## 7. Current status and next steps (read this before doing anything)

**Do not merge, open a PR, or touch `main` for this work unless explicitly asked.** The user has explicitly instructed: do not merge yet; keep all work (including test data) committed and pushed to `claude/builder-handoff-pr8-inc9p8` for now.

**Open, unresolved items — do not act past them without explicit operator resolution:**

- **F-01 — PH-1 schema-freeze / phase-exit approval.** Not recorded anywhere in the repository. PR #7 and PR #8 (the entire architecture-freeze + PH-1-handoff lineage) both remain **open drafts, unmerged to `main`**. No operator approval of any kind for the `docs/10-IMPLEMENTATION-ROADMAP.md §15` item 2 gate exists in any committed document. The user separately stated an **Operator Authority** policy: the operator's explicit in-conversation approval is authoritative for workflow gates when repository policy requires approval, and once given it should be recorded and treated as satisfied without being re-requested absent new repository evidence. That explicit approval for PH-1 specifically has not yet been given in a message that was not interrupted before it could be acted on.
- **F-02 — PH-2 planning target branch undefined.** A separate, highly structured PH-2 planning-framework request (Principal-Architect role, 10 sections, Pass 1 = "Implementation Readiness Realignment") is in progress but has not named which branch PH-2 *planning* artifacts should land on.
- **F-06 — May PH-2 planning proceed in draft form ahead of formal PH-1 promotion?** Not yet answered.
- A Pass 1 report was produced under that PH-2 planning framework with verdict **`BLOCKED_BY_AUTHORITY`**, explicitly citing F-01/F-02/F-06 as blockers, and explicitly instructed **"Do NOT create planning files yet"** and **"do not begin Pass 2"** until the operator resolves them. No PH-2 planning files exist in this repository as of this handoff.
- **PR #6** (a separate, still-open, unchecked competing Section-1-implementation attempt via local Aider+Ollama, based on a stale pre-freeze commit) duplicates the mission now completed on `claude/builder-handoff-pr8-inc9p8`. Needs an operator decision (likely closure) — not yet acted on.

**For the next session:** do not repeat the Pass 1 analysis or re-request F-01/F-02/F-06 from scratch — check first whether the user's next message already resolves them (per the Operator Authority policy the user stated), and only re-ask if genuinely still unresolved. If resolved, record the resolution here and in the PH-2 planning artifacts once those are authorized to be created.
