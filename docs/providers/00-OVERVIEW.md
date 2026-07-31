# Providers 00 — Overview

Hosted provider adapters, **BUILT_NOT_ACTIVATED**. A shared OpenAI-compatible core drives
OpenRouter / Hugging Face / Together; Replicate uses a separate prediction lifecycle. Every hosted
call passes the brokered envelope: **privacy (CLOUD_ALLOWED) → task-scoped NetworkApproval → short
SecretBroker lease → redirect containment → byte charge → redaction → lease revoke**. No live call
is possible (only the deterministic `FakeHttpTransport`); no keys are read.

| Provider | Secret ref | Core | Doc |
|---|---|---|---|
| OpenRouter | `OPENROUTER_API_KEY` | OpenAI-compatible | 02 |
| Hugging Face | `HF_TOKEN` | OpenAI-compatible | 03 |
| Together | `TOGETHER_API_KEY` | OpenAI-compatible | 04 |
| Replicate | `REPLICATE_API_TOKEN` | prediction lifecycle | 05 |

**Invariants:** discovery ≠ approval; adapter fallback forbidden (router owns fallback); returned
model + upstream provider verified (mismatch fails closed); a provider failure is never a success.
State: `HOSTED_EGRESS := DISABLED_BY_DEFAULT`, `PROVIDER_KEYS := NOT_PROVISIONED`,
`LIVE_PROVIDER_CALLS := NOT_EXECUTED`.
