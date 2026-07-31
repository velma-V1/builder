# Preinstall 06 — Local-Only Network Policy

Source of truth: `factory.preinstall.network_policy`. `HOSTED_EGRESS := DISABLED_BY_DEFAULT`.

## Policy

- **Default-deny, local-first.** Workers run on an internal-only network and reach nothing off-box
  directly. Loopback / private / link-local destinations are allowed locally.
- **Hosted (cloud) egress is disabled by default** (`HOSTED_EGRESS_DEFAULT_ENABLED = False`). A
  hosted destination is denied with `HOSTED_EGRESS_DISABLED` unless the operator explicitly enables
  egress **and** approves that exact destination (`HOSTED_DESTINATION_NOT_APPROVED` otherwise).
- All egress, when enabled, flows through the **broker** (the sole dual-homed service); workers never
  egress directly. Credentials for any hosted provider are handled by the secret broker (Preinstall
  07), never embedded.

## Evaluation

`NetworkPolicy.evaluate(destination)` returns `(allowed, reason)`:

| Destination | Default policy result |
|---|---|
| `127.0.0.1`, `10.x`, `192.168.x`, `localhost` | `True, LOCAL_ALLOWED` |
| any hosted hostname | `False, HOSTED_EGRESS_DISABLED` |
| hosted hostname, egress enabled but not approved | `False, HOSTED_DESTINATION_NOT_APPROVED` |
| hosted hostname, egress enabled and approved | `True, HOSTED_APPROVED` |

## Operator decision

Enabling hosted egress and approving specific providers (Groq / Cerebras / NVIDIA) is an explicit
operator decision (see `docs/live-gate/08`, "hosted routes"). Off by default; nothing is enabled here.
