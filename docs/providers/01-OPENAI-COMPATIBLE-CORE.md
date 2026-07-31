# Providers 01 — OpenAI-Compatible Core

`factory.providers.openai_core.OpenAICompatibleAdapterCore` — one HTTP client seam (injected
`BrokeredHttp`); no per-provider duplicate clients.

- **chat** (non-streaming): builds `{model, messages, max_tokens, stream:false, **extra}`; verifies
  the returned `model` equals the requested model (`RETURNED_MODEL_MISMATCH` otherwise) and the
  upstream `provider` equals the expected one (`PROVIDER_MISMATCH` otherwise).
- **discovery** (`GET /models`): read-only; returns `DiscoveredModel`s — never approval.
- **capability gate:** a required capability not advertised → `CAPABILITY_UNAVAILABLE`.
- **usage** normalized to `UsageRecord`; request id captured.

## Failure mapping (HTTP → code)
401/403 → AUTH_UNAVAILABLE · 404 → MODEL_MISSING · 408/timeout → TIMED_OUT · 409 → PROVIDER_CONFLICT
· 429 → RATE_LIMITED · 5xx/transport → RUNTIME_UNAVAILABLE · bad JSON/schema → MALFORMED_OUTPUT ·
unsupported feature → CAPABILITY_UNAVAILABLE. **Never** converts a failure into success; **never**
retries against another model/provider (Builder router owns fallback).
