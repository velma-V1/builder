# 10 — SQLite Upgrade Runbook (Option A, AUTHORIZED) — WSL2 target host

**Authorized:** Option A — upgrade SQLite to **≥ 3.51.3**. Run this **on your Windows 11 + WSL2
target host**, inside the WSL2 Linux distro that runs the factory. This preparation session cannot
reach your host, so every step here is operator-executed. Capture the before/after output into an
evidence record (`docs/live-gate/09`).

Proven ahead of time (deterministic, no host change): the compliance gate returns **FAIL** at 3.50.4
and **PASS** at 3.51.3 / 3.51.4 / 3.52.0, and durable activation is REFUSED below the floor and
PERMITTED at/above it. So once the engine reports ≥ 3.51.3, the `sqlite-engine-floor` gate flips to
`PASS` with no code change.

## 0. Evidence BEFORE

```bash
python3 -c "import sqlite3; print('sqlite', sqlite3.sqlite_version)"   # expect 3.50.4
apt-cache policy libsqlite3-0 2>/dev/null | head -3
```

## 1. Preferred: upgrade the distro package (if it provides ≥ 3.51.3)

```bash
sudo apt-get update
apt-cache policy libsqlite3-0            # check the candidate version FIRST
# Only if the candidate is >= 3.51.3:
sudo apt-get install --only-upgrade libsqlite3-0
python3 -c "import sqlite3; print(sqlite3.sqlite_version)"   # expect >= 3.51.3
```

## 2. Fallback: pinned amalgamation + LD_PRELOAD (if the distro is behind)

Use only if step 1 cannot reach ≥ 3.51.3. Pin the exact approved release and verify its SHA-256
against the value published on sqlite.org **before** building.

```bash
ver=3510300                                              # 3.51.3 (pin the approved release)
curl -fsSLO "https://sqlite.org/2025/sqlite-autoconf-${ver}.tar.gz"
sha256sum "sqlite-autoconf-${ver}.tar.gz"                # MUST equal the published digest
tar xf "sqlite-autoconf-${ver}.tar.gz" && cd "sqlite-autoconf-${ver}"
./configure --prefix=/opt/sqlite-3.51.3 && make -j"$(nproc)" && sudo make install
# Preload for the factory venv only (does NOT replace the system engine):
export LD_PRELOAD=/opt/sqlite-3.51.3/lib/libsqlite3.so   # add to the factory service env to persist
python3 -c "import sqlite3; print(sqlite3.sqlite_version)"   # expect 3.51.3
```

## 3. Validate (must all pass before durable-store use)

```bash
python3 -c "import sqlite3; print(sqlite3.sqlite_version)"          # >= 3.51.3
python -m pytest tests/livegate/test_sqlite_compliance.py -q       # green
python scripts/live_gate/run_readiness.py                          # sqlite-engine-floor -> PASS
cat .livegate-out/readiness.json                                   # redacted; attach to evidence
```

The same readiness run also reports Docker / WSL2 / NVIDIA-CUDA / Ollama and the approved models
(`qwen3:8b`, `qwen3:14b`). All mandatory gates must be `PASS` for the runner to exit 0.

## 4. Rollback (if validation fails)

```bash
# Package path:
sudo apt-get install --allow-downgrades libsqlite3-0=<previous_pinned_version>
# Amalgamation path:
unset LD_PRELOAD                     # and remove it from the service env if you persisted it
sudo rm -rf /opt/sqlite-3.51.3
python3 -c "import sqlite3; print(sqlite3.sqlite_version)"          # back to 3.50.4 (gate FAIL)
```

After rollback the `sqlite-engine-floor` gate returns to `FAIL` and durable stores refuse to
activate — the safe state.

## 5. After a green readiness run

Review the generated evidence (`.livegate-out/readiness.json` + filled records in `docs/live-gate/09`).
Then, and only then, authorize **PH-4 live runtime integration only** — keep PH-5 and PH-6 blocked
until PH-4 passes independently (see `docs/live-gate/06` and `08`). Nothing in this runbook authorizes
PH-4/5/6; each remains `NOT_AUTHORIZED` until you grant it explicitly.
