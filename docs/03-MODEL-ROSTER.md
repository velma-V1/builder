# Approved Model and Coding-Worker Roster

**Status:** Approved architecture record  
**Recorded:** July 23, 2026  
**Rule:** No silent substitutions

## 1. Permanent local runtime

Ollama is the permanent local model runtime for Factory v1.

Factory must remain fully usable for its approved basic workflow without another local runtime, Codex, VS Code, OpenHands, or a hosted provider.

## 2. Primary local coding worker

| Worker | Runtime | Primary Factory role |
|---|---|---|
| Aider | Ollama-backed models | Primary bounded local coding worker for repository inspection, implementation, repair, test-driven iteration, and diff production |

Aider operates beneath the deterministic watchdog through a coding-worker adapter. It cannot certify its own work, change authoritative task state, expand path ownership, bypass permissions, merge protected branches, publish, or release.

## 3. Local model assignments

| Runtime | Exact model ID | Primary Factory role |
|---|---|---|
| Ollama | `qwen3:8b` | Fast local dispatcher, task-packet preparation, classification, summaries, log compression, routine work, and suitable Aider coding tasks |
| Ollama | `qwen3:14b` | Local judgment supervisor, difficult planning, architecture review, escalation review, stronger local coding or repair work, and recovery assistance |

The deterministic watchdog remains above Aider and both models. No local worker or model can certify its own work.

## 4. Hosted lane assignments — optional secondary capacity

Hosted lanes remain approved secondary capacity. They are not required for basic Factory operation and do not replace the Aider + Ollama primary local path.

### Lane 1 — Groq

| Position | Exact provider model ID | Assigned role |
|---|---|---|
| Worker | `qwen/qwen3.6-27b` | Fast agentic coding, implementation, tool use, visual understanding when required, and suitable light-to-hard component tasks |
| Reviewer | `openai/gpt-oss-120b` | Independent reasoning review, difficult repairs, contract and evidence review, and Worker takeover when required |

### Lane 2 — Cerebras

| Position | Exact provider model ID | Assigned role |
|---|---|---|
| Worker | `qwen-3-235b-a22b-instruct-2507` | Fast large-model implementation, planning, analysis, and bounded component work |
| Reviewer | `gpt-oss-120b` | Independent reasoning review, difficult coding and repair, evidence inspection, and Worker takeover when required |

### Lane 3 — NVIDIA

| Position | Exact provider model ID | Assigned role |
|---|---|---|
| Worker | `poolside/laguna-xs-2.1` | Long-horizon agentic coding, terminal work, implementation, debugging, and iterative repair |
| Reviewer | `nvidia/nemotron-3-ultra-550b-a55b` | Frontier reasoning, architecture and integration review, long-context inspection, complex repair, and Worker takeover when required |

## 5. Tool and platform status

| Component | v1 status |
|---|---|
| Ollama | Required permanent local runtime |
| Aider | Required primary local coding worker |
| Builder Dashboard | Required primary interface |
| Monaco editor | Required built-in editor |
| Built-in file explorer | Required built-in workspace component |
| VS Code | Optional external tool through a disabled-by-default adapter |
| Codex | Not a required dependency; optional external development aid only |
| OpenHands | Deferred possible future addition; excluded from v1 dependencies and acceptance criteria |

## 6. Explicit model exclusion

`GLM-4.7` and `zai-glm-4.7` are not approved Factory models and must not appear in default configuration, fallback lists, documentation examples, tests, or generated setup files.

## 7. Routing hierarchy

The default local-first hierarchy is:

1. route suitable coding work to Aider using an approved Ollama model;
2. use `qwen3:8b` for fast dispatch, routine tasks, and suitable local work;
3. escalate locally to `qwen3:14b` for difficult work, judgment, review, or recovery;
4. use an approved hosted Worker or Reviewer only when cloud permission, privacy, availability, quota, and task benefit allow it;
5. fall back to the approved local Aider + Ollama path when hosted capacity is unavailable;
6. pause only the affected task when no approved path can safely perform it.

The router selects by demonstrated task capability, not parameter count alone.

## 8. Availability and deprecation handling

Ollama health, exact local model availability, context limits, and resource state must be checked before assignment when cached status is stale.

Hosted provider catalogs, availability, context limits, tool support, and quotas may also change. Availability changes do not authorize model replacement.

If an exact approved model is removed or unavailable:

- record the runtime or provider response and timestamp;
- use only an approved paired or local route when suitable;
- mark the affected route degraded;
- require user approval before adding a replacement model.

Aider failure does not authorize an unapproved coding worker. The task may retry, recover, use an approved hosted lane when allowed, or pause accurately.

## 9. Privacy boundary

Private project material remains local unless the user explicitly grants task-scoped cloud permission. The router must evaluate privacy before hosted capability or speed.

## 10. Provider source references

- Groq model catalog: `https://console.groq.com/docs/models`
- Cerebras model catalog: `https://inference-docs.cerebras.ai/models/overview`
- NVIDIA model catalog: `https://build.nvidia.com/models`

These links validate provider identifiers and availability only. They do not replace Factory evaluation, task tests, or user approval.