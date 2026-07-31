# 02 — WSL2 & Docker Readiness

Per Decision C (`01R`), the live substrate is **WSL2 + Docker (Linux) only**. These are read-only
readiness checks; installing/starting/ configuring WSL2 or Docker is an operator action (document
08) requiring separate authorization.

## Docker Engine (mandatory gate `docker-engine`)

| Item | Value |
|---|---|
| Probe | `docker --version` (read-only) |
| Floor | **24.0.0** (`factory.livegate.version_probe.MIN_DOCKER_VERSION`) |
| PASS when | parsed version ≥ 24.0.0 |
| UNAVAILABLE when | `docker` not found / unparseable → install Docker Engine on the host |

Rationale for the floor: Compose v2 GA, cgroup-v2 resource limits, and rootless improvements are all
present at ≥ 24.0. The live sandbox relies on cgroup-v2 limits (`pids`, `memory`, `cpus`).

## WSL2 default version (mandatory gate `wsl2-default`)

| Item | Value |
|---|---|
| Probe | `wsl --status` (read-only, Windows host) |
| Requirement | `Default Version: 2` |
| UNAVAILABLE when | `wsl` not found (expected off the Windows host) |

## Additional operator confirmations (manual, at live time)

- Docker daemon is running rootless or with a non-root default user (workers run non-root anyway).
- cgroup v2 is active in the WSL2 distro (`stat -fc %T /sys/fs/cgroup` → `cgroup2fs`).
- No `DOCKER_HOST` points at a remote/socket-forwarded daemon (the sandbox forbids the runtime
  socket inside containers; the host daemon must be local).

## Compose templates (validated statically, unapplied)

`deploy/compose/factory-workers.compose.yaml` and `factory-broker.compose.yaml` encode the hardened
topology and are validated by `tests/livegate/test_compose_topology.py`. They are **not** applied
during preparation. Before any live apply: replace `__PINNED_DIGEST__` with an `@sha256:` digest and
re-run the structural validator.
