# Preinstall 03 — Docker Compose Topology

Unapplied templates in `deploy/compose/` (see `deploy/compose/README.md`), validated statically by
`factory.livegate.compose_topology.validate_compose` — the compile-time twin of
`factory.sandbox.policy.evaluate_spec`. Nothing is applied during preinstall.

## Services

- `factory-workers.compose.yaml` — workers, each **single-homed** on the internal-only network.
- `factory-broker.compose.yaml` — the **sole dual-homed** service (internal + egress legs).

## Enforced invariants (worker; broker exempt only from net single-homing)

internal-only network · single-homed worker · no runtime socket mount · no `network_mode: host` ·
no published ports · `read_only: true` · non-root `user` · `cap_drop: [ALL]` ·
`security_opt: [no-new-privileges:true]` · positive `cpus`/`mem_limit`/`pids_limit`.

## Before any live apply (separate authorization)

Replace `__PINNED_DIGEST__` with an `@sha256:` image digest, confirm the SQLite gate is `PASS`, run
`tests/livegate/test_compose_topology.py` (must be green), then apply on the WSL2 host under explicit
authorization. `docker compose up` is **not** run during preinstall.
