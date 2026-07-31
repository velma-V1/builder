# 04 — Ollama & Approved-Model Availability

PH-4 live routing needs the approved **local** models present in Ollama, and the excluded model
absent. This is a read-only availability check; installing Ollama and pulling models are operator
actions (document 08).

## Gate `ollama-models` (mandatory)

| Item | Value |
|---|---|
| Probe | `ollama list` (read-only) |
| Parser | `factory.livegate.version_probe.parse_ollama_list` |
| Approved local models | `qwen3:8b` (dispatcher), `qwen3:14b` (supervisor) — from `factory.routing.roster` |
| Excluded | `glm-4.7`, `zai-glm-4.7` — must **not** be installed (`EXCLUDED_MODEL_IDS`) |
| PASS when | every approved model present **and** no excluded model installed |
| FAIL when | an approved model missing, or an excluded model present |
| UNAVAILABLE when | Ollama not running / no models |

Single source of truth: the approved/excluded sets are imported directly from the routing roster, so
this check cannot drift from the router's own policy.

## Approved-model provisioning (operator, under authorization)

```bash
# Read-only check first:
ollama list

# Provision the approved local models (operator action; do NOT run during preparation):
ollama pull qwen3:8b
ollama pull qwen3:14b

# Confirm the excluded model is absent (remove if present):
ollama list | grep -i glm && ollama rm glm-4.7 || true
```

The Aider coding worker (`aider`) is a coding-tool worker, not an Ollama-served model tag; its live
readiness is covered by the PH-5 sandbox/tooling acceptance criteria, not this gate.

## Hosted (cloud) routes

Hosted secondary routes (Groq / Cerebras / NVIDIA) are cloud APIs, not local Ollama models, and are
out of scope for this local-availability gate. They are reachable only via the egress broker under
the default-deny network policy, and their credentials are handled by the secret broker — never
probed or stored here.
