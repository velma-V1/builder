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

## API-only hardened deployment

The pinned upstream `docker/run` image is a rootful supervisord system runtime and cannot start
under the approved non-root/read-only/capability-dropped boundary. The approved deployment instead
builds an **API-only child image** (`deploy/integrations/agent-zero/Dockerfile.api`) from the exact
pinned v2.7 source commit (`87e1e591…`, parent `builder/agent-zero-parent:404177ac`). It runs only
the Agent Zero API/UI process (`run_ui.py` / uvicorn on 8080) as non-root `1000:1000` under a
read-only rootfs with `cap_drop ALL` + `no-new-privileges`. The security boundary is not weakened.

Live acceptance on Docker Desktop for WSL2 (2026-08-03) is **PASS** end-to-end: Builder → ingress
(`127.0.0.1:50080`) → bridge relay → Squid egress → `host.docker.internal:8100` model gateway →
Ollama `qwen3:8b` returned `LIVE-MODEL-OK`. Two sanctioned in-scope mitigations are required by
upstream v2.7 behavior and are baked into the image, not into Builder's core:

1. **Model preset:** v2.7's `_model_config` plugin overrides `A0_SET_chat_model_*` with its `Default`
   preset, so `presets.yaml` is baked with Default chat+utility → `openai/qwen3:8b` at the gateway
   base URL.
2. **Offline embedding:** the `_memory` plugin would download `all-MiniLM-L6-v2` from huggingface.co;
   a pruned offline cache (88 MB) is baked with `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1`.
3. **SSE-only chat loop:** v2.7 always sends `stream:true`; the model-gateway route normalizes it to
   a single non-streaming completion and returns OpenAI SSE (`[DONE]`). `ModelGateway.complete()`
   keeps its fail-closed non-streaming contract.

Known upstream defect: `normalize_settings` overwrites `A0_SET_mcp_server_token` with a derived
token, so `api_log_get` / `api_terminate_chat` require that derived token rather than the configured
key. Builder records this and uses the derived token for cancel/logs lifecycle operations.

See `docs/verification/agent-zero-worldmonitor-verification.md` for exact commands, counts, image
digests, topology proof, and the upstream-defect evidence.
