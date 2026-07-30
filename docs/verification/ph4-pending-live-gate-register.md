# PH-4 Pending Live-Gate Register

Work that is **out of scope for preinstallation** and remains gated behind installation and live
validation. Nothing below is claimed complete. The preinstallation core is built against deterministic
fakes; each item here replaces a fake with a live backend under the *same* interface and adds the
live acceptance evidence.

| Gate | Depends on | What remains | Blocked by |
|---|---|---|---|
| LG-4.1 Live Ollama runtime adapter | installed Ollama daemon | implement `src/factory/models/ollama_adapter` live adapter against the daemon (health/version, exact-model pull/discovery, real call/cancel); prove local-only operation | `NOT_AUTHORIZED`: software_installation, model_installation, live_Ollama_execution |
| LG-4.2 Live Aider worker adapter | installed Aider + Ollama models | implement `src/factory/workers/aider_adapter` live adapter (bounded submit/stream/revise/cancel/collect over real Aider); prove owned-path enforcement on a real repo | `NOT_AUTHORIZED`: software_installation, live_Aider_execution |
| LG-4.3 Real model fingerprints | live daemon | populate fingerprints from real weight/manifest digests, quantization, runtime/driver versions | live runtime |
| LG-4.4 Live resource sensing | host GPU/OS sensors | replace `SensorReading` fakes with real VRAM/RAM/storage/thermal reads; validate reservations against live pressure | host hardware access |
| LG-4.5 Durable exec-record + quota store | PH-2 runtime DB migrations | wire the append-only `ExecutionLedger` / `QuotaLedger` to a durable SQLite store under `migrations/runtime/` with SHA-pinned migrations and crash reconciliation | migrations (not added in preinstallation) |
| LG-4.6 Health-check live probes | live daemon | real availability/identity/config/response probes on the `01J §3.4` triggers | live runtime |
| LG-4.7 Roster benchmark evidence (`01J §5.18`) | representative Factory tasks on live models | repeated representative benchmark evidence before any roster change | live runtime |
| LG-4.8 IP-2 (PH-4 ∥ PH-5 integration) | PH-5 sandbox/isolation | integrate live routing with live sandbox execution | PH-5 live |

**Promotion posture:** PH-4 preinstallation is `COMPLETE`; `PROM-PH4` is `NOT_AUTHORIZED`. Promotion
requires the live gates above plus separate operator authorization, exactly as RPH-3 required.
