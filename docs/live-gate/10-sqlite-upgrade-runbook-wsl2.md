# 10 — SQLite Upgrade Runbook (Option A, SELECTED) — WSL2 target host

**Decision:** `SQLITE_REMEDIATION := OPTION_A_SELECTED_EXECUTION_DEFERRED`. Upgrade the
**Python-linked** SQLite engine to satisfy the floor. Run on your **Windows 11 + WSL2 target host**.
This preparation session runs in a remote Linux container that **cannot reach your host or
sqlite.org**, so every step here is operator-executed and **no step has been executed**.

## Floor vs. selected install version

- **Floor (fixed):** `>= 3.51.3` (`factory.persistence.sqlite_guard.MIN_SQLITE_VERSION`). Unchanged.
- **Selected install version:** the **current official stable SQLite release whose
  `SQLITE_VERSION >= 3.51.3`**, read from official data at execution time (below). The floor is a
  minimum, *not* a specific pinned tarball — do not hardcode a version that you have not verified
  against official SQLite data.

> ⚠️ **Unverified-from-here:** this environment could not fetch `sqlite.org` (egress blocked). I have
> therefore **not** asserted any specific version, URL, size, or digest. You must read the exact
> values from the official source below and verify the digest before use. If the current official
> release is **below 3.51.3**, STOP — do not lower the floor and do not use an unapproved build.

## Source of truth + official digest algorithm

- Download page: **https://sqlite.org/download.html**. It contains a machine-readable block
  *"Download product data for scripts to read"* with CSV lines:
  `PRODUCT,VERSION,RELATIVE-URL,SIZE-IN-BYTES,SHA3-256-HASH`.
- The **official digest algorithm is SHA3-256** (SQLite publishes SHA3-256, computed with `sha3sum`).
  **Do not use `sha256sum`.** Verify with `openssl dgst -sha3-256 <file>` (or `sha3sum -a 256`) and
  compare to the `SHA3-256-HASH` field for the exact `RELATIVE-URL` you downloaded.

## 0. Enter the distro, pull the branch, capture rollback BEFORE any change

```bash
# From Windows PowerShell:  wsl -l -v   →   wsl -d <YourFactoryDistro>
cd ~/builder && git fetch --prune origin
git checkout claude/ph4-ph5-ph6-preinstall && git pull --ff-only origin claude/ph4-ph5-ph6-preinstall
git rev-parse HEAD                       # confirm the expected branch head
mkdir -p .livegate-out
{ echo "date: $(date -u +%FT%TZ)"
  echo "python_sqlite_BEFORE: $(.venv/bin/python -c 'import sqlite3;print(sqlite3.sqlite_version)')"
  echo "libsqlite3_pkg_BEFORE: $(dpkg -s libsqlite3-0 2>/dev/null | awk -F': ' '/Version/{print $2}')"
} | tee .livegate-out/ROLLBACK_BEFORE.txt
```

## 1. Detect how the factory Python provides SQLite (chooses the path)

```bash
.venv/bin/python - <<'PY'
from factory.preinstall.python_env import running_interpreter, remediation_note, linked_sqlite_version
kind, exe = running_interpreter()
print("interpreter:", exe)
print("python_type:", kind.value)
print("linked_sqlite:", ".".join(map(str, linked_sqlite_version())))
print("remediation:", remediation_note(kind))
PY
```

## 2. Upgrade — follow the block for your `python_type`

### 2a. `distro` (dynamically links the OS libsqlite3) — preferred, simplest

```bash
sudo apt-get update
apt-cache policy libsqlite3-0                     # confirm Candidate >= 3.51.3 FIRST
sudo apt-get install --only-upgrade libsqlite3-0  # only if Candidate satisfies the floor
```

### 2b. `uv_managed` (bundles its own SQLite) — rebuild the environment

An OS library upgrade does **not** move a uv-standalone interpreter's linked SQLite. Preferred:
switch the factory interpreter to one that already links SQLite ≥ 3.51.3, then **rebuild the venv**:

```bash
# Point the project at an interpreter that links >= 3.51.3 (a newer uv build, or a system Python):
uv python pin <interpreter-that-links-sqlite-3.51.3-or-newer>
uv sync                                            # REQUIRED: rebuild the venv when Python changes
```

`LD_PRELOAD` is a **last resort only** and will **not** override a statically linked engine — do not
rely on it for a uv-standalone interpreter.

### 2c. `custom` — determine linkage, rebuild if static

Establish whether `_sqlite3` is dynamically or statically linked. If dynamic, upgrade the OS
`libsqlite3` (as 2a). If static, rebuild the interpreter/`_sqlite3` extension against SQLite
≥ 3.51.3. Then rebuild the venv (`uv sync`) if the interpreter changed.

### 2d. Amalgamation fallback (any type, if the above cannot reach the floor)

```bash
# Read PRODUCT/VERSION/RELATIVE-URL/SHA3-256 from https://sqlite.org/download.html product-data block.
url="https://sqlite.org/<RELATIVE-URL-from-official-data>"      # e.g. .../sqlite-autoconf-XXXXXXX.tar.gz
curl -fsSLO "$url"
openssl dgst -sha3-256 "$(basename "$url")"                     # MUST equal the official SHA3-256 hash
tar xf "$(basename "$url")" && cd "$(basename "$url" .tar.gz)"
./configure --prefix=/opt/sqlite-floor && make -j"$(nproc)" && sudo make install
# Then rebuild/point the factory interpreter at this engine and `uv sync`; verify per Step 3.
```

## 3. AUTHORITATIVE verification (Python-linked engine, not the CLI)

```bash
.venv/bin/python -c "import sqlite3; print(sqlite3.sqlite_version)"   # MUST be >= 3.51.3
```

STOP if this prints `< 3.51.3` — the `sqlite3` CLI version is **not** authoritative and does not
count.

## 4. Validate the gate + run readiness

```bash
.venv/bin/python -m pytest tests/livegate/test_sqlite_compliance.py -q
.venv/bin/python scripts/live_gate/run_readiness.py      # sqlite-engine-floor -> PASS
cat .livegate-out/readiness.json                          # redacted; send this back for review
```

## 5. Rollback (if any step fails)

```bash
# distro:
sudo apt-get install --allow-downgrades libsqlite3-0=<libsqlite3_pkg_BEFORE>
# uv/custom: restore the previous interpreter pin and rebuild:
uv python pin <previous-interpreter> && uv sync
# amalgamation: stop using it and remove the prefix:
sudo rm -rf /opt/sqlite-floor
# confirm restored (gate returns to FAIL — the safe state):
.venv/bin/python -c "import sqlite3; print(sqlite3.sqlite_version)"
```

## 6. After a green readiness run

Review `.livegate-out/readiness.json` and fill the evidence records (`docs/live-gate/09`). Then, and
only then, authorize **PH-4 live runtime integration only** (PH-5/PH-6 stay blocked until PH-4 passes
independently). Nothing here authorizes any phase; `PROM_PH4/PH5/PH6` remain `NOT_AUTHORIZED`.
