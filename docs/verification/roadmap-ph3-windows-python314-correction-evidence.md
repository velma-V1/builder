# RPH3 T3/T2/T5 Windows and Python 3.14 Correction Evidence

**Status:** `RPH3-T3/T2/T5_CORRECTED — READY_FOR_OPERATOR_REVIEW`

**Branch:** `claude/roadmap-ph3-security-spine-planning`

**Reviewed base:** `8fee3a7f8d8a13e6bb741cc3d52d596e9358b843`

**Correction commit:** `928535961e9e1224d00a933b3be0cc899e954b96`

**Date:** 2026-07-29 (America/New_York)

This report supplements, and does not replace, the prior Linux T3/T2/T5 evidence. Those reports remain
historical records of their original Linux/Python 3.12 runs. This correction is not `PROM-RPH3` and is not
operator acceptance.

## 1. Environment

| Field | Result |
|---|---|
| Windows | Windows 10 Home 25H2, build 26200.8875 |
| Git | 2.55.0.windows.2 |
| Git line-ending configuration | `core.autocrlf=true`; `core.eol` unset |
| Python 3.12 | CPython 3.12.13 |
| Python 3.13 | CPython 3.13.14 |
| Python 3.14 | CPython 3.14.6 |
| Dependency source | Frozen `uv.lock`; isolated environment per Python version |

Python 3.13 was available and was tested. No Python version is claimed without a completed run.

## 2. Root causes and exact corrections

1. Git for Windows materialized tracked SQL files as CRLF when `core.autocrlf=true`. Every migration
   runner hashes `Path.read_bytes()` and compares the exact SHA-256 with a pinned constant, so the checkout
   conversion correctly failed the integrity gate.
   - Added `.gitattributes` with exactly `*.sql text eol=lf`.
   - Kept every migration runner's byte-exact hashing unchanged.
   - Ran `git add --renormalize migrations` and `git checkout -- migrations`.
   - `git diff --word-diff=porcelain -- migrations/**/*.sql` produced no SQL text diff.
2. Eight public exception classes were frozen dataclasses. Python 3.14's `contextlib` restores
   `__traceback__` while unwinding and the generated frozen `__setattr__` raised `FrozenInstanceError`.
   - Replaced `ApprovalError`, `AuditError`, `ContractError`, `FileOpError`, `OrchestratorError`,
     `PermissionError`, `SafeModeError`, and `ToolError` with normal typed `Exception` classes.
   - Preserved constructor call shapes, `code`, `message`, `ContractError.issues`, `.args`, `str()`, and
     the prior dataclass-style `repr()`.
   - Searched all repository `Exception` subclasses. `WorkerEngineError`, `_OutputInvalid`, and
     `_NoSandbox` were already normal classes and required no production change.
3. Windows verifier hygiene found while proving a repository-wide Ruff pass:
   - `scripts/verify_section2.py` now invokes tools through `sys.executable`, emits console-safe ASCII, and
     has no Ruff violations. This does not change a PH-2 product contract.

## 3. Exact migration SHA-256 results

| Migration | SHA-256 | Result |
|---|---|---|
| `migrations/contracts/0001_activation_store.sql` | `21d41f6d954fc92ef15c114ee847b81ca8d17eb83d5895823fd57ca6f337ffa1` | exact |
| `migrations/runtime/0001_state.sql` | `2fd4ecda34c05265be99de9c8aa36518cc9ac540c4038286c5da9cfb1fbd5f4c` | exact |
| `migrations/runtime/0002_leases.sql` | `a3a143e4b225655b68aadb5bc677acae7a99cf99b8c047e6c3113deb34b32ba6` | exact |
| `migrations/runtime/0003_memory.sql` | `65e0a4d16b84a49b205b1f2e48c91e11ae6dc48e9c179e318da3026283e10587` | exact |
| `migrations/audit/0001_audit_chain.sql` | `935e535a8db35693f94c6a30bcd9d312960eeeb24babea62e933ba7dfa06c433` | exact |
| `migrations/security/0001_security_spine.sql` | `099ae959d6f06c6b944925af151d8fa8dd2b65fdffd63660cf2a4355b7878a51` | exact |
| `migrations/security/0002_permission.sql` | `a65d227d9683eb060c834ae8b3cb65f33186ba37420b4065eec8623f8ded88cb` | exact |
| `migrations/security/0003_tools.sql` | `0050e74f80932fb58ea15d1f60f95661c7589d57dd623aad7691e26ea73a69b5` | exact |

`git check-attr text eol` returned `text: set` and `eol: lf` for all eight files. A fresh local clone made
with `core.autocrlf=true` at correction commit `9285359` passed all 16 checkout-policy and exact-hash cases.

## 4. Verification matrix

| Python | Focused portability/exception tests | T3 verifier | T2 verifier | T5 verifier | Full repository |
|---|---:|---:|---:|---:|---:|
| 3.12.13 | 34 passed | 9/9 PASS | 10/10 PASS | 10/10 PASS | 755 passed, 1 skipped |
| 3.13.14 | 34 passed | 9/9 PASS | 10/10 PASS | 10/10 PASS | 755 passed, 1 skipped |
| 3.14.6 | 34 passed | 9/9 PASS | 10/10 PASS | 10/10 PASS | 755 passed, 1 skipped |

The single skip on every Windows run is
`tests/contracts/security/test_path_attacks.py::test_symlink_escape_is_denied`, explicitly classified
`NOT_TESTABLE` on this platform; the suite points to its alternate denial test. There were no hidden or
unreported skips.

Focused migration lifecycle verification on Python 3.14 covered new databases, already-migrated/idempotent
startup, malformed/missing/apply-failure paths, and tampered-byte rejection across the contract, runtime,
audit, approval, permission, and tool runners: **26 passed, 59 deselected**.

## 5. Static analysis and coverage

- `ruff check .`: **PASS**.
- Strict mypy: **PASS** for all affected source packages (`contracts`, `orchestrator`, `audit`, `approval`,
  `permission`, `tools`, `fileops`, `safemode`) and both new regression-test modules.
- Each T3/T2/T5 verifier's own Ruff and strict-mypy checks: **PASS** on Python 3.12, 3.13, and 3.14.
- Python 3.14 branch coverage, with every existing threshold retained at 95%:
  - approval: **99.80%** (56 passed);
  - permission: **99.80%** (69 passed);
  - tools: **98.55%** (57 passed);
  - fileops: **97.02%** (21 passed);
  - safemode: **98.91%** (10 passed).

## 6. Known limitations and boundary confirmation

- The approval-only coverage run emitted two `ResourceWarning` messages on Python 3.13/3.14 for SQLite
  connections discovered during inspection. The tests and coverage gate pass; this correction does not
  suppress or misreport the warnings.
- The legacy PH-2 verifier now executes on Windows instead of failing on interpreter lookup/console
  encoding. Its unrelated recent-history heuristic reports 17/18 because it searches only the newest ten
  commits and no longer sees the old T2.1-T2.5 boundary messages. T3/T2/T5 verification does not depend on
  that heuristic.
- `main` remained exactly `9bce1cab3cfd360555194d2b33c03425c38b5345`.
- Draft PR #10 was not modified or merged.
- Watchdog and Lane A were not started.
- No migration hash comparison was weakened, no coverage threshold was lowered, no new milestone began,
  and no `PROM-RPH3` claim is made.
