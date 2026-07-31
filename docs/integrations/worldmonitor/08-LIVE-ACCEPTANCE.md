# WorldMonitor 08 — Live Acceptance (for later; NOT executed)

Before any live use (separate authorization): confirm the pinned release/commit + image digest from
upstream; approve required domains/ports; provision optional credentials into the `SecretBroker`.
Then confirm on live infra: health healthy/degraded/unavailable; capability discovery per mode;
REST/MCP normalization preserving provenance; stale-data marking; dedup; malformed-input rejection;
source/output URL validation; redirect denial; UI message validation; and model-router-only AI.
Every check has a deterministic fake-parity test in `tests/integrations/worldmonitor/`.
