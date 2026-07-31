# Providers 07 — Live Acceptance Plan (for later; NOT executed)

`LIVE_PROVIDER_TESTS := NOT_EXECUTED_NOT_AUTHORIZED`. Before any live provider call (separate
authorization): provision the provider key into the `SecretBroker` (never the repo/env); enable
hosted egress and approve the exact domain; declare the `ApprovedHostedRoute`. Then, per provider,
confirm on live infra: exact-model success + returned-model match; upstream-provider match; usage +
request id captured; 401/404/429/5xx mapping; timeout + cancellation; hidden-fallback rejection;
Replicate create→succeed / timeout→cancel with pinned version + output-URL validation. Each live
check has a deterministic fake-parity test already passing in `tests/providers/`.
