# Compose templates — UNAPPLIED (Stage-3 live-gate preparation)

These Docker Compose files are **structural templates**, not deployables. During Stage-3
preparation they are **not** applied: no network is created, no image is pulled, no container is
started.

## Files

| File | Role |
|---|---|
| `factory-workers.compose.yaml` | Worker services, each single-homed on the internal-only network. |
| `factory-broker.compose.yaml` | The sole dual-homed egress broker (internal + egress legs). |

## Hardening invariants (validated statically)

Both templates are validated by `factory.livegate.compose_topology.validate_compose`, the
compile-time twin of `factory.sandbox.policy.evaluate_spec`. A worker must satisfy all ten:

1. attached to exactly one network, marked `internal: true`;
2. not dual-homed (broker only);
3. no container-runtime socket bind mount;
4. no `network_mode: host`;
5. no published ports;
6. `read_only: true`;
7. non-root `user` (uid ≠ 0);
8. `cap_drop: [ALL]`;
9. `security_opt: [no-new-privileges:true]`;
10. positive `cpus` / `mem_limit` / `pids_limit`.

The broker is exempt from (1)/(2) only and must satisfy every other invariant.

## Before any live use (requires separate operator authorization)

- Replace `__PINNED_DIGEST__` with an image pinned by `@sha256:` digest (never a floating tag).
- Confirm the SQLite compliance gate passes (see `docs/live-gate/05-...`).
- Run the structural validator (`tests/livegate/test_compose_topology.py`) — must be green.
- Only then, and only under explicit authorization, apply on the WSL2 + Docker target host.
