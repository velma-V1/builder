# Approved Model Roster

**Status:** Approved architecture record  
**Recorded:** July 22, 2026  
**Rule:** No silent substitutions

## 1. Local control and fallback

| Runtime | Exact model ID | Primary Factory role |
|---|---|---|
| Ollama | `qwen3:8b` | Fast local dispatcher, task-packet preparation, classification, summaries, log compression, routine work, and first local fallback |
| Ollama | `qwen3:14b` | Local judgment supervisor, difficult planning, architecture review, escalation review, stronger local fallback, and recovery assistance |

The deterministic watchdog remains above both models. Neither local model can certify its own work.

## 2. Hosted lane assignments

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

## 3. Explicit exclusion

`GLM-4.7` and `zai-glm-4.7` are not approved Factory models and must not appear in default configuration, fallback lists, documentation examples, tests, or generated setup files.

## 4. Routing hierarchy

For each hosted lane:

1. route suitable implementation work to the Worker;
2. route independent review and clearly difficult work to the Reviewer;
3. allow the Reviewer to take over when the Worker fails capability checks, exhausts quota, becomes unavailable, or exceeds its repair limit;
4. fall back to `qwen3:8b` for suitable local work;
5. escalate locally to `qwen3:14b` for difficult work or judgment;
6. pause only the affected task when no approved model can safely perform it.

The router selects by demonstrated task capability, not parameter count alone.

## 5. Availability and deprecation handling

Provider catalogs, availability, context limits, tool support, and quotas can change. The Factory must query provider model-list or capability endpoints during setup and before assignment when cached status is stale.

Availability changes do not authorize model replacement.

If an exact approved model is removed or unavailable:

- record the provider response and timestamp;
- use only its paired approved model when suitable;
- otherwise use the approved local fallback path;
- mark the lane degraded;
- require user approval before adding a replacement model.

## 6. Privacy boundary

Private project material remains local unless the user explicitly grants task-scoped cloud permission. The router must evaluate privacy before hosted capability or speed.

## 7. Provider source references

- Groq model catalog: `https://console.groq.com/docs/models`
- Cerebras model catalog: `https://inference-docs.cerebras.ai/models/overview`
- NVIDIA model catalog: `https://build.nvidia.com/models`

These links validate provider identifiers and availability only. They do not replace Factory evaluation, task tests, or user approval.