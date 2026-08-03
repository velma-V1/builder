# Agent Zero and WorldMonitor Verification — supersedes 2026-08-02

## Status (updated 2026-08-03, live Docker acceptance PASS on Docker Desktop for WSL2)

- **Branch / HEAD:** `codex/agent-zero-worldmonitor-integration` @ `62a34af6659852decec5e00da7745f5157cb3dea`
- **Docker:** client 29.6.2 / daemon 29.6.2 (Docker Desktop) / Compose v5.3.1. Python 3.14.6 in `.venv`.
- **Pinned Agent Zero runtime:** release `v2.7`, commit
  `87e1e591e1ba2e8b1a19d34e134fcae490c8dded` (ancestor of tag `v2.7`), image
  `builder/agent-zero:v2.7-87e1e591` (built; OCI revision label verified = `87e1e59…`).

Agent Zero deterministic implementation: **PASS**. WorldMonitor section: **INCOMPLETE** — only
`disasters.earthquakes` is implemented from the approved pinned-upstream scope.

**Docker live acceptance: PASS** for the approved **API-only hardened deployment** (2026-08-03,
Docker Desktop for WSL2). The full Agent Zero chat loop — Builder → ingress → bridge relay →
Squid egress → `host.docker.internal:8100` model gateway → Ollama `qwen3:8b` — is proven live
(`LIVE-MODEL-OK` final response, see below). The original rootful `docker/run` runtime cannot start
under the mandated boundary (it is a supervisord system runtime that drops to root, chmods `/root`,
copies `/per` onto read-only `/`, and needs `SETUID`/`SETGID` for sshd/cron/searxng); the approved
resolution keeps the exact pinned v2.7 commit but runs **only the API/UI process** non-root under a
read-only rootfs with `cap_drop ALL` (the child image `builder/agent-zero-api`). The security
boundary is not weakened. Remaining known constraints are documented upstream defects (token
derivation, SSE-only chat loop) with sanctioned in-scope mitigations recorded below, not blockers.

WorldMonitor live remains outside this Agent Zero acceptance and stays INCOMPLETE (only
`disasters.earthquakes` implemented; other approved capabilities are a confirmed product gap).

## Complete local gate

| Check | Result |
|---|---|
| `UV_CACHE_DIR=/tmp/builder-uv-cache uv lock --check` | PASS — 35 packages resolved |
| `npm ls --all --depth=0` (`ui`) | PASS |
| `ruff format --check .` | PASS — 545 files |
| `ruff check .` | PASS |
| `mypy src/factory scripts` | PASS — 310 source files |
| `pytest --collect-only -q` | PASS — 1,775 collected |
| `pytest -q` | PASS — 1,690 passed, 85 capability skips |
| Section 2 / roadmap PH-3 / PH-4 preinstall / worker substrate | PASS — 18/18, 10/10, 10/10, 18/18 |
| Agent Zero / WorldMonitor deterministic structure | PASS — 12/12; WorldMonitor structure 10/10 with capability scope explicitly INCOMPLETE |
| frontend typecheck / lint / test / build | PASS — 53 tests, production build |

The full gate preceded two direct-review corrections limited to dashboard credential injection and
runtime/configuration enablement distinction. Affected focused regressions after those corrections:
backend `26 passed, 5 loopback capability skips`; launcher `17 passed, 6 loopback capability skips`;
frontend `13 passed`, typecheck, lint, and production build PASS. No unaffected full gate was rerun.

Latest blocker-focused evidence: Agent Zero transactional intake and WorldMonitor scope tests
`17 passed`; affected backend/worker/integration/API gates `49 passed, 5 loopback capability skips`;
frontend `14 passed`, typecheck, lint, and production build PASS. Agent Zero intake now requires an
explicit write/edit grant, validates every returned file before mutation, enforces 100-file,
2,000,000-byte per-file, and 8,000,000-byte total-response ceilings, stages writes, rolls back prior
writes on failure, and cancels the exact active upstream context.

## Environment classifications

- **ENVIRONMENT-BLOCKED:** `UV_CACHE_DIR=/tmp/builder-uv-cache .venv/bin/python
  scripts/verify_section1.py` stops at its required `uv sync --frozen`: pinned
  `hatchling==1.27.0` cannot be fetched because DNS fails with `Temporary failure in name
  resolution`. Rerun with the locked build dependency cached or approved PyPI network access.
- **ENVIRONMENT-BLOCKED:** loopback HTTP tests skip only after socket creation returns
  `[Errno 1] Operation not permitted`. Rerun outside the restricted network sandbox.
- **ENVIRONMENT-BLOCKED:** native-Windows junction tests require Windows semantics (1 skip; not a code defect).

## Live Docker acceptance — 2026-08-03 (Docker Desktop for WSL2, Ubuntu)

### Approved API-only deployment

The pinned upstream `docker/run` image is a rootful supervisord system runtime that cannot start
under the mandated boundary (supervisord `user=root`; `initialize.sh` chmods `/root` and copies
`/per/*` onto read-only `/`; sshd/cron/searxng need `SETUID`/`SETGID`). The approved resolution is
an **API-only child image** derived from the exact pinned source commit; it runs only `run_ui.py`
(uvicorn) as non-root `1000:1000` under `read_only` rootfs with `cap_drop ALL` +
`no-new-privileges` + resource/pids bounds. The security boundary is unchanged from the approved
profile.

Images:

| Image | Provenance | Digest / size |
|---|---|---|
| `builder/agent-zero-parent:404177ac` | parent build of pinned v2.7 source @ `87e1e591…`; OCI revision label verified; build **not byte-reproducible** (documented) | `sha256:404177ac…` (14 GB) |
| `builder/agent-zero-api:v2.7-87e1e591` | `deploy/integrations/agent-zero/Dockerfile.api` from parent; bakes the hardened model preset and pruned offline embedding cache into `/a0/usr` (seeds a fresh volume); reproducible via `docker compose … build agent-zero` (repo-root context) | `sha256:83702a9e…` (14 GB) |

### Topology (approved, kept intact)

`builder-agent-zero` (internal-only, no published ports) → `agent-zero-bridge-relay` (loopback +
internal, socat 8080→agent) → `agent-zero-ingress` (loopback-only `127.0.0.1:50080→8080`→relay) →
`agent-zero-egress` Squid (internal + gateway net, allowlist `host.docker.internal:8100` only).

### PASS

| Gate | Evidence |
|---|---|
| Compose render | `docker compose -f deploy/integrations/agent-zero/compose.yaml --profile builder-enabled config` PASS |
| Agent Zero API image build | `docker build -f deploy/integrations/agent-zero/Dockerfile.api -t builder/agent-zero-api:v2.7-87e1e591 …` PASS; OCI revision label `87e1e591e1ba2e8b1a19d34e134fcae490c8dded`; baked preset + offline cache verified in a fresh volume |
| Containers healthy | all four services up; agent `(healthy)` via `/api/health` 200 within healthcheck bounds |
| Bake on fresh volume | after `down -v` recreate, `/a0/usr/plugins/_model_config/presets.yaml` (Default → `qwen3:8b` via gateway) and 88 MB offline HF cache (14 blobs) seeded from image content; offline `SentenceTransformer` load returns `EMB-OFFLINE-PRUNE-OK` |
| Gateway auth | `127.0.0.1:8100` 401 without bearer, 200 with the runtime model-gateway bearer token |
| Live model round-trip | probe/start_async/poll → **`LIVE-MODEL-OK`** final response (fresh context `SqsIxls4`); Squid `TCP_MISS/200 … POST http://host.docker.internal:8100/api/integrations/model/v1/chat/completions … text/event-stream … HIER_DIRECT/192.168.65.254`; agent-side `mode: chat_completions`, `provider_model_key: openai/qwen3:8b` |
| SSE adapter | Agent Zero v2.7 always sends `stream:true`; normalized only at the route (`_model_completion` → `_sse_completion_response`, `media_type="text/event-stream"`, `[DONE]`). `ModelGateway.complete()` keeps its fail-closed non-streaming contract. 16 route tests incl. no-leak |
| Poll greeting race | client `poll()` now only accepts a final answer logged after the last `user` entry, so the `finished:true` demo greeting (`fw.initial_message.md`) is not mistaken for a final response; regression test added |
| Relay non-proxy | ingress + bridge-relay each listen only `0.0.0.0:8080` (socat) + Docker DNS stub `127.0.0.11`; no other listeners |
| Egress allowlist | Squid forwards only `host.docker.internal:8100`; disabled IPv6 on egress resolves `host.docker.internal` to `192.168.65.254` (`dns_v4_first` obsolete in Squid 6.13) |
| Egress deny external | proxied `GET http://example.com/` → Squid **`TCP_DENIED/403`** `HIER_NONE/-` |
| Cancel / logs lifecycle | `api_terminate_chat` + `api_log_get` work with the derived upstream token (`200 {"success":true}`; 14 log items); see upstream-token defect below |
| Restart / persistence | `docker compose … restart agent-zero` → healthy; presets.yaml, `.env`, `memory/`, HF cache persist in the named volume; post-restart model round-trip works |
| Timeout handling | `LoopbackHttpTransport` raises `TransportTimeout`; `tests/worker_engine/test_agent_zero_official_transport.py` + adapter lifecycle tests PASS |
| Malformed / rollback | malformed JSON → 400; non-object body → 400 `model request must be a JSON object`; wrong model even with `stream:true` → rejected (`requested model is not the selected Builder route`); bad API key on agent → 401 |
| Log redaction | no credentials/tokens appear in agent/squid/relay/orchestrator logs; SSE route tests assert no token/prompt leak |

### Known upstream defects (documented, with sanctioned mitigations)

- **Model preset override:** v2.7 chat model is not driven by `A0_SET_chat_model_*`; the
  `_model_config` plugin's `Default` preset (openrouter/gpt-5.6-terra) overrides. Fixed by baking
  `presets.yaml` (Default chat+utility → `provider: openai`, `name: qwen3:8b`,
  `api_base: http://host.docker.internal:8100/api/integrations/model/v1`). Plugin generates the file
  only when absent, so the baked override is authoritative.
- **Offline embedding:** `_memory` downloads `all-MiniLM-L6-v2` from huggingface.co on first turn.
  Fixed by baking the pruned offline cache (safetensors + metadata, 88 MB, verified offline) with
  `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1`.
- **SSE-only chat loop:** v2.7 always requests `stream:true`; `ModelGateway.complete()` rejects
  streaming by design. Sanctioned mitigation: SSE compatibility adapter **only at the route**
  (normalizes `stream`, returns OpenAI SSE chunks + `[DONE]`). Core gateway streaming rejection
  contract preserved.
- **`create_auth_token` overwrite:** `normalize_settings` overwrites `A0_SET_mcp_server_token` with
  `create_auth_token()` (a sha256-derived token regenerated at startup; value not recorded here). The
  `requires_api_key` endpoints (`api_log_get`, `api_terminate_chat`) check the derived token, so
  Builder's configured key gets 401. Verified: the endpoints work with the derived token (see
  lifecycle gate). No security boundary weakened; recorded as an upstream defect to revisit.
- **Poll greeting race** (Builder client): fixed + regression-tested, above.

### Historical blocker (resolved by the API-only deployment)

The original full-runtime attempt was BLOCKED because the pinned `docker/run` image could not start
under the boundary: supervisord `user=root`; `initialize.sh` chmod `/root` + `cp -r /per/* /` on
read-only `/`; sshd/cron/searxng need `SETUID`/`SETGID`. A rootful full-capability probe reached
`/api/health` 200, isolating the blocker to the runtime profile. This PR's approved resolution is
the API-only child image above; the security boundary is not weakened.

### Deterministic gates rerun on this worktree (all PASS)

| Gate | Command | Result |
|---|---|---|
| Full test suite | `pytest -q` | 1799 passed, 2 skipped (junction = Windows), 1 pre-existing unrelated failure (`test_agent_task_and_worldmonitor_refresh_return_real_durable_payloads`, fails with these changes stashed too) |
| Orchestrator / API / integrations / worker-engine | `pytest tests/orchestrator_api tests/integrations/agent_zero tests/worker_engine/test_agent_zero_official_transport.py tests/worker_engine/test_worker_engine_service.py -q` | 184 passed, 1 skipped, 1 pre-existing unrelated failure |
| Agent Zero structure verifier | `scripts/verify_agent_zero_structure.py` | PASS 12/12 |
| Ruff | `ruff check …` (changed files) | PASS |
| mypy --strict | `mypy` | PASS (283 source files, `strict`, `warn_unreachable`) |
| Secret / debug / dead-path scan | grep over src/tests/scripts/docs/deploy | no secrets, no debug/TODO/FIXME markers in changed source |
| Official client | `pytest tests/integrations/agent_zero/test_official_client.py -q` | 7 passed (incl. new greeting-race regression test) |
| Model gateway route | `pytest tests/orchestrator_api/test_model_gateway_route.py -q` | 16 passed |

### Changed files (working tree; not committed per task rules)

- `deploy/integrations/agent-zero/compose.yaml` — agent env (preset interplay + gateway base URL +
  `A0_SET_litellm_global_kwargs={"stream":false}`), egress IPv6 disable sysctl fix, `HF_HUB_OFFLINE` /
  `TRANSFORMERS_OFFLINE`; keeps pinned parent build context, `read_only`, `cap_drop ALL`,
  `no-new-privileges`, loopback ports.
- `deploy/integrations/agent-zero/Dockerfile.api` (untracked) — API-only child image; bakes the
  model preset (`agent-zero-presets/presets.yaml`) and pruned offline HF cache
  (`agent-zero-hf-cache/huggingface`) into `/a0/usr` so a fresh volume is seeded from image content.
- `deploy/integrations/agent-zero/squid.conf` — allowlist unchanged; `dns_v4_first on` removed
  (obsolete in Squid 6.13); IPv6 disabled at the egress container level instead.
- `src/factory/orchestrator_api/app.py` — `_model_completion` SSE compatibility adapter +
  `_sse_completion_response` (route-only `stream` normalization).
- `src/factory/integrations/agent_zero/official_client.py` — `poll()` ignores the demo greeting
  (accepts a final answer only when logged after the last `user` entry).
- `tests/orchestrator_api/test_model_gateway_route.py` (untracked) — SSE/contract tests.
- `tests/integrations/agent_zero/test_official_client.py` — greeting-race regression test.
- `tests/integrations/test_compose_manifests.py`, `config/builder.yaml` (agent_zero enabled only),
  docs.

### Notes

- Live artifacts are temporary: orchestrator/gateway DBs and logs under `/tmp/opencode/az-gateway/`;
  stack credentials are runtime placeholders supplied only via environment for compose
  interpolation — never written to files.
- Parent image build is not byte-reproducible (documented); the child API image and pinned source
  commit are deterministic.
- The two Compose projects use distinct ports, networks, volumes, and resource budgets.

## Direct review

**PASS** for the implemented deterministic scope and the accuracy of its incomplete classification.
Review covered model/approval authority,
disposable workspace and path boundaries, immutable provenance, async cancellation/recovery,
managed migration integrity, failed-start cleanup, degraded evidence, enablement, browser credential
exposure, dead placeholder paths, secrets, and Docker-socket isolation. WorldMonitor’s remaining
approved capabilities are a confirmed product gap, not an environment skip;
Docker and host-capability gates remain separately blocked as listed above.
