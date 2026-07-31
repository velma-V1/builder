# WorldMonitor 01 — Architecture

Modules (`src/factory/integrations/worldmonitor/`): `models` (contracts + IntelligenceRecord),
`manifest` (pinned/unverified upstream + license), `capabilities` (discovery; unknown → denied),
`policy` (brokered HTTP + model authority), `rest_client`, `mcp_client` (discovery-only fake),
`normalization` + `provenance`, `health`, `ui_bridge`, `lifecycle` (dry-run), `retention`,
`fake_transport`, `adapter` (the managed `WorldMonitorAdapter`).

Data flow: query → capability gate → brokered REST fetch → normalize (stale-mark, source-URL check,
dedup, provenance) → `WorldMonitorResult`. AI flow: `WorldMonitorAdapter.request_ai` → `ModelRouterPort`
(Builder) — WorldMonitor never selects a provider or holds a key.
