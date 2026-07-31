# Preinstall 02 — Python / uv / SQLite Plan

## Python + uv

- Target **CPython 3.12**, managed with **uv** and a committed `uv.lock` (reproducible installs).
- Recreate the environment with `uv sync` (offline where the cache allows). **Rebuild the venv
  whenever the interpreter changes** — the linked SQLite engine is a property of the interpreter.

## The SQLite subtlety (authoritative check)

The SQLite version that governs the durable-store gate is the one linked by the **exact interpreter
that runs the factory**, not the `sqlite3` CLI:

```bash
.venv/bin/python -c "import sqlite3; print(sqlite3.sqlite_version)"
```

`factory.preinstall.python_env.running_interpreter()` classifies the interpreter as
`uv_managed | distro | custom` and returns the correct remediation note:

- **distro** — dynamically links OS `libsqlite3`; upgrade the OS library.
- **uv_managed** — bundles its own SQLite; an OS upgrade does not move it. Switch to an interpreter
  that links ≥ 3.51.3 and `uv sync`. `LD_PRELOAD` is a last resort and cannot override a static link.
- **custom** — determine linkage; rebuild if static.

Full procedure with SHA3-256 download verification: `docs/live-gate/10-sqlite-upgrade-runbook-wsl2.md`.

## Floor

`sqlite >= 3.51.3` (`factory.persistence.sqlite_guard.MIN_SQLITE_VERSION`). Durable stores fail
closed below the floor. `SQLITE_REMEDIATION := OPTION_A_SELECTED_EXECUTION_DEFERRED`.
