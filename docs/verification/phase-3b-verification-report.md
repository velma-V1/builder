# Phase 3B Verification Report

**Verdict:** `ENVIRONMENT-BLOCKED`

Verified implementation commit: `475c528580fb580922526b0404101f9b080a0c9c`. Date: 2026-08-02.
Environment: Linux, CPython 3.14.6, locked `uv` environment. Native-Windows results below
remain historical evidence for `48e0dd8`; they are not attributed to the current commit.

## Results

| Command/check | Result |
|---|---|
| `pytest --collect-only -q` | PASS — 1733 collected |
| `pytest -q` | PASS — 1648 passed, 85 environment-classified skips in the restricted Linux sandbox |
| `.venv/bin/pytest -q -m loopback` outside restricted socket sandbox | PASS — 83 passed |
| focused launcher portability regression | PASS — 3 passed; guarded lookup, Linux absence, and fail-closed Windows absence |
| focused native-Windows launcher tests | ENVIRONMENT-BLOCKED — current host reports `sys.platform == "linux"` |
| two Windows junction cases | HISTORICAL PASS at `48e0dd8` — 2 passed; rerun at current commit is required |
| `UV_CACHE_DIR=/tmp/builder-uv-cache .venv/bin/python scripts/verify_section1.py` | PASS — 325 contract tests; 96.86% branch coverage |
| `ruff format --check .` / `ruff check .` | PASS — 530 files formatted; lint clean |
| `mypy src/factory scripts` | PASS — 305 source files |
| `uv lock --check` with writable cache | PASS — 35 packages resolved |
| `git diff --check` | PASS |
| Phase 3B focused lifecycle/promotion/verification gates | PASS |
| frontend typecheck/lint/test/build | PASS — 43 tests; bundle built |
| `verify_section2.py` | PASS — 18/18 |
| `verify_roadmap_ph3.py` | PASS — 10/10; 12 exact migration hashes |
| `verify_ph4_preinstall.py` | PASS — 10/10; 127 tests; coverage ≥95% |
| cross-lane, RPH3 T1–T5, preinstall, PH5, PH6, worker substrate | PASS |

## Environment-blocked checks

| Command | Exact error | Missing capability | Required rerun environment |
|---|---|---|---|
| `py -3.14 -m pytest -q tests/scripts/test_start_all.py -k "creation_flags or spawn_and_terminate_process_group"` | Not executed: capability probe returned `linux`, not `win32` | Native Windows process creation and `CREATE_NEW_PROCESS_GROUP` behavior | Native Windows with CPython 3.14 and the locked dependencies at `475c528580fb580922526b0404101f9b080a0c9c` |

## Release boundary

Native-Windows launcher verification remains required at the exact current commit. Independent
review also remains a separate merge gate. This report does not authorize a merge, deployment,
release, or protected-ref promotion; those remain operator-only decisions.
