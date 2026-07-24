# Factory PH-1 Implementation Handoff

**Repository:** `velma-V1/builder`
**Branch:** `claude/factory-arch-planning-n1a7gn` (based on `agent/minimum-builder-shell-design`)
**Status at handoff:** Planning complete and readiness-verified. Readiness verdict: **`READY_TO_BEGIN_PH1`**. Product implementation has **not** started (no `src/`, `schemas/`, or `migrations/` exist yet).
**For a new session/window:** read this file first, then the authority documents named below, then begin **only** PH-1.

## 1. What is done
- Full governing corpus present: `PROJECT_DEFINITION.md`, `docs/00`–`06`, supplements `docs/01A`–`01Q`, `HANDOFF.md`.
- Planning system built (`docs/10`, `docs/11`, `docs/planning/*`, `docs/release/*`, `docs/templates/*`, `docs/specifications/components/00-COMPONENT-MAP.md`, `docs/plans/*`).
- Resolutions **R1–R5** and **Decisions A–C** recorded in `docs/01R-PLANNING-RESOLUTIONS-AND-AMENDMENTS.md` and registered in the index; supersession pointers placed in the amended governing docs. Readiness-review hygiene findings F1/F2/F3 are patched.

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

## 3. The only task now: PH-1
Execute **`docs/plans/section-1-requirements-contracts.md`** task-by-task, step-by-step: Task 1 → Task 5, following every `- [ ]` step and its exact `uv run` / `git commit` commands. That plan builds the Section 1 contract subsystem: seven YAML contract families + envelope, safe ingestion + canonicalization + SHA-256, semantic/impact validation, policy/change/activation, immutable runtime cache, and the full verification package.

- Tech stack and pins are specified in the plan (Python 3.12, uv, PyYAML, jsonschema, rfc8785, pytest, mypy, ruff). Verify pins resolve via `uv lock` / `uv sync --frozen`; if any pin is unavailable, record the nearest approved compatible pin (RISK-DEP-01).
- Target the **Windows 11 Home** dev path (± activation); ≥95% branch coverage for `src/factory/contracts`.
- Deletion policy in code/tests must be **approval-required** (Decision B) — do not implement disposable auto-delete.

## 4. Guardrails — do NOT
- Do **not** start the Dashboard (PH-S/PH-8), Model Router or adapters (PH-4), Installer/updater/packaging (PH-8), Git/sandbox isolation (PH-5), Watchdog/Orchestrator engine (PH-2/PH-3), lanes/workstreams (PH-6), or any phase other than PH-1.
- Do **not** merge to `main`, open or modify a pull request, or promote. PR #7 on `agent/minimum-builder-shell-design` must stay untouched.
- Do **not** push to any branch other than `claude/factory-arch-planning-n1a7gn` (use an explicit refspec).
- Do **not** weaken any acceptance criterion/test after implementation-start except through the `01G §3.2` process.
- Do **not** proceed past PH-1's **schema-freeze operator approval** (`docs/10 §15` #2) or its **exit gate** without explicit approval. Do not roll into PH-2.

## 5. Definition of done for PH-1
All 13 Section 1 acceptance criteria `PASS`, each required criterion backed by a complete Evidence Traceability Manifest (`01G §3.1`); `scripts/verify_section1.py` green on the Windows 11 Home dev path; evidence package finalized with integrity hashes. Then **stop** and request the schema-freeze / phase-exit approval per the roadmap gates (G5 → G6).

## 6. Git & verification discipline
- Work on `claude/factory-arch-planning-n1a7gn`; commit per the plan's Task-boundary commits with the standard trailers; push with an explicit refspec and `--force-with-lease` never needed for fast-forward.
- Before the first code commit, confirm the branch is based on `agent/minimum-builder-shell-design` and that no premature artifacts exist beyond what the current PH-1 step creates.
- Report test outcomes faithfully (verdicts from the `01G` set); never relabel unverified results as `PASS`.
