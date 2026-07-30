# Approved Verification and Evidence Decision

**Status:** Approved architecture supplement  
**Recorded:** July 23, 2026  
**Clarified:** July 23, 2026

## 1. Governing verification boundary

Factory treats model output, human expectation, and implementation claims as unverified until supported by applicable deterministic tests, inspections, measurements, or recorded manual verification.

Every code-changing task must define acceptance criteria and a verification plan before implementation begins. Verification is risk-based and selected according to changed or affected behavior rather than running every possible test on every task.

Every required acceptance criterion must participate in one deterministic evidence chain:

```text
Requirement
-> acceptance criterion
-> test or check
-> command or procedure
-> environment
-> result
-> evidence file
-> evidence hash
-> tested artifact hash
-> approver or approval record
```

After implementation begins, acceptance criteria, verification procedures, tests, expected outputs, applicability decisions, thresholds, and baselines cannot be weakened or changed without recorded justification, separate approval, versioned supersession, and re-verification of affected work.

Promotion is blocked when a required acceptance criterion lacks valid evidence or has a verdict that is not promotion-eligible. Missing, unavailable, incomplete, unstable, quarantined, or not-testable required verification cannot be converted into an estimated pass.

## 2. Approved Stage 5 decisions

1. **Predefined acceptance criteria:** Every task defines its required acceptance criteria before implementation begins.
2. **Verification planning:** Factory creates an applicable verification plan before executing code-changing work.
3. **Risk-based selection:** Verification methods are selected according to task scope, affected behavior, risk, and governing requirements rather than applying every verification type universally.
4. **Changed and affected behavior:** All changed behavior and reasonably affected behavior must be tested before promotion.
5. **Existing unrelated failures:** A pre-existing failure does not automatically block promotion only when deterministic evidence proves it is unrelated, unchanged, non-safety-critical, outside the affected dependency graph, and fully documented. Any operator exception also requires explicit residual-risk acceptance.
6. **No model-only or approval-only dismissal:** A failing test cannot be ignored because a model calls it unrelated or because an operator prefers to proceed. Deterministic unrelatedness evidence is mandatory; operator approval may accept residual risk only inside the bounded exception policy.
7. **Verification classes:** Factory distinguishes unit, integration, system, regression, security, performance, visual, reproducibility, and manual verification.
8. **Targeted security verification:** Security testing is required when a change affects permissions, inputs, execution, network access, secrets, credentials, trust boundaries, isolation, or another security-sensitive behavior.
9. **Targeted performance verification:** Performance testing is required when performance-sensitive behavior, resource use, latency, throughput, capacity, or hardware limits may have changed.
10. **Visual verification:** Visual projects support screenshot, rendered-output, reference-image, or recorded manual comparison when applicable.
11. **Verified baselines:** Results are compared against an approved verified baseline when one exists.
12. **Baseline and verification change control:** Updating or replacing a verified baseline, test, procedure, expected output, threshold, applicability decision, or acceptance criterion after implementation begins requires separate justification, evidence, approval, and affected-scope re-verification. Verification cannot be changed merely to make a regression pass.
13. **Numerically bounded flaky-test retries:** A suspected flaky test may receive no more than two automatic retries after the initial failure, for three total attempts, under the approved retry conditions and delays.
14. **Unstable classification:** A test that passes only after retry is not a clean pass. Factory records it as `UNSTABLE`, preserves every attempt, and does not use the retry-dependent pass as sole required promotion evidence.
15. **Flaky-test quarantine:** Tests crossing the deterministic instability threshold enter quarantine, receive an owner and investigation deadline, and cannot provide required promotion evidence until reinstated through repeated clean passes.
16. **Reproducibility evidence:** Verification records retain commands, tool and dependency versions, configuration, environment identity, inputs, outputs, errors, exit codes, timestamps, and applicable resource data.
17. **Artifact integrity:** Promoted artifacts receive integrity hashes or an equivalent deterministic identity so Factory can prove which exact artifact was tested and approved.
18. **Evidence integrity:** Finalized evidence packages receive integrity protection sufficient to detect alteration, corruption, or substitution.
19. **Proportionate hashing:** Factory does not require a separate cryptographic hash for every minor log entry. Integrity protection applies to finalized evidence packages, promoted artifacts, critical records, snapshots, and other approved integrity boundaries.
20. **Build-environment verification:** Initial verification normally occurs in the same isolated environment used to build the artifact, followed by a clean recreated-environment check when required by task risk, reproducibility needs, or release policy.
21. **Release reproducibility:** Release candidates must be verified in a clean recreated environment before release approval.
22. **No mandatory model consensus:** A separate model is not required to review every task. Deterministic evidence remains authoritative.
23. **Optional adversarial review:** Another model may provide critique, review, or adversarial analysis, but its findings remain claims until verified through an approved method.
24. **Final verdict:** Every criterion and finalized verification package uses only `PASS`, `FAIL`, `BLOCKED`, `INCONCLUSIVE`, or `NOT_TESTABLE`, with the exact promotion semantics defined below.
25. **Honest incompleteness:** Missing, unavailable, incomplete, unstable, or quarantined verification is represented explicitly and cannot be estimated, inferred, or presented as proven.
26. **Requirement coverage manifest:** Evidence identifies which requirements and acceptance criteria were tested, the exact verification chain for each, which passed or failed, and which remain blocked, inconclusive, or not testable.
27. **Evidence-complete promotion:** Promotion is blocked when any required acceptance criterion lacks a complete valid traceability chain and promotion-eligible verdict.
28. **Recorded manual verification:** Manual verification is allowed when automation is impractical, provided the procedure, operator, environment, expected result, actual result, supporting artifacts, integrity identities, and verdict are recorded.
29. **Unchanged-boundary evidence:** When scope, permission, safety, or regression claims depend on files or behavior remaining unchanged, Factory preserves evidence proving the material boundary remained unchanged.
30. **Artifact-change invalidation:** Verification is invalidated when the tested artifact changes afterward. The changed artifact must be verified again before promotion.

## 3. Binding verification hardening

### 3.1 Mandatory Evidence Traceability Manifest

Every verification package contains a machine-readable Evidence Traceability Manifest. Each required acceptance criterion has one or more records linking:

- Project, requirement, task, and acceptance-criterion identifiers;
- verification-plan and check identifiers;
- exact automated command or normalized manual procedure;
- tool, dependency, test, fixture, and expected-output versions;
- environment identity, configuration, sandbox, source commit, and relevant hardware profile;
- start time, completion time, exit status, measured result, and criterion verdict;
- evidence-file path or stable evidence identifier;
- evidence content hash and finalized evidence-package hash;
- exact tested artifact identity and artifact hash;
- baseline identity and comparison when applicable;
- approver identity and approval-record identifier, or an explicit `APPROVAL_NOT_REQUIRED_BY_POLICY` value;
- supersession, retry, instability, exclusion, and residual-risk references when applicable.

The manifest uses stable deterministic identifiers and direct references rather than a general narrative summary. Broken, missing, ambiguous, or hash-mismatched links make the affected criterion incomplete and block promotion.

A package-level `PASS` may be issued only when the manifest proves complete promotion-eligible coverage for every required criterion.

### 3.2 Verification anti-weakening control

Implementation is considered started when the task enters `RUNNING`, performs its first material code or configuration change, or executes an implementation command, whichever occurs first.

After that point, changing any of the following requires a versioned verification-change record, recorded justification, impact analysis, and separate approval:

- requirements or acceptance criteria;
- verification-plan scope or applicability;
- test code, fixtures, inputs, or test data;
- expected outputs, tolerances, thresholds, or success metrics;
- commands, procedures, tools, or environments;
- verified baselines or comparison rules;
- required versus non-required classification.

The previous version remains preserved. The change record must explain why the original verification was incorrect or insufficient, identify coverage gained or lost, and require re-verification of all affected work. A change whose primary purpose is to convert a failure into a pass without proving the original verification invalid is rejected and recorded as an anti-gaming or security event.

### 3.3 Exact verdict and promotion semantics

| Verdict | Enforceable meaning | Promotion effect |
|---|---|---|
| `PASS` | The criterion or package has complete valid evidence and met its approved expected result. | Allowed only after all other policy checks and required approvals pass. |
| `FAIL` | The approved check executed or was inspected and the required expected result was not met. | Blocked. |
| `BLOCKED` | A required dependency, permission, prerequisite, environment, resource, or external condition prevented completion. | Blocked until the blocker is resolved and verification completes. |
| `INCONCLUSIVE` | Evidence exists but is insufficient, conflicting, unstable, or unable to determine the required result. | Blocked for required criteria. Non-required inconclusive checks must be documented and excluded before the package can be recomputed as `PASS`. |
| `NOT_TESTABLE` | The check cannot be performed under the declared constraints or available methods. | Blocked for required criteria. Permitted only for explicitly documented non-required checks; the package must still satisfy every required criterion and receive `PASS`. |

A finalized package cannot promote while its package-level verdict is `FAIL`, `BLOCKED`, `INCONCLUSIVE`, or `NOT_TESTABLE`. Non-required checks may retain those criterion-level verdicts only when their non-required status was approved before implementation or through the verification-change process.

### 3.4 Unrelated-failure exception policy

A failure is unrelated only when deterministic evidence proves all of the following:

- it existed on the approved baseline before the current change;
- the current task did not create, worsen, mask, or change its detection;
- dependency and impact analysis place it outside the affected dependency graph;
- no changed interface, shared state, resource, security boundary, or promotion artifact depends on it;
- it is non-safety-critical, non-security-critical, non-data-integrity-critical, and non-promotion-critical;
- the exclusion and evidence appear in the Evidence Traceability Manifest.

An operator may approve an exception only after those facts are proven, the failure is fully documented, and the operator records an explicit residual-risk acceptance with scope, expiration or review condition, and rollback implications. Operator approval cannot replace deterministic evidence, relabel the failure as `PASS`, or exempt a safety-critical failure.

### 3.5 Numeric flaky-test policy

The initial approved flaky-test policy is:

- Maximum automatic retries: **2** after the initial failure, for **3 total attempts**.
- Retry delays: **5 seconds** before retry 1 and **30 seconds** before retry 2.
- Retries are allowed only when the artifact, source state, test, fixture, command, configuration, and environment remain unchanged and the failure is plausibly transient or nondeterministic.
- Test edits, environment replacement, artifact rebuilding, or baseline changes start a new verification record rather than a retry.
- Every failed and successful attempt, output, timing, exit status, and environment record is preserved.
- A pass after any retry is `UNSTABLE`, not a clean `PASS`, and cannot alone satisfy a required promotion criterion.
- A consistently failing test is `FAIL`, not automatically labeled flaky.

A test enters `QUARANTINED` when either condition occurs:

1. it produces a failure followed by a retry-dependent pass in **2 separate verification sessions within 7 calendar days**; or
2. it produces **3 retry-dependent passes within 30 calendar days**.

A quarantined test:

- cannot provide required promotion evidence;
- must have an assigned investigation owner within **1 business day**;
- must have a target investigation deadline within **7 calendar days** or before the next affected release or promotion, whichever occurs first;
- remains visible with every failed attempt and affected requirement;
- may be replaced only by an independently approved equivalent or stronger check.

Reinstatement requires a documented root cause and corrective action plus **5 consecutive first-attempt clean passes** across at least **2 clean recreated verification sessions**, with no retries and no contradictory result.

Changing these numeric limits requires the verification-change process and cannot occur solely to permit promotion.

## 4. Verification selection rules

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

## 5. Existing-failure handling

A pre-existing failure may be excluded from blocking the current promotion only through the unrelated-failure exception policy. The failure remains visible, retains its actual verdict, and cannot be converted into a passing result.

If deterministic unrelatedness and bounded residual-risk acceptance cannot both be established where approval is required, the failure blocks promotion or the task remains `BLOCKED` or `INCONCLUSIVE`.

## 6. Evidence package minimum

A finalized verification package includes at least:

- task, project, workstream, requirement, environment, artifact, and evidence identifiers;
- acceptance criteria and verification-plan versions;
- the complete Evidence Traceability Manifest;
- selected verification methods and applicability rationale;
- commands, procedures, configurations, versions, inputs, outputs, errors, exit codes, and timestamps;
- baseline identity and comparison result when applicable;
- retry history, instability status, quarantine status, owner, and deadline when applicable;
- requirement-by-requirement coverage;
- artifact and evidence integrity identities;
- verification-change records and superseded versions;
- unrelated-failure evidence and residual-risk approvals;
- unresolved failures, limitations, exclusions, and uncertainty;
- criterion verdicts, package verdict, and promotion eligibility.

## 7. Acceptance criteria

This decision is satisfied only when tests prove that:

1. code-changing tasks cannot begin without defined acceptance criteria and a verification plan;
2. every required criterion has a deterministic Evidence Traceability Manifest chain;
3. broken, ambiguous, missing, or hash-mismatched evidence links block promotion;
4. changed and affected behavior cannot be promoted without applicable tests or approved recorded manual checks;
5. implementation-start detection activates verification anti-weakening controls;
6. acceptance criteria, tests, procedures, expected outputs, thresholds, applicability, or baselines cannot change after implementation begins without justification, separate approval, versioning, and re-verification;
7. verification cannot be weakened merely to convert a failure into a pass;
8. unrelated existing failures cannot be excluded without deterministic evidence and bounded residual-risk acceptance;
9. operator approval cannot replace unrelatedness evidence or exempt safety-critical failures;
10. model review cannot substitute for deterministic verification;
11. security, performance, visual, and clean-environment checks are selected when their risk conditions apply;
12. verified baselines cannot be changed without separate justification and approval;
13. automatic flaky-test retries stop after two retries and preserve all three attempts;
14. retry conditions and 5-second and 30-second delays are enforced;
15. retry-dependent passes become `UNSTABLE` and cannot independently satisfy required promotion evidence;
16. deterministic quarantine thresholds assign an owner and deadline;
17. quarantined tests cannot provide required promotion evidence;
18. reinstatement requires five consecutive first-attempt clean passes across at least two clean sessions;
19. verification evidence retains commands, versions, configuration, environment, outputs, errors, exit codes, and timestamps;
20. promoted artifacts and finalized evidence packages have verifiable integrity identities;
21. minor log entries are not burdened with unnecessary individual hashing;
22. release candidates are verified in a clean recreated environment;
23. verdicts use only the approved classes and enforce their declared promotion semantics;
24. required `FAIL`, `BLOCKED`, `INCONCLUSIVE`, or `NOT_TESTABLE` criteria block promotion;
25. non-required inconclusive or not-testable checks cannot silently become required coverage passes;
26. missing verification cannot be represented as a pass;
27. manual verification retains its procedure, operator, environment, result, artifacts, hashes, and approval record;
28. material unchanged boundaries can be proven when required;
29. changing a tested artifact invalidates prior verification and blocks promotion until re-verification;
30. package-level `PASS` cannot be issued until every required criterion has complete promotion-eligible evidence.