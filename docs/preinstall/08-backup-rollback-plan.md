# Preinstall 08 — Backup & Rollback Plan

Every future live step must be reversible. Completeness is modelled by
`factory.preinstall.rollback.RollbackPlan` (a mutating step with no rollback, or no
capture-before-change, is reported incomplete).

## Backup-before-change checklist (per mutating step)

1. Record current state into `.livegate-out/ROLLBACK_BEFORE.txt` (versions, package versions, config
   snapshots, interpreter pin, git HEAD).
2. Confirm a concrete rollback command exists for the change.
3. Apply the change (only in `--apply` mode of a guarded installer).
4. Verify the intended end state; if verification fails, execute the rollback immediately.

## Standard rollbacks

| Change | Rollback |
|---|---|
| SQLite upgrade (distro) | `apt-get install --allow-downgrades libsqlite3-0=<recorded>` |
| SQLite upgrade (uv/custom) | restore prior interpreter pin, `uv sync`, re-verify |
| SQLite amalgamation | remove `/opt/sqlite-*` prefix; restore prior interpreter |
| Compose apply | `docker compose … down --remove-orphans`; `docker network rm factory-internal factory-egress` |
| Ollama model pull | `ollama rm <tag>` |
| Durable store created | remove the DB + `-wal`/`-shm` under the git-ignored runtime dir |

## Invariant

After any rollback, re-run `scripts/live_gate/run_readiness.py`. A rolled-back SQLite change returns
the `sqlite-engine-floor` gate to `FAIL` — the safe state; durable stores refuse to activate.
Detailed cleanup: `docs/live-gate/07-rollback-and-cleanup.md`.
