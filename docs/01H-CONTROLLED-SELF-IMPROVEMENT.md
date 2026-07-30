# Approved Controlled Self-Improvement Decision

**Status:** Approved architecture supplement  
**Recorded:** July 23, 2026  
**Clarified:** July 23, 2026

## 1. Governing improvement boundary

Factory may analyze verified evidence and generate Improvement Packet proposals, but it cannot test against approved Factory state, apply changes, alter governing controls or their enforcement implementations, download tools or models, or modify the model roster without required permissions and approvals.

Improvement proposals must be evidence-based, provenance-classified, measurable where possible, reversible, and proportionate to their expected benefit. Safety, correctness, reliability, recoverability, and verification remain higher priorities than convenience, speed, or cosmetic improvement.

A proposed improvement is not a proven improvement. It becomes accepted only after controlled testing, comparison with a verified baseline, regression review, approved application, successful monitoring, and completion of the full packet lifecycle.

Monthly analysis remains the normal proposal path. A verified security, correctness, data-loss, or recovery defect immediately enters the normal defect-remediation process and does not wait for the monthly Improvement Packet cycle.

## 2. Approved Stage 6 decisions

1. **Evidence threshold:** Factory generates proposals from repeated verified patterns or strong verified single-event evidence, not unsupported impressions or random variation. Every source is provenance-classified.
2. **Evidence classification and provenance:** Every proposal identifies evidence strength and whether support came from verified test results, operational telemetry, user reports, model analysis, manual observations, untrusted project content, or another approved source class.
3. **Proposal ranking:** Proposals are ranked by expected benefit, evidence strength, provenance trust, risk, cost, reversibility, hardware impact, and governing-priority alignment.
4. **Priority order:** Safety, correctness, reliability, recoverability, and verification improvements rank above convenience, appearance, and speed.
5. **Duplicate and conflict detection:** Factory detects duplicate, overlapping, superseding, and conflicting proposals before review.
6. **Deterministic proposal merging:** Proposals merge automatically only when their scope, evidence, cause, proposed change, expected outcome, authority, provenance, and affected dependencies are deterministically identical. Otherwise they remain separate and linked.
7. **Bounded monthly output with urgent-defect exception:** Each monthly review presents a limited set of the highest-value actionable proposals. Verified security, correctness, data-loss, or recovery defects bypass monthly waiting and enter defect remediation immediately.
8. **Searchable lower-priority findings:** Findings not promoted into an Improvement Packet remain searchable as observations under their evidence and retention rules.
9. **Experimental isolation:** Every tested improvement runs in an isolated experimental sandbox and cannot modify approved Factory behavior directly.
10. **Verified comparison baseline:** Improvement testing uses an identified verified baseline whenever a comparative benefit is claimed.
11. **Predefined success metrics:** Success metrics, failure thresholds, regression limits, evaluation methods, sample requirements, and applicable observation durations are defined before an experiment begins.
12. **Controlled variables and major-change classification:** One major variable is changed per experiment when practical. Whether a change is `MAJOR` is determined by the approved impact criteria rather than informal judgment.
13. **Dependent change bundles:** Related changes may be tested together when they cannot function independently, provided dependency, bundled scope, shared metrics, state, rollback, and failure domains are explicitly documented.
14. **Higher-priority regression protection:** Every experiment checks that the proposed benefit does not reduce a higher-priority requirement.
15. **Unmeasurable benefit classification:** A proposal is not automatically rejected solely because its benefit cannot yet be measured, but it remains `INCONCLUSIVE` or unverified and cannot be presented as proven.
16. **One major improvement by default:** Factory activates only one `MAJOR` improvement at a time by default.
17. **Independent low-risk grouping:** Multiple `LOW_RISK` improvements may share a controlled packet or activation window only when deterministic dependency analysis proves they are independently testable, traceable, reversible, attributable, and do not share affected components, metrics, state, rollback paths, or failure domains.
18. **Staged activation:** Applied improvements use staged or limited activation when the affected component supports it.
19. **Hardened predefined rollback triggers:** Automatic rollback conditions are measurable, deterministic, approved before activation, and include sample size or duration, debouncing or hysteresis, verified snapshot integrity, and anti-loop behavior when applicable.
20. **Pre-approved automatic rollback:** Factory may automatically restore the last verified approved state when a pre-approved rollback trigger fires. The rollback produces evidence, suspends remaining activations, and does not authorize new behavior.
21. **Stop-after-rollback:** After any improvement rollback, Factory immediately suspends all remaining pending or staged improvement activations until the failure, recovery, and shared-failure-domain impact are reviewed.
22. **Rollback quarantine:** Rolled-back improvements enter quarantine with their evidence, trigger measurements, failure, recovery result, provenance, and investigation status.
23. **Controlled reconsideration:** A failed, stale, quarantined, or rejected proposal may be reconsidered only when new evidence, a materially changed design, a refreshed baseline, or changed operating conditions justify a new version and experiment.
24. **Monitoring period:** Applied improvements remain under monitoring before being classified as accepted.
25. **Risk-based monitoring duration:** Monitoring duration and intensity depend on change type, blast radius, reversibility, risk, required sample size, and failure-detection latency.
26. **Monitoring-period reversibility:** An improvement remains reversible throughout its monitoring period.
27. **Expected-versus-actual comparison:** Measured results are compared with the proposal's original expected benefit, cost, risk, resource estimate, sample requirement, and operating assumptions.
28. **Side-effect recording:** Negative side effects, regressions, tradeoffs, and unexpected resource impacts are recorded even when the primary metric improves.
29. **Reusable lesson promotion:** A verified accepted improvement may become a reusable engineering lesson only after approval, scope review, provenance review, and confirmation that it does not overgeneralize project-specific evidence.
30. **Governing-control and enforcement protection:** Normal Improvement Packets cannot change Factory's governing safety, permission, verification, approval, authority, isolation, evidence, audit, rollback, recovery, or promotion rules or the implementations that enforce them. Such changes require a separate explicit architecture-change process.
31. **Model-roster protection:** Factory cannot modify its model roster automatically. It may propose roster changes supported by evidence, but the user must approve them.
32. **Download protection:** Factory cannot automatically download models, tools, packages, or external components during analysis. Downloads require explicit task-scoped approval and sandbox controls.
33. **Hardware and storage impact:** Every proposal includes estimated CPU, RAM, GPU, VRAM, storage, runtime, and relevant power or thermal impact when applicable.
34. **Complexity justification:** Any improvement that increases permanent architecture, maintenance burden, dependencies, storage, permissions, or operational complexity requires stronger measurable justification.
35. **Evidence preservation after packet deletion or archival:** Deleting or archiving an Improvement Packet does not delete supporting evidence protected by audit, security, recovery, investigation, lesson, or retention rules.

## 3. Proposal qualification

An Improvement Packet proposal must include:

- the observed problem, defect, or opportunity;
- evidence strength and linked supporting records;
- evidence provenance for every material claim;
- whether the pattern is repeated, isolated, incomplete, conflicting, or inconclusive;
- affected components, contracts, permissions, models, tools, storage, workflows, state, metrics, rollback paths, and failure domains;
- the proposed change and bounded scope;
- deterministic impact classification as `MAJOR`, `LOW_RISK`, or another approved class;
- expected measurable benefit and predefined success metrics;
- minimum sample size or observation duration where applicable;
- risks, regressions, side effects, data-loss potential, trust-boundary impact, and permanent-complexity impact;
- estimated hardware, storage, runtime, maintenance, power, and thermal impact;
- experimental design, comparison baseline, controlled variables, and dependency analysis;
- validation, regression, monitoring, rollback, quarantine, and stale-invalidation plans;
- reversibility and staged-activation capability;
- confidence, uncertainty, known limitations, duplicates, conflicts, and provenance trust;
- packet version, governing-requirement version, baseline identity, dependency identities, model-roster version, and affected-component versions.

Unsupported root causes, guessed benefits, model-only claims, untrusted-content claims, or unverified observations must be labeled explicitly and cannot be presented as established facts or independently authorize testing or application.

## 4. Binding self-improvement hardening

### 4.1 Control-plane implementation protection

Normal Improvement Packets cannot modify, replace, disable, bypass, weaken, or reconfigure the governing rules or the code and data paths that enforce them, including:

- approval engine;
- permission enforcement and secret broker;
- sandbox and isolation boundaries;
- verification engine and verdict logic;
- Evidence Traceability Manifest generation and validation;
- evidence store and integrity controls;
- audit writer, chain validation, and retention protection;
- rollback, snapshot, and recovery system;
- Promotion Service and protected-ref gate;
- authoritative state machine and policy loader;
- Watchdog authority and intervention interface.

A change to any protected control-plane component requires a separate architecture-change process containing:

- explicit architecture-change scope and rationale;
- threat, failure, authority, compatibility, and rollback analysis;
- isolated implementation branch and test environment;
- independent verification against the currently approved behavior;
- evidence that the change does not reduce enforcement strength;
- explicit operator approval before testing against approved state or promotion;
- verified recovery protection and a separately approved promotion path.

Renaming, moving, wrapping, replacing dependencies beneath, changing defaults in, or altering schemas consumed by a protected component counts as a control-plane change when enforcement behavior could change.

### 4.2 Packet lifecycle and staleness

Every Improvement Packet uses the following minimum lifecycle:

```text
PROPOSED
-> REVIEWED
-> EXPERIMENT_AUTHORIZED
-> TESTING
-> VERIFIED | FAILED | INCONCLUSIVE
-> APPLY_AUTHORIZED
-> MONITORING
-> ACCEPTED | ROLLED_BACK | QUARANTINED
-> ARCHIVED
```

`STALE` is a fail-closed invalidation state reachable from any nonterminal state when material authority or evidence changes.

A packet becomes `STALE` when any applicable item changes after the packet was evaluated:

- approved comparison baseline;
- affected component or interface;
- supporting evidence or evidence integrity status;
- dependencies, toolchain, runtime, or environment;
- model roster, model fingerprint, or routing policy relevant to the packet;
- governing requirements, acceptance criteria, permissions, or architecture;
- success metrics, expected outputs, rollback path, or recovery snapshot;
- affected state, metrics, trust boundaries, or failure domains.

A stale packet cannot continue testing, application, monitoring, or acceptance. It must be revalidated, superseded by a new version, or archived. Previous evidence and state transitions remain preserved.

Every transition records previous state, new state, cause, actor or authoritative service, monotonic order, wall-clock timestamp, linked evidence, approvals, baseline, and packet version. Invalid transitions fail closed and produce an audit event.

### 4.3 Deterministic impact classifications

Impact classification uses these factors:

- trust-boundary, permission, credential, or external-access changes;
- safety, security, privacy, data-loss, or corruption potential;
- rollback difficulty, migration need, or manual recovery burden;
- number and criticality of affected users, components, repositories, and interfaces;
- persistent architecture, dependency, maintenance, or operational complexity;
- performance, capacity, storage, power, thermal, or hardware impact;
- verification scope, blast radius, and failure-detection latency.

A change is `MAJOR` when any approved threshold indicates material trust-boundary change, meaningful data-loss risk, difficult or stateful rollback, multiple critical components, persistent architectural expansion, material permission exposure, or material resource impact.

A change is `LOW_RISK` only when all of the following are proven:

- no trust-boundary, permission, credential, security-policy, or external-side-effect expansion;
- no protected or persistent data-loss risk;
- one bounded noncritical component or behavior;
- deterministic independent verification;
- simple verified rollback without migration or manual reconstruction;
- no permanent architecture or dependency expansion;
- resource impact remains below versioned low-risk thresholds;
- failure cannot weaken mandatory verification, evidence, audit, recovery, or authority controls.

Two changes are `INDEPENDENT` only when deterministic dependency analysis proves they do not share:

- affected components or interfaces;
- success, safety, or rollback metrics;
- persistent or runtime state;
- rollback paths or recovery snapshots;
- dependencies or migration ordering;
- security boundaries or permissions;
- resource bottlenecks;
- failure domains.

Parallel testing may occur in isolated environments. Parallel activation is permitted only for changes proven independent under these rules.

### 4.4 Urgent verified-defect path

A verified security, correctness, data-loss, corruption, or recovery defect immediately creates a normal defect-remediation task. It does not wait for monthly analysis or compete for the bounded monthly proposal list.

The urgent path does not bypass requirements, permissions, sandboxing, protected control-plane rules, verification, evidence, rollback, approval, or promotion gates. It changes scheduling priority only.

Unverified reports may trigger immediate containment or investigation according to risk, but they are not treated as verified defects until evidence confirms them.

### 4.5 Hardened automatic rollback

Every pre-approved automatic rollback trigger defines:

- exact metric, event, invariant, or failure condition;
- deterministic threshold and comparison method;
- minimum sample size or observation duration when statistical or temporal evidence is required;
- debouncing, cooldown, or hysteresis sufficient to prevent oscillation and rollback loops;
- maximum trigger and rollback attempt count;
- verified active recovery-snapshot identity and integrity status;
- affected components, state, metrics, and failure domains;
- required rollback-event evidence and audit fields;
- post-rollback verification and quarantine behavior.

Before activation, Factory verifies that the active recovery snapshot is restorable and applicable to the affected state. A missing, stale, incompatible, or unverified recovery path blocks activation.

When a rollback trigger fires, Factory:

1. pauses or contains the affected activation;
2. suspends all remaining improvement activations that are pending, staged, or share any affected component or failure domain;
3. records trigger measurements and packet, artifact, environment, snapshot, and policy identities;
4. performs the bounded approved rollback;
5. verifies recovery integrity and authoritative state reconciliation;
6. moves the packet to `ROLLED_BACK` or `QUARANTINED`;
7. blocks further activation until review authorizes resumption.

Repeated rollback triggering, failed rollback, or uncertain recovery opens the circuit breaker, quarantines the affected change and environment, and fails closed.

### 4.6 Evidence provenance classes

Every material proposal claim identifies one or more source classes:

```text
VERIFIED_TEST_RESULT
OPERATIONAL_TELEMETRY
USER_REPORT
MODEL_ANALYSIS
MANUAL_OBSERVATION
UNTRUSTED_PROJECT_CONTENT
OTHER_APPROVED_SOURCE
```

Each source record includes origin, collection method, integrity identity, timestamp, project scope, trust classification, verification status, and linked claim.

- `VERIFIED_TEST_RESULT` may provide direct evidence when the test and traceability chain are valid.
- `OPERATIONAL_TELEMETRY` must identify instrumentation, sampling, coverage, and integrity limits.
- `USER_REPORT` and `MANUAL_OBSERVATION` may justify investigation but require corroboration for consequential claims.
- `MODEL_ANALYSIS` remains a claim until independently verified.
- `UNTRUSTED_PROJECT_CONTENT` is treated as untrusted input and cannot independently authorize a proposal, experiment, application, or root-cause conclusion.

Conflicting or low-trust provenance lowers confidence and must remain visible. Provenance cannot be silently upgraded.

## 5. Controlled lifecycle rules

No packet transition may bypass required evidence, the Stage 5 Evidence Traceability Manifest, verification, recovery snapshot, permission, staleness, or approval gates.

A packet may be removed from the active operator backlog or archived, but protected evidence and audit records remain governed by their own retention rules.

A packet marked `FAILED`, `INCONCLUSIVE`, `ROLLED_BACK`, `QUARANTINED`, or `STALE` cannot enter application without a new justified version and the required review path.

## 6. Application and recovery rules

Before application:

- Factory confirms the packet is not stale;
- Factory creates or selects and verifies the approved active recovery snapshot;
- the exact change, tested artifact, baseline, dependencies, and enforcement boundary are identified;
- success metrics, sample requirements, monitoring duration, and rollback triggers are approved;
- applicable regression, higher-priority, security, recovery, and control-plane checks pass;
- staged activation and monitoring are configured when supported;
- parallel activation is rejected unless independence is deterministically proven.

During monitoring:

- the improvement remains reversible;
- measured outcomes are compared with baseline and packet predictions;
- provenance, sample size, duration, side effects, and resource impacts are recorded;
- packet staleness is re-evaluated after material environment or authority changes;
- a pre-approved trigger may restore the last verified state automatically;
- remaining activations suspend immediately when a rollback trigger fires.

After rollback:

- no additional improvement activation proceeds;
- the failed change and affected environment enter quarantine when required;
- recovery integrity and authoritative state reconciliation are verified;
- trigger evidence and rollback-event evidence are finalized;
- the cause remains `UNKNOWN` or `UNCONFIRMED` until evidence proves it;
- retry requires new evidence, a materially changed design, refreshed baseline, and a new packet version.

## 7. Acceptance criteria

This decision is satisfied only when tests prove that:

1. unsupported impressions and random variation cannot become actionable Improvement Packets without qualifying evidence;
2. every proposal exposes evidence strength, provenance, risk, expected benefit, cost, reversibility, and hardware impact;
3. model analysis, user reports, manual observations, and untrusted project content cannot independently authorize consequential improvement action;
4. safety, correctness, reliability, recoverability, and verification outrank convenience and speed;
5. duplicate or conflicting proposals are detected and non-identical proposals cannot merge silently;
6. monthly review output remains bounded while verified urgent defects enter remediation immediately;
7. urgent scheduling cannot bypass normal requirements, approval, verification, evidence, or promotion controls;
8. experiments cannot modify approved Factory state directly;
9. normal Improvement Packets cannot modify protected governing rules or their enforcement implementations;
10. indirect changes to protected control-plane components trigger the separate architecture-change process;
11. comparative claims cannot be verified without an identified baseline, predefined success metrics, and required sample or duration;
12. packet lifecycle transitions follow only the declared state machine and retain complete transition evidence;
13. invalid packet transitions fail closed and create an audit event;
14. a packet becomes `STALE` when its baseline, component, evidence, dependencies, model roster, environment, recovery path, or governing requirements materially change;
15. stale packets cannot continue testing, application, monitoring, or acceptance without versioned revalidation;
16. bundled changes document why they cannot be tested independently;
17. `MAJOR`, `LOW_RISK`, and `INDEPENDENT` classifications use deterministic impact criteria;
18. improvements cannot be classified as accepted when a higher-priority requirement regresses;
19. unmeasured benefits remain inconclusive rather than proven;
20. one major improvement is activated at a time by default;
21. grouped or parallel low-risk activations proceed only when independence analysis proves no shared components, metrics, state, rollback paths, dependencies, resource bottlenecks, or failure domains;
22. activation uses approved deterministic rollback triggers and staged deployment when supported;
23. rollback triggers enforce approved sample size or duration, hysteresis or debouncing, and maximum attempt limits;
24. activation is blocked when the recovery snapshot or rollback path is missing, stale, incompatible, or unverified;
25. a pre-approved rollback trigger records evidence, suspends remaining activations, and restores only the last verified approved state;
26. repeated triggers or failed rollback open a circuit breaker and quarantine affected work;
27. additional improvements remain suspended after rollback until review is complete;
28. rolled-back improvements retain trigger, failure, provenance, recovery, and investigation evidence;
29. failed, stale, or rejected proposals cannot be reconsidered without new evidence, changed design, refreshed authority, or changed conditions;
30. applied improvements remain reversible throughout their risk-based monitoring period;
31. measured results are compared with original predictions and all negative side effects are retained;
32. reusable lessons require approval, scope review, and provenance review;
33. Factory cannot automatically change the model roster or download models, tools, packages, or external components during analysis;
34. permanent complexity increases require stronger measurable justification;
35. deleting or archiving a packet cannot delete evidence protected by another retention, recovery, security, or audit rule.