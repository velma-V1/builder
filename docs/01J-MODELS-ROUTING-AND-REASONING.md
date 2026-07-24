# Approved Models, Routing, and Reasoning Decision

**Status:** Approved architecture supplement  
**Recorded:** July 23, 2026

## 1. Governing model boundary

Factory is local-first and routes work through approved Ollama-hosted models according to declared task type, model capability, resource limits, and deterministic policy. Model output remains a claim until verified through an approved method.

Authoritative task state is stored in model-neutral Factory records. Model switching, unloading, fallback, or failure cannot erase approved requirements, evidence, checkpoints, or open dependencies.

## 2. Approved Stage 8 decisions

1. **Task-based selection:** Model selection is based on declared task type and approved model roles.
2. **Visible deterministic routing:** Routing rules are deterministic, testable, and visible to the operator.
3. **Operator override:** The operator may override the selected model within resource, sandbox, permission, and compatibility limits.
4. **Model identity evidence:** Every task records model name, version, quantization, runtime, context settings, sampling settings, and other material configuration.
5. **Stage pinning:** Model identity and material settings are pinned for the duration of an active task stage unless an approved switch or fallback occurs.
6. **VRAM unloading:** Inactive GPU models unload when another approved model requires the available VRAM.
7. **Model-neutral state:** Factory preserves authoritative state in model-neutral task records rather than relying on one model's conversation history.
8. **Structured handoffs:** Model handoffs use structured context packets containing applicable requirements, decisions, state, evidence, artifacts, constraints, and open questions.
9. **Relevant context only:** Context packets exclude irrelevant raw history and do not replace authoritative source records.
10. **Context and output budgets:** Each model has configurable context, output, time, and resource budgets appropriate to its role.
11. **Authority order:** Current approved requirements and source records outrank model-generated summaries or interpretations.
12. **Orchestrated delegation:** Models cannot directly delegate work to another model. Delegation passes through the Orchestrator, task policy, and resource scheduler.
13. **Safe CPU concurrency:** CPU-only model work may continue while another approved model uses the GPU when verified resource limits permit it.
14. **No silent fallback:** Automatic fallback to a different model never occurs silently.
15. **Compatible fallback:** Factory may use a pre-approved compatible fallback after failure when the substitution is visible, recorded, and covered by the task's verification requirements.
16. **Bounded retries:** Model failures use bounded retries and cannot enter infinite retry loops.
17. **Failure quarantine:** Repeated equivalent model-task failures trigger quarantine and operator review.
18. **Health checks:** Factory performs model availability, identity, configuration, and basic response health checks before important or high-risk tasks.
19. **Representative roster evidence:** Model-roster changes require benchmark evidence from representative Factory tasks, not generic benchmarks alone.
20. **Benchmark dimensions:** Model evaluation measures correctness, instruction following, coding quality, reasoning quality where applicable, latency, VRAM, RAM, stability, and failure behavior.
21. **Schema validation:** Model output intended for tools or state transitions must pass expected-schema and policy validation before use.
22. **Approved tool gateway:** Models call tools only through the approved tool gateway and cannot bypass permissions or auditing.
23. **No permanent hidden reasoning storage:** Factory does not permanently store hidden reasoning traces. It stores concise decisions, inputs, outputs, evidence, uncertainty, and actionable rationale.
24. **No required cloud dependency:** Cloud models are not required for normal Factory operation.
25. **Optional cloud adapters:** Optional cloud adapters may be added later only through separate approval, remain disabled by default, and follow explicit data, permission, and cost controls.
26. **Repeated promotion evidence:** A model is not promoted to a reusable role because of one successful test. Promotion requires repeated representative evidence.
27. **Drift rechecks:** Model performance is rechecked after material model, quantization, runtime, driver, prompt-policy, or hardware changes.

## 3. Operating boundaries

- Routing is automatic but visible and operator-overridable.
- Model switching never loses authoritative task state.
- Fallback must be predefined, compatible, disclosed, and evidenced.
- Cloud support remains optional, disabled by default, and unnecessary for core operation.
- Factory records actionable rationale and evidence rather than private reasoning traces.

## 4. Acceptance criteria

This decision is satisfied only when tests prove that:

1. routing follows declared deterministic rules and exposes the selected model and reason;
2. operator overrides remain within permissions and hardware limits;
3. task evidence identifies the exact model and material settings used;
4. a task stage cannot silently change model identity;
5. model unloading and switching preserve model-neutral task state;
6. handoff packets contain required current authority and exclude irrelevant raw history;
7. models cannot delegate or call tools outside the Orchestrator and approved gateway;
8. fallback cannot occur silently and is recorded in evidence;
9. repeated failures trigger bounded retry and quarantine behavior;
10. malformed model output cannot become a tool action or state transition;
11. cloud services are not required for local Factory operation;
12. roster changes require repeated representative benchmark evidence.