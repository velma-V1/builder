# 05 — SQLite Compliance & Remediation (FIRST MANDATORY GATE)

> **AUTHORIZATION (recorded):** the operator has **authorized Option A — upgrade SQLite to
> ≥ 3.51.3** (preferred over a custom backport: simpler to verify, maintain, update, and package).
> **Option B (approved backport) is NOT selected.**
>
> **Execution boundary:** the upgrade runs on the operator's **Windows 11 + WSL2 target host**. This
> preparation session runs in a remote Linux builder container with no access to that host, so it
> **cannot** perform the upgrade. State on the target host is therefore
> `SQLITE_REMEDIATION := AUTHORIZED_OPTION_A — PENDING_EXECUTION_ON_TARGET_HOST`. Use the turnkey
> runbook in `docs/live-gate/10-sqlite-upgrade-runbook-wsl2.md`.

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

### Option A — Upgrade the SQLite runtime to ≥ 3.51.3 (preferred)

Python's `sqlite3` links the system/Python `libsqlite3`. The exact commands depend on how Python is
provided on the WSL2 target. **Run only after authorization; capture evidence at each step.**

WSL2 Ubuntu, system Python (illustrative — pin the real fixed version when authorized):

```bash
# 0. Evidence BEFORE (record):
python3 -c "import sqlite3; print(sqlite3.sqlite_version)"      # expect 3.50.4
apt-cache policy libsqlite3-0

# 1. Upgrade libsqlite3 to a build >= 3.51.3 from the approved apt source:
sudo apt-get update
sudo apt-get install --only-upgrade libsqlite3-0     # must land >= 3.51.3

# 2. Evidence AFTER:
python3 -c "import sqlite3; print(sqlite3.sqlite_version)"      # expect >= 3.51.3
```

If the distro does not yet ship ≥ 3.51.3, build the amalgamation and preload it (pinned version
only, verified against the upstream SHA):

```bash
# Download the EXACT approved amalgamation, verify its SHA-256, build, and preload for Python:
sqlite_ver=3510300                                   # 3.51.3 — pin the approved release
curl -fsSLO "https://sqlite.org/2025/sqlite-autoconf-${sqlite_ver}.tar.gz"
sha256sum "sqlite-autoconf-${sqlite_ver}.tar.gz"     # compare to the approved digest BEFORE use
tar xf "sqlite-autoconf-${sqlite_ver}.tar.gz" && cd "sqlite-autoconf-${sqlite_ver}"
./configure --prefix=/opt/sqlite-3.51.3 && make -j"$(nproc)" && sudo make install
# Preload for the factory venv only (does not touch the system engine):
export LD_PRELOAD=/opt/sqlite-3.51.3/lib/libsqlite3.so
python3 -c "import sqlite3; print(sqlite3.sqlite_version)"      # expect 3.51.3
```

**Rollback for Option A:**

```bash
# apt path:
sudo apt-get install --allow-downgrades libsqlite3-0=<previous_pinned_version>
# amalgamation path — simply stop preloading and remove the prefix:
unset LD_PRELOAD
sudo rm -rf /opt/sqlite-3.51.3
python3 -c "import sqlite3; print(sqlite3.sqlite_version)"      # back to 3.50.4
```

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
