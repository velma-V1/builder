# Preinstall 05 — Ollama Model Roster

Single source of truth: `factory.routing.roster` (imported by the readiness check, so the roster and
the check cannot drift). Availability is a read-only probe; pulling models is an operator action.

## Approved local models (must be present for PH-4 live)

| Tag | Role | Resource class |
|---|---|---|
| `qwen3:8b` | dispatcher | GPU-light |
| `qwen3:14b` | supervisor | GPU-heavy |

The Aider coding worker (`aider`) is a coding-tool worker, not an Ollama-served tag; its readiness is
covered by the PH-5 sandbox/tooling criteria.

## Excluded (must NOT be installed)

`glm-4.7`, `zai-glm-4.7` (`factory.routing.roster.EXCLUDED_MODEL_IDS`). The readiness gate
`ollama-models` FAILs if an excluded model is present.

## Provisioning (operator, under authorization)

```bash
ollama list                 # read-only check first
ollama pull qwen3:8b        # operator action — NOT run during preinstall
ollama pull qwen3:14b
ollama list | grep -i glm && ollama rm glm-4.7 || true
```

## No silent substitution

The router never silently substitutes a model (proven by `verify_ph4` and the routing tests). The
readiness gate confirms the exact approved tags are present and no excluded tag is installed, so
routing never needs to substitute.
