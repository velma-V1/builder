# 07 — Rollback & Cleanup Procedure

This procedure applies to any **future** live step (each performed only under separate
authorization). During preparation nothing was applied, so there is nothing to roll back now — this
is the standing procedure to keep every live step reversible.

## Principles

- **One reversible change at a time.** Capture evidence before and after each step.
- **Fail closed.** If a step cannot be verified, roll it back rather than proceeding.
- **Never rewrite history or force-push** to protected refs to "fix" a live issue.
- **Durable stores stay inert** until the SQLite gate is `PASS`.

## SQLite remediation rollback

See document 05 §3 for the exact per-option rollback (apt downgrade / remove amalgamation preload /
remove the approved-backport tuple). After rollback, re-run
`python scripts/live_gate/run_readiness.py` — the `sqlite-engine-floor` gate must return to `FAIL`
and durable stores must refuse to activate.

## Container / Compose cleanup (if a live apply was authorized)

```bash
# Stop and remove the stack (no volumes are declared; add -v only if volumes are later introduced):
docker compose -f deploy/compose/factory-workers.compose.yaml down --remove-orphans
docker compose -f deploy/compose/factory-broker.compose.yaml  down --remove-orphans

# Remove the internal/egress networks if they were created:
docker network rm factory-internal factory-egress 2>/dev/null || true

# Confirm nothing is left running:
docker ps --filter "name=worker-" --filter "name=broker"
```

## Ollama cleanup

```bash
# Remove any model pulled for a trial that should not persist (approved models normally stay):
ollama rm <model-tag>
```

## Durable store cleanup

The durable schema is a template and is not applied during preparation. If a live store was created
under authorization and must be removed:

```bash
# The durable DB path lives under a git-ignored runtime directory; remove the file + WAL/SHM:
rm -f <runtime>/execution_journal.db <runtime>/execution_journal.db-wal <runtime>/execution_journal.db-shm
```

## Readiness / discovery output cleanup

```bash
rm -rf .livegate-out/     # git-ignored; regenerated read-only by the readiness runner
```

## Evidence

For every live step, attach: the before/after command output, the readiness report
(`.livegate-out/readiness.json`, redacted), and the relevant filled evidence record (document 09).
Rollback events are recorded the same way, noting the trigger and the restored state.
