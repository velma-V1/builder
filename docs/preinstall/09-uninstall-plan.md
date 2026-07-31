# Preinstall 09 — Uninstall Plan

How to fully remove the live footprint on the host, if ever needed. Nothing is installed during
preinstall, so there is nothing to uninstall now — this is the standing procedure.

## Order (reverse of install)

1. **Stop & remove containers/networks**
   ```bash
   docker compose -f deploy/compose/factory-workers.compose.yaml down --remove-orphans
   docker compose -f deploy/compose/factory-broker.compose.yaml  down --remove-orphans
   docker network rm factory-internal factory-egress 2>/dev/null || true
   ```
2. **Remove durable stores** (only if created under authorization)
   ```bash
   rm -f <runtime>/execution_journal.db <runtime>/execution_journal.db-wal <runtime>/execution_journal.db-shm
   ```
3. **Remove pulled models** (optional)
   ```bash
   ollama rm qwen3:8b qwen3:14b
   ```
4. **Revert SQLite** (if upgraded) — see Preinstall 08 / `docs/live-gate/10` rollback.
5. **Remove readiness output**
   ```bash
   rm -rf .livegate-out/
   ```
6. **Remove the clone / venv** (optional)
   ```bash
   rm -rf ~/builder/.venv    # and the clone itself if desired
   ```

## What uninstall never touches

It does not remove WSL2, Docker, the NVIDIA driver, or system packages the operator may use for other
purposes — those are host-level and out of the factory's scope. Removing them is a separate, explicit
operator decision.
