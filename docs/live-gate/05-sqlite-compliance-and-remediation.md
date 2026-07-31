# 05 — SQLite Compliance & Remediation (FIRST MANDATORY GATE)

> **AUTHORIZATION (recorded):** the operator has **authorized Option A — upgrade SQLite to
> ≥ 3.51.3** (preferred over a custom backport: simpler to verify, maintain, update, and package).
> **Option B (approved backport) is NOT selected.**
>
> **Execution boundary:** the upgrade runs on the operator's **Windows 11 + WSL2 target host**. This
> preparation session runs in a remote Linux builder container with no access to that host (and no
> egress to `sqlite.org`), so it **cannot** perform or verify the upgrade. State is therefore
> `SQLITE_REMEDIATION := OPTION_A_SELECTED_EXECUTION_DEFERRED`. Use the turnkey runbook in
> `docs/live-gate/10-sqlite-upgrade-runbook-wsl2.md` (SHA3-256 verification; per-interpreter paths).

**Gate result in the builder container: `FAIL` (blocking).** Durable-store activation is refused and
remains refused until the target host is upgraded and its readiness probe reports `PASS`.

## 1. Detected runtime

| Fact | Value |
|---|---|
| Detection method | `sqlite3.sqlite_version` (read-only) |
| Linked runtime | **3.50.4** |
| Required floor | **3.51.3** (`factory.persistence.sqlite_guard.MIN_SQLITE_VERSION`) |
| Approved backports | none registered |
| Result | `3.50.4 < 3.51.3` and not an approved backport → **below floor** |

## 2. Fail-closed verification (already proven)

`factory.livegate.sqlite_compliance.durable_activation_fails_closed_below_floor()` confirms the
guard **raises `SQLITE_ENGINE_UNSUPPORTED`** for a below-floor engine with no approved backport, so
the durable stores cannot silently come up. This is unit-tested
(`tests/livegate/test_sqlite_compliance.py`) and re-checked live by the readiness runner. No durable
store is or will be activated while this gate is `FAIL`.

## 3. Remediation options (choose one — PREPARED, NOT EXECUTED)

### Option A — Upgrade the Python-linked SQLite engine to ≥ 3.51.3 (SELECTED)

`SQLITE_REMEDIATION := OPTION_A_SELECTED_EXECUTION_DEFERRED`. The full, corrected, step-by-step
procedure is **`docs/live-gate/10-sqlite-upgrade-runbook-wsl2.md`**. Key points (superseding any
earlier draft):

- **Floor ≠ pinned tarball.** The floor is `>= 3.51.3`; the *selected install version* is the current
  official release with `SQLITE_VERSION >= 3.51.3`, read from official data at execution time.
- **Official source + algorithm.** Read `PRODUCT,VERSION,RELATIVE-URL,SIZE,SHA3-256` from the
  *"Download product data for scripts to read"* block on `https://sqlite.org/download.html`. Verify
  the archive with **SHA3-256** (`openssl dgst -sha3-256`), **not** `sha256sum`. (The earlier draft's
  guessed `sqlite.org/2025/...` URL and `sha256sum` step were incorrect and have been removed.)
- **Path depends on the interpreter type** (`factory.preinstall.python_env.running_interpreter`):
  `distro` → upgrade OS `libsqlite3`; `uv_managed` → an OS upgrade does not move it, so switch to an
  interpreter linking ≥ 3.51.3 and **`uv sync`** (rebuild the venv); `custom` → rebuild if statically
  linked. `LD_PRELOAD` is a last resort and cannot override a static link.
- **Authoritative check** (never the CLI): `.venv/bin/python -c "import sqlite3; print(sqlite3.sqlite_version)"`.
- **Rebuild the venv whenever the interpreter changes** (`uv sync`), then re-verify.
- **Rollback** is captured *before* any change and restores the prior engine (gate returns to `FAIL`).

### Option B — Register an approved patched backport (NOT SELECTED)

> Recorded as **not chosen**. Retained for reference only; do not register a backport for this rollout.


If a vendor/distro ships a **patched** SQLite that carries the required fixes under a version string
below `3.51.3`, it may be accepted **only** with exact version + security evidence, by registering
it in `approved_backports`:

```python
from factory.persistence.sqlite_guard import assert_sqlite_supported
# Example ONLY — replace with the exact approved version and attach the security evidence:
assert_sqlite_supported(approved_backports=frozenset({(3, 50, 4)}))
```

Backport acceptance requires, in writing: exact version, the CVEs/fixes it carries, the source of
the security evidence, and the operator's approval. **Rollback:** remove the tuple from
`approved_backports`; the gate returns to `FAIL` and durable stores refuse to activate.

## 4. Post-remediation validation (run after either option, once authorized)

```bash
python3 -c "import sqlite3; print(sqlite3.sqlite_version)"      # >= 3.51.3 or approved backport
python -m pytest tests/livegate/test_sqlite_compliance.py -q
python scripts/live_gate/run_readiness.py                       # sqlite-engine-floor must be PASS
```

## 5. Standing constraint

Durable stores must **not** be activated until this gate is `PASS`. Until then the durable schema
(`deploy/schemas/durable/0001_execution_journal.sql`) stays unapplied and the live PH-4/PH-6 stores
stay inert. This item is #1 on the consolidated operator-action list (document 08).
