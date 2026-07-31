# Preinstall 07 — Secret Placeholder Procedure

No real secret is created, stored, or transmitted during preinstall. This defines how secrets are
represented as **placeholders** now and provisioned later through the secret broker.

## Principles

- **No secret in the repo.** `.gitignore` already excludes `.env*`, `*.key`, `*.pem`, `*.p12`,
  `credentials.*`, `/secrets/`, tokens, etc. Only `.env.example` (placeholder) is ever committed.
- **Placeholders only.** Configuration references a secret by **id/reference**, never by value
  (e.g. `OLLAMA_HOST=http://localhost:11434`, `GROQ_API_KEY=<provisioned-via-secret-broker>`).
- **Broker-provisioned at runtime.** Real values are injected by the secret broker
  (`factory.secret`) at live time — redacted in logs, revoke-and-forget supported, export-scanned.
  They are never written to the repo or to readiness output.
- **Redaction everywhere.** Any readiness/inventory output is redacted
  (`factory.livegate.redaction`) before it is written or shared.

## Placeholder file (example, committed as `.env.example` only)

```dotenv
# Local, non-secret defaults:
OLLAMA_HOST=http://localhost:11434
FACTORY_HOSTED_EGRESS=disabled
# Secret REFERENCES (values provisioned by the secret broker at live time — never commit values):
GROQ_API_KEY=<provisioned-via-secret-broker>
CEREBRAS_API_KEY=<provisioned-via-secret-broker>
NVIDIA_API_KEY=<provisioned-via-secret-broker>
```

## Operator action (later, under authorization)

Provision real values into the secret broker on the host, only for hosted providers you have
explicitly approved (Preinstall 06). Confirm redaction by checking they never appear in
`.livegate-out/readiness.json` or any log.
