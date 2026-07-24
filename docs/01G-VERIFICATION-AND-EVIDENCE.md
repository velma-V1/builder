# Approved Verification and Evidence Decision

**Status:** Approved architecture supplement  
**Recorded:** July 23, 2026

## 1. Governing verification boundary

Factory treats model output, human expectation, and implementation claims as unverified until supported by the applicable deterministic tests, inspections, measurements, or recorded manual verification.

Every code-changing task must define acceptance criteria and a verification plan before implementation begins. Verification is risk-based and selected according to the changed or affected behavior rather than running every possible test on every task.

Promotion is blocked when a required acceptance criterion lacks valid evidence. Missing, unavailable, or incomplete verification must be reported honestly and cannot be converted into an estimated pass.

## 2. Approved Stage 5 decisions

1. **Predefined acceptance criteria:** Every task defines its required acceptance criteria before implementation begins.
2. **Verification planning:** Factory creates an applicable verification plan before executing code-changing work.
3. **Risk-based selection:** Verification methods are selected according to task scope, affected behavior, risk, and governing requirements rather than applying every verification type universally.
4. **Changed and affected behavior:** All changed behavior and reasonably affected behavior must be tested before promotion.
5. **Existing unrelated failures:** A pre-existing failure does not automatically block promotion when deterministic evidence proves it is unrelated, unchanged, non-safety-critical, and outside the affected scope. It must still be documented.
6. **No model-only dismissal:** A failing test cannot be ignored merely because a model claims it is unrelated. Unrelated status requires deterministic evidence or explicit operator approval.
7. **Verification classes:** Factory distinguishes unit, integration, system, regression, security, performance, visual, reproducibility, and manual verification.
8. **Targeted security verification:** Security testing is required when a change affects permissions, inputs, execution, network access, secrets, credentials, trust boundaries, isolation, or another security-sensitive behavior.
9. **Targeted performance verification:** Performance testing is required when performance-sensitive behavior, resource use, latency, throughput, capacity, or hardware limits may have changed.
10. **Visual verification:** Visual projects support screenshot, rendered-output, reference-image, or recorded manual comparison when applicable.
11. **Verified baselines:** Results are compared against an approved verified baseline when one exists.
12. **Baseline change control:** Updating or replacing a verified baseline requires separate justification, evidence, and approval. A baseline cannot be changed merely to make a regression pass.
13. **Bounded flaky-test retries:** Suspected flaky tests may be retried automatically only within a documented bounded retry policy.
14. **Unstable classification:** A test that passes only after retry is not classified as a clean pass. Factory records it as unstable and retains the original failure and retry evidence.
15. **Flaky-test quarantine:** Repeatedly flaky tests are quarantined for investigation and cannot silently become accepted normal behavior.
16. **Reproducibility evidence:** Verification records retain commands, tool and dependency versions, configuration, environment identity, inputs, outputs, errors, exit codes, timestamps, and applicable resource data.
17. **Artifact integrity:** Promoted artifacts receive integrity hashes or an equivalent deterministic identity so Factory can prove which exact artifact was tested and approved.
18. **Evidence integrity:** Finalized evidence packages receive integrity protection sufficient to detect alteration, corruption, or substitution.
19. **Proportionate hashing:** Factory does not require a separate cryptographic hash for every minor log entry. Integrity protection applies to finalized evidence packages, promoted artifacts, critical records, snapshots, and other approved integrity boundaries.
20. **Build-environment verification:** Initial verification normally occurs in the same isolated environment used to build the artifact, followed by a clean recreated-environment check when required by task risk, reproducibility needs, or release policy.
21. **Release reproducibility:** Release candidates must be verified in a clean recreated environment before release approval.
22. **No mandatory model consensus:** A separate model is not required to review every task. Deterministic evidence remains authoritative.
23. **Optional adversarial review:** Another model may provide critique, review, or adversarial analysis, but its findings remain claims until verified through an approved method.
24. **Final verdict:** Every verification package ends with an explicit `PASS`, `FAIL`, `BLOCKED`, `INCONCLUSIVE`, or `NOT_TESTABLE` verdict.
25. **Honest incompleteness:** Missing, unavailable, or incomplete verification is represented explicitly and cannot be estimated, inferred, or presented as proven.
26. **Requirement coverage:** Evidence identifies which requirements and acceptance criteria were tested, which passed or failed, and which were not tested.
27. **Evidence-complete promotion:** Promotion is blocked when any required acceptance criterion lacks valid evidence.
28. **Recorded manual verification:** Manual verification is allowed when automation is impractical, provided the procedure, operator, expected result, actual result, supporting artifacts, and verdict are recorded.
29. **Unchanged-boundary evidence:** When scope, permission, safety, or regression claims depend on files or behavior remaining unchanged, Factory preserves evidence proving the material boundary remained unchanged.
30. **Artifact-change invalidation:** Verification is invalidated when the tested artifact changes afterward. The changed artifact must be verified again before promotion.

## 3. Verification selection rules

Factory selects the minimum complete verification set needed to prove the task without weakening required coverage.

Applicable checks may include:

- unit tests for changed isolated behavior;
- integration tests for component interactions and contracts;
- system tests for end-to-end behavior;
- regression tests for previously verified behavior at risk;
- security checks for affected trust boundaries;
- performance checks for affected resource or latency behavior;
- visual comparison for rendered or user-interface outputs;
- clean-environment reproduction for releases or dependency-sensitive work;
- recorded manual verification for behavior that cannot be proven automatically.

The verification plan must state why each selected check is required and why any normally expected check is not applicable.

## 4. Existing-failure handling

A pre-existing failure may be classified as unrelated only when evidence shows that:

- it existed before the current task;
- the current task did not worsen it;
- the changed or affected scope does not depend on it;
- it is not safety-critical or promotion-critical;
- its exclusion is recorded in the final evidence package.

If those conditions cannot be proven, the failure blocks promotion or the task remains `BLOCKED` or `INCONCLUSIVE`.

## 5. Evidence package minimum

A finalized verification package includes at least:

- task, project, workstream, requirement, environment, artifact, and evidence identifiers;
- acceptance criteria and verification plan;
- selected verification methods and applicability rationale;
- commands, configurations, versions, inputs, outputs, errors, exit codes, and timestamps;
- baseline identity and comparison result when applicable;
- retry history and instability classification when applicable;
- requirement-by-requirement coverage;
- artifact and evidence integrity identities;
- unresolved failures, limitations, exclusions, and uncertainty;
- final verdict and promotion eligibility.

## 6. Acceptance criteria

This decision is satisfied only when tests prove that:

1. code-changing tasks cannot begin without defined acceptance criteria and a verification plan;
2. changed and affected behavior cannot be promoted without applicable tests;
3. unrelated existing failures cannot be excluded without deterministic evidence or explicit operator approval;
4. model review cannot substitute for deterministic verification;
5. security, performance, visual, and clean-environment checks are selected when their risk conditions apply;
6. verified baselines cannot be changed without separate justification and approval;
7. flaky-test retries are bounded and retry-dependent passes are classified as unstable;
8. repeatedly flaky tests enter quarantine rather than being silently accepted;
9. verification evidence retains commands, versions, configuration, environment, outputs, errors, exit codes, and timestamps;
10. promoted artifacts and finalized evidence packages have verifiable integrity identities;
11. minor log entries are not burdened with unnecessary individual hashing;
12. release candidates are verified in a clean recreated environment;
13. final verdicts use only the approved verdict classes;
14. missing verification cannot be represented as a pass;
15. evidence maps results to every required acceptance criterion;
16. manual verification retains its procedure, operator result, and supporting artifacts;
17. material unchanged boundaries can be proven when required;
18. changing a tested artifact invalidates prior verification and blocks promotion until re-verification.