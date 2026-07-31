# WorldMonitor 05 — Model Routing

WorldMonitor obtains AI **only** through `ModelRouterPort` (`request_ai` → `AiCapabilityRequest`).
Builder selects the approved route and enforces privacy/cost/resources; the result returns with a
model fingerprint + provider route. Defaults: `LOCAL_FIRST := true`, `HOSTED_REQUIRES := CLOUD_ALLOWED`,
`SILENT_CLOUD_FALLBACK := false`. Future routes (task-compatible): Ollama, NVIDIA, OpenRouter,
Hugging Face, Together, Replicate. WorldMonitor holds no provider adapter and no key
(`verify_worldmonitor_structure.py` enforces the router-only slot).
