# Providers 02 — OpenRouter

Config: base `https://openrouter.ai/api/v1`, approved domain `openrouter.ai`, secret
`OPENROUTER_API_KEY`. Strict routes require an exact model slug + an explicit upstream provider.

Request policy (always): `provider.allow_fallbacks=false`, `require_parameters=true`,
`data_collection="deny"`; `provider.zdr=true` when the route requires ZDR; `provider.order=[upstream]`
when an explicit upstream is set. A strict route with no upstream → `CAPABILITY_UNAVAILABLE`.

Verified on response: returned model, upstream provider, usage, request id. Rejected: unexpected
upstream, unexpected model, hidden fallback, missing capability. Recorded on the fingerprint:
OpenRouter slug, upstream provider, returned model, privacy, (pricing when supplied).
