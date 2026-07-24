# Approved Controlled Self-Improvement Decision

**Status:** Approved architecture supplement  
**Recorded:** July 23, 2026

## 1. Governing improvement boundary

Factory may analyze verified evidence and generate Improvement Packet proposals, but it cannot test against approved Factory state, apply changes, alter governing controls, download tools or models, or modify the model roster without the required permissions and approvals.

Improvement proposals must be evidence-based, measurable where possible, reversible, and proportionate to their expected benefit. Safety, correctness, reliability, recoverability, and verification remain higher priorities than convenience, speed, or cosmetic improvement.

A proposed improvement is not a proven improvement. It becomes verified only after controlled testing, comparison with a verified baseline, regression review, approved application, and successful monitoring.

## 2. Approved Stage 6 decisions

1. **Evidence threshold:** Factory generates proposals from repeated verified patterns or strong verified single-event evidence, not from unsupported impressions or random variation.
2. **Evidence classification:** Every proposal identifies whether its support is repeated, isolated, incomplete, conflicting, or inconclusive.
3. **Proposal ranking:** Proposals are ranked by expected benefit, evidence strength, risk, cost, reversibility, hardware impact, and governing-priority alignment.
4. **Priority order:** Safety, correctness, reliability, recoverability, and verification improvements rank above convenience, appearance, and speed.
5. **Duplicate and conflict detection:** Factory detects duplicate, overlapping, superseding, and conflicting proposals before review.
6. **Deterministic proposal merging:** Proposals merge automatically only when their scope, evidence, cause, proposed change, expected outcome, and authority are deterministically identical. Otherwise they remain separate and linked.
7. **Bounded monthly output:** Each monthly review presents a limited set of the highest-value actionable proposals instead of creating an unbounded operator backlog.
8. **Searchable lower-priority findings:** Findings not promoted into an Improvement Packet remain searchable as observations under their evidence and retention rules.
9. **Experimental isolation:** Every tested improvement runs in an isolated experimental sandbox and cannot modify approved Factory behavior directly.
10. **Verified comparison baseline:** Improvement testing uses an identified verified baseline whenever a comparative benefit is claimed.
11. **Predefined success metrics:** Success metrics, failure thresholds, regression limits, and evaluation methods are defined before an experiment begins.
12. **Controlled variables:** One major variable is changed per experiment when practical so cause and effect remain attributable.
13. **Dependent change bundles:** Related changes may be tested together when they cannot function independently, provided the dependency and bundled scope are explicitly documented.
14. **Higher-priority regression protection:** Every experiment checks that the proposed benefit does not reduce a higher-priority requirement.
15. **Unmeasurable benefit classification:** A proposal is not automatically rejected solely because its benefit cannot yet be measured, but it remains `INCONCLUSIVE` or `UNVERIFIED` and cannot be presented as proven.
16. **One major improvement by default:** Factory applies only one major improvement at a time by default.
17. **Independent low-risk grouping:** Multiple low-risk improvements may share one controlled packet only when each is independently testable, traceable, reversible, and attributable.
18. **Staged activation:** Applied improvements use staged or limited activation when the affected component supports it.
19. **Predefined rollback triggers:** Automatic rollback conditions and thresholds are defined and approved before activation.
20. **Pre-approved automatic rollback:** Factory may automatically restore the last verified approved state when a pre-approved rollback trigger fires. This restoration does not authorize any new behavior.
21. **Stop-after-rollback:** After an improvement causes rollback, Factory stops applying additional improvements until the failure is reviewed and resolved.
22. **Rollback quarantine:** Rolled-back improvements enter quarantine with their evidence, failure, recovery result, and investigation status.
23. **Controlled reconsideration:** A failed or rejected proposal may be reconsidered only when new evidence, a materially changed design, or changed operating conditions justify a new experiment.
24. **Monitoring period:** Applied improvements remain under monitoring before being classified as successful.
25. **Risk-based monitoring duration:** Monitoring duration and intensity depend on the change type, blast radius, reversibility, and risk.
26. **Monitoring-period reversibility:** An improvement remains reversible throughout its monitoring period.
27. **Expected-versus-actual comparison:** Measured results are compared with the proposal's original expected benefit, cost, risk, and resource estimate.
28. **Side-effect recording:** Negative side effects, regressions, tradeoffs, and unexpected resource impacts are recorded even when the primary metric improves.
29. **Reusable lesson promotion:** A verified successful improvement may become a reusable engineering lesson only after approval, scope review, and confirmation that it does not overgeneralize project-specific evidence.
30. **Governing-control protection:** Normal Improvement Packets cannot change Factory's governing safety, permission, verification, approval, authority, isolation, or audit rules. Such changes require a separate explicit architecture decision.
31. **Model-roster protection:** Factory cannot modify its model roster automatically. It may propose roster changes supported by evidence, but the user must approve them.
32. **Download protection:** Factory cannot automatically download models, tools, packages, or external components during analysis. Downloads require explicit task-scoped approval and sandbox controls.
33. **Hardware and storage impact:** Every proposal includes estimated CPU, RAM, GPU, VRAM, storage, runtime, and relevant power or thermal impact when applicable.
34. **Complexity justification:** Any improvement that increases permanent architecture, maintenance burden, dependencies, storage, permissions, or operational complexity requires stronger measurable justification.
35. **Evidence preservation after deletion:** Deleting an Improvement Packet proposal does not delete supporting evidence that remains protected by audit, security, recovery, investigation, lesson, or retention rules.

## 3. Proposal qualification

An Improvement Packet proposal must include:

- the observed problem or opportunity;
- evidence classification and linked supporting records;
- whether the pattern is repeated, isolated, incomplete, conflicting, or inconclusive;
- affected components, contracts, permissions, models, tools, storage, and workflows;
- the proposed change and its bounded scope;
- expected measurable benefit and predefined success metrics;
- risks, regressions, side effects, and permanent-complexity impact;
- estimated hardware, storage, runtime, and maintenance impact;
- experimental design, comparison baseline, and controlled variables;
- validation, regression, monitoring, rollback, and quarantine plans;
- reversibility and staged-activation capability;
- confidence, uncertainty, known limitations, duplicates, and conflicts.

Unsupported root causes, guessed benefits, or unverified claims must be labeled explicitly and cannot be presented as established facts.

## 4. Controlled lifecycle

Improvement Packets follow this lifecycle:

```text
OBSERVED
-> PROPOSED
-> REVIEWED
-> APPROVED_FOR_TEST
-> EXPERIMENTAL
-> VERIFIED | FAILED | INCONCLUSIVE
-> APPROVED_FOR_APPLICATION
-> STAGED
-> MONITORING
-> SUCCESSFUL | ROLLED_BACK | QUARANTINED
-> ARCHIVED
```

No state transition may bypass the required evidence, verification, recovery snapshot, permission, or approval gate.

A proposal may be deleted from the operator backlog, but protected evidence and audit records remain governed by their own retention rules.

## 5. Application and recovery rules

Before application:

- Factory creates and verifies the approved rolling recovery snapshot;
- the exact change and tested artifact are identified;
- success metrics and rollback triggers are approved;
- applicable regression checks pass;
- staged activation and monitoring are configured when supported.

During monitoring:

- the improvement remains reversible;
- measured outcomes are compared with the baseline and proposal predictions;
- side effects and resource impacts are recorded;
- a pre-approved trigger may restore the last verified state automatically.

After rollback:

- no additional improvement is applied;
- the failed change is quarantined;
- recovery integrity is verified;
- the cause remains `UNKNOWN` or `UNCONFIRMED` until evidence proves it;
- retry requires new evidence or a materially changed design.

## 6. Acceptance criteria

This decision is satisfied only when tests prove that:

1. unsupported impressions and random variation cannot become actionable Improvement Packets without qualifying evidence;
2. every proposal exposes its evidence strength, risk, expected benefit, cost, reversibility, and hardware impact;
3. safety, correctness, reliability, recoverability, and verification outrank convenience and speed;
4. duplicate or conflicting proposals are detected and non-identical proposals cannot merge silently;
5. monthly review output remains bounded while lower-priority findings remain searchable;
6. experiments cannot modify approved Factory state directly;
7. comparative claims cannot be verified without an identified baseline and predefined success metrics;
8. bundled changes explicitly document why they cannot be tested independently;
9. improvements cannot be classified as successful when a higher-priority requirement regresses;
10. unmeasured benefits remain inconclusive or unverified rather than proven;
11. one major improvement is applied at a time by default;
12. grouped low-risk changes remain independently testable, traceable, reversible, and attributable;
13. activation uses approved rollback triggers and staged deployment when supported;
14. a pre-approved rollback trigger can restore the last verified state without authorizing new behavior;
15. additional improvements stop after rollback until review is complete;
16. rolled-back improvements enter quarantine and cannot immediately retry;
17. failed proposals cannot be reconsidered without new evidence, changed design, or changed conditions;
18. applied improvements remain reversible throughout their risk-based monitoring period;
19. measured results are compared with original predictions and all negative side effects are retained;
20. reusable lessons require approval and scope review;
21. normal Improvement Packets cannot modify governing controls or automatically change the model roster;
22. analysis cannot automatically download models, tools, packages, or external components;
23. permanent complexity increases require stronger measurable justification;
24. deleting a proposal cannot delete evidence protected by another retention or audit rule.