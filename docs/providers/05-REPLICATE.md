# Providers 05 — Replicate (prediction lifecycle)

Not chat-completion. Config: base `https://api.replicate.com/v1`, approved domain
`api.replicate.com`, secret `REPLICATE_API_TOKEN` (auth scheme `Token`).

Lifecycle: resolve exact `owner/name` at a **pinned version** → validate input against approved
schema keys → `POST /predictions {version,input}` → poll `GET /predictions/{id}` (bounded
`max_polls`) → on timeout `POST /predictions/{id}/cancel`. States: starting/processing/succeeded/
failed/canceled. Output normalized; every output URL host must be in the route's approved domains
(`OUTPUT_URL_DENIED` otherwise). Rejected: version drift (`PROVIDER_CONFLICT`), unpinned/community
route, unknown input key, output outside the normalizer. Scope: prediction polling only — no
webhooks, deployments, model/version creation, training, or mutation APIs.
