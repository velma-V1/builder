# Approved Models, Routing, and Reasoning Decision

**Status:** Approved architecture supplement  
**Recorded:** July 23, 2026  
**Clarified:** July 23, 2026

## 1. Governing model boundary

Factory is local-first and routes work through approved Ollama-hosted models according to declared task type, model capability, executable resource limits, and deterministic policy. Model factual, acceptance, action-authorizing, and completion claims remain unverified until confirmed through an approved method. Ordinary conversational output does not require artificial verification unless it creates or supports one of those consequential claims.

Authoritative task state is stored in model-neutral Factory records. Model switching, unloading, fallback, or failure cannot erase approved requirements, evidence, checkpoints, execution provenance, or open dependencies.

## 2. Approved Stage 8 decisions

1. **Task-based selection:** Model selection is based on declared task type and approved model roles.
2. **Visible deterministic routing:** Routing rules are deterministic, testable, and visible to the operator.
3. **Operator override:** The operator may override the selected model within resource, sandbox, permission, and compatibility limits.
4. **Model identity evidence:** Every task records exact model identity and all material runtime configuration.
5. **Stage pinning:** Model identity and material settings are pinned for the duration of an active task stage unless an approved switch or fallback starts a new execution record.
6. **VRAM unloading:** Inactive GPU models unload when another approved model requires the available VRAM.
7. **Model-neutral state:** Factory preserves authoritative state in model-neutral task records rather than relying on one model's conversation history.
8. **Structured handoffs:** Model handoffs use structured context packets containing applicable requirements, decisions, state, evidence, artifacts, constraints, and open questions.
9. **Relevant context only:** Context packets exclude irrelevant raw history and do not replace authoritative source records.
10. **Context and output budgets:** Each model has configurable context, output, time, and resource budgets appropriate to its role.
11. **Authority order:** Current approved requirements and source records outrank model-generated summaries or interpretations.
12. **Orchestrated delegation:** Models cannot directly delegate work to another model. Delegation passes through the Orchestrator, task policy, and Resource Scheduler.
13. **Safe CPU concurrency:** CPU-only model work may continue while another approved model uses the GPU only when configured executable limits permit it.
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
27. **Drift rechecks:** Model performance is rechecked after material model, quantization, runtime, driver, prompt-policy, tool-schema, context, sampling, or hardware changes.

## 3. Binding model-routing clarifications

### 3.1 Complete model fingerprint

Every model-execution record contains a deterministic fingerprint including, when applicable:

- model family and declared name;
- weight, artifact, or manifest digest;
- quantization and format;
- Ollama and underlying runtime version;
- context-window and context-allocation configuration;
- sampling and decoding settings;
- system-instruction or policy-prompt version;
- tool-schema version;
- adapter and routing-policy version;
- material GPU, driver, and runtime configuration.

A display name or mutable model tag alone is not sufficient identity evidence.

### 3.2 Fallback provenance boundary

A fallback model may not silently continue the failed model's execution provenance.

Factory must:

1. terminate, fail, or create a verified checkpoint for the affected attempt;
2. preserve the failed attempt's inputs, outputs, errors, evidence, and model fingerprint;
3. record the approved substitution and reason;
4. create a new model-execution record;
5. restart the affected stage or smallest independently verified unit under the fallback;
6. rerun all verification gates affected by the substitution.

The fallback may consume model-neutral authoritative state and a structured handoff packet, but it cannot inherit an unverified completion state from the failed model.

### 3.3 Executable Resource Scheduler limits

The Resource Scheduler uses versioned configured limits rather than informal judgments. Policies include at least:

- maximum GPU VRAM reservation by model and task class;
- maximum system RAM reservation;
- minimum free RAM before CPU-model loading;
- CPU model concurrency limit and sustained utilization ceiling;
- minimum free storage and emergency-reserve protection;
- model unload and cancellation timeout;
- model preload, identity-check, and health-check timeout;
- thermal, driver-reset, allocation-failure, and instability response;
- deterministic resource-pressure pause and cancellation order;
- cooldown and minimum-residency controls that prevent repeated load/unload thrashing.

Resource reservations are acquired before loading and released or reconciled after termination. A model cannot start merely because current observed usage is temporarily low when required reservation capacity is unavailable.

### 3.4 Important-task health-check definition

A task or task stage requires a fresh model health check when one or more of these conditions apply:

- it is high-risk or action-authorizing;
- it can write persistent or protected state;
- it performs architecture, security, migration, promotion, release, or destructive work;
- it depends on exact structured-output or tool-use reliability;
- the model or runtime was loaded, restarted, changed, or recovered since its last valid check;
- the previous check has expired under versioned policy;
- recent failures, resource instability, or configuration drift reduce confidence.

Routine low-risk chat or read-only navigation may reuse a still-valid health record.

## 4. Operating boundaries

- Routing is automatic but visible and operator-overridable.
- Model switching never loses authoritative task state or execution provenance.
- Fallback is predefined, compatible, disclosed, separately recorded, and reverified.
- Resource concurrency and model loading follow executable reservations, ceilings, timeouts, and cancellation policy.
- Cloud support remains optional, disabled by default, and unnecessary for core operation.
- Factory records actionable rationale and evidence rather than private reasoning traces.

## 5. Acceptance criteria

This decision is satisfied only when tests prove that:

1. routing follows declared deterministic rules and exposes the selected model and reason;
2. operator overrides remain within permissions, compatibility, and configured hardware limits;
3. every model execution records a complete deterministic model fingerprint;
4. a task stage cannot silently change model identity or material configuration;
5. fallback closes or checkpoints the failed attempt and starts a new execution record;
6. fallback reruns the verification required for the restarted stage or verified unit;
7. model unloading and switching preserve model-neutral task state;
8. handoff packets contain required current authority and exclude irrelevant raw history;
9. models cannot delegate or call tools outside the Orchestrator and approved gateway;
10. Resource Scheduler reservations prevent overcommit before model loading;
11. CPU concurrency, RAM, VRAM, storage, timeout, thermal, and cancellation policies are deterministically enforced;
12. cooldown and residency controls prevent repeated model load/unload thrashing;
13. important-task health checks are triggered by the declared deterministic conditions;
14. repeated failures trigger bounded retry and quarantine behavior;
15. malformed model output cannot become a tool action or state transition;
16. ordinary chat is not mislabeled as verified evidence, while factual, acceptance, action-authorizing, and completion claims remain gated;
17. cloud services are not required for local Factory operation;
18. roster changes require repeated representative benchmark evidence.