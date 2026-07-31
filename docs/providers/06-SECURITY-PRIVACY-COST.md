# Providers 06 — Security, Privacy & Cost

- **Network:** every request via `NetworkBroker` under a task-scoped `NetworkApproval` (approved
  host + method + byte ceiling); redirects re-validated; bytes charged. No direct HTTP library in any
  adapter (`verify_provider_adapters.py` enforces).
- **Secrets:** leased from `SecretBroker` per call, put only on the `Authorization` header, revoked
  in `finally`. Never read from the environment, persisted, logged, or placed in exceptions/records.
  Refs: `OPENROUTER_API_KEY`, `HF_TOKEN`, `TOGETHER_API_KEY`, `REPLICATE_API_TOKEN`.
- **Privacy:** `LOCAL_ONLY` tasks can never reach a host; hosted requires a task-scoped
  `CLOUD_ALLOWED` grant. `HOSTED_EGRESS := DISABLED_BY_DEFAULT`.
- **Cost:** `ApprovedHostedRoute.cost_ceiling_usd` per route; `CostRecord` carries pricing only when
  the provider supplied it (`priced=false` ⇒ unknown, not zero-cost).
