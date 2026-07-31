# Providers 03 — Hugging Face (Inference Providers)

Config: base `https://router.huggingface.co/v1`, approved domain `router.huggingface.co`, secret
`HF_TOKEN`. Requires an exact model + an **explicit inference provider**. In strict mode,
`auto`/`fastest`/`cheapest`/empty are forbidden (`CAPABILITY_UNAVAILABLE`). The actual provider is
verified when returned (`PROVIDER_MISMATCH` otherwise). Hub discovery is never approval.
