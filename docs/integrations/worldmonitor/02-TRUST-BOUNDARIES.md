# WorldMonitor 02 — Trust Boundaries

WorldMonitor is NEVER exposed to: provider keys, the Builder repository, the Docker socket, the host
filesystem, the Builder secret store, the worker control channel, or permission-engine internals.

- **Network:** all traffic via `NetworkBroker` under a task-scoped approval (domain allowlist,
  redirect validation, byte/time/request ceilings, audit). No direct network.
- **Secret:** optional `WORLDMONITOR_API_KEY` / `WORLDMONITOR_OAUTH_TOKEN` leased from `SecretBroker`
  only; never from env, never persisted/logged.
- **Model authority:** WorldMonitor MUST NOT select a provider, load/unload models, call Ollama/cloud,
  retain credentials, or bypass routing. It hands a capability request to the Builder router.
