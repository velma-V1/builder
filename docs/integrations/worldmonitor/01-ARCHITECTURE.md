# WorldMonitor 01 — Architecture

Modules (`src/factory/integrations/worldmonitor/`): `models` (contracts + IntelligenceRecord),
`manifest` (pinned upstream + license), `capabilities` (discovery; unknown → denied), `policy`,
`official_client`, `normalization` + `provenance`, `health`, `ui_bridge`, and `retention`. Shared
lifecycle, durable state, audit, migration, and API control live in `factory.integrations` rather
than a WorldMonitor-specific placeholder.

Data flow: authenticated refresh intent → pinned read-only upstream request → source validation →
normalize with provenance → durable success or actionable `DEGRADED` evidence → Builder dashboard.
WorldMonitor has no model-provider path and holds no provider credential.
