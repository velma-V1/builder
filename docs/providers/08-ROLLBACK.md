# Providers 08 — Rollback / Disable

To disable a provider: remove its `ApprovedHostedRoute`; revoke its key from the `SecretBroker`
(`revoke`/`revoke_task`); set hosted egress off / remove the approved domain. Nothing is installed,
so there is nothing to uninstall — the adapters are inert without an approved route + task-scoped
grant + provisioned key. Reverting the PR removes the code entirely.
