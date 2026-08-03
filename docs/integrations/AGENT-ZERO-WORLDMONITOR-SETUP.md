# Agent Zero and WorldMonitor local integration

Builder manages Agent Zero v2.7 and WorldMonitor v2.5.23 as pinned external containers. Their
source is not vendored. Agent Zero is MIT-licensed. WorldMonitor is AGPL-3.0-or-later and this
integration is approved only for local use; hosted/commercial operation and relicensing are not
covered.

## Prerequisites and configuration

Install Docker Desktop with WSL2 integration, then confirm `docker compose version` works inside
the configured WSL distribution. Review `config/builder.yaml`; it contains the exact releases,
commits, loopback ports, timeouts, and resource ceilings. Normal use requires configuration only,
not source edits. Builder creates runtime-scoped operator, Agent Zero API, and model-gateway
credentials at launch. The local dashboard proxy injects operator authorization server-side;
bearer credentials are not compiled into frontend code or written to browser storage, logs,
config, or repository files.

Run Builder with `uv run python scripts/start_all.py`, open the dashboard, and use **Managed
integrations**. Install pulls/builds the pinned dependency, Start waits for container health,
Stop preserves data, Disable stops and records the disabled state, and Remove tears down containers
without deleting named volumes. Volume deletion is intentionally a separate destructive action.

## Agent Zero workflow

Start Agent Zero, wait for `READY`, enter task instructions, and submit. Builder calls the official
v2.7 asynchronous `/api/message_async` and `/api/poll` contracts with its runtime API credential,
persists the returned context before polling, and treats the response as untrusted input. Builder
performs independent verification and approval/promotion before reporting completion. Status,
bounded logs, active cancellation, timeout, stop, and restart remain Builder-owned.
Agent Zero receives no Docker socket, main-branch authority, promotion authority, or persistent
Builder credential. Its container is non-root, read-only, capability-dropped, resource-bounded,
loopback-published, and isolated on its own Docker network.

## WorldMonitor workflow

Start WorldMonitor, wait for `READY`, then choose Refresh. Builder calls the official pinned
`/api/seismology/v1/list-earthquakes` contract and displays source-attributed USGS earthquake data.
This is the only implemented WorldMonitor capability. The approved pinned-upstream scope also
includes world briefs, country risk, conflicts, military, cyber, broader disasters, climate,
maritime, aviation, markets, economic indicators, infrastructure, and news/research; those remain
unimplemented, so WorldMonitor and the combined section are `INCOMPLETE`.
The application has no repository or Docker-socket mount. Outbound traffic is forced through a
sidecar allowlist for `earthquake.usgs.gov`; unavailable sources produce an actionable degraded
result rather than fabricated data. Stop and restart preserve its cache.

## Recovery and troubleshooting

On Builder restart, durable integration state is compared with Docker Compose state. A previously
ready service whose container is missing becomes `FAILED`; it is never reported ready from stale
state. Startup timeouts and Compose errors are retained as the authoritative detail. Inspect the
bounded service logs in Builder, correct Docker/resource/port issues, then Start again. The two
Compose projects use distinct ports, networks, volumes, and resource budgets, so one service can
fail or restart without changing the other's durable state.

Live container acceptance must be run on Windows 11 + WSL2 with Docker Desktop integration. A host
without a working Docker command can pass deterministic contract/security tests but must record
installation, readiness, real use, restart, recovery, cleanup, and combined operation as BLOCKED.
