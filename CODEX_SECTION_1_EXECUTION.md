# Codex Execution Handoff — Factory Section 1

## Objective

Implement the approved Factory Section 1 requirements-and-contracts system from the existing specification and implementation plan. Execute all five tasks continuously with isolated worker and reviewer contexts. Do not redesign approved behavior.

## Authoritative sources

Read these first:

1. `PROJECT_DEFINITION.md`
2. `docs/01-APPROVED-DECISIONS.md`
3. `docs/02-FACTORY-ARCHITECTURE.md`
4. `docs/specifications/2026-07-23-section-1-requirements-contracts-design.md`
5. `docs/superpowers/plans/2026-07-23-section-1-requirements-contracts.md`

The implementation plan is the task-by-task execution source. The specification and approved decisions govern any interpretation.

## Required workflow

Use these skills in this order:

1. `superpowers:using-git-worktrees`
2. `superpowers:subagent-driven-development`
3. Each implementer uses `superpowers:test-driven-development`
4. Final review uses `superpowers:requesting-code-review`
5. Completion uses `superpowers:finishing-a-development-branch`

## Branch and isolation

- Base commit: `5e0cbf42dcfa53664f0558979db9fe2c4709bb83`
- Development branch: `agent/section-1-implementation`
- Never implement directly on `main`.
- Use an isolated worktree.
- Keep task ownership within the exact files named by the plan.
- Do not run multiple implementation workers concurrently.

## Execution rules

For each of the five plan tasks:

1. Extract only that task into a task brief.
2. Dispatch a fresh implementer with explicit model selection.
3. Implement tests first.
4. Run the exact task tests and required static checks.
5. Commit an automatic checkpoint containing only the task-owned files.
6. Generate a complete diff/review package from the recorded task base commit.
7. Dispatch a fresh task reviewer.
8. Require both:
   - specification compliance approval;
   - code-quality approval.
9. Fix every Critical or Important finding and re-review.
10. Record completion in `.superpowers/sdd/progress.md`.
11. Continue automatically to the next task.

After all tasks:

1. Run the complete Section 1 test suite.
2. Run the Windows-path, malicious-YAML, stale-cache, rollback, authority-expansion, deletion, and failure-path tests required by the plan.
3. Run the final whole-branch review using the merge-base-to-head review package.
4. Fix and re-review all blocking findings.
5. Open a draft pull request to `main` with exact evidence.
6. Do not merge the pull request.

## Autonomy policy

Proceed automatically when the work is proven to be:

- inside task-owned paths;
- bounded and reversible;
- non-destructive;
- compatible with dependent components;
- covered by required tests and rollback evidence;
- unchanged in approved architecture, security, privacy, and product intent.

Do not interrupt the user for routine implementation decisions, test failures, safe fixes, checkpoint commits, cache rebuilds, or recovery from verified checkpoints.

Stop and request a human decision only when genuinely blocked or when a proposed action would:

- delete or replace protected or pre-existing material;
- change approved architecture, security, privacy, permissions, or cloud policy;
- expand authority or weaken required evidence;
- introduce an unresolved breaking shared-interface change;
- install persistent host software;
- transfer private project material without existing permission;
- merge into `main`;
- publish, release, or spend money.

Security violations are denied and audited, not offered as normal approval choices.

## Completion standard

Do not claim Section 1 complete unless every acceptance criterion in the approved specification is mapped to retained evidence and all applicable deterministic tests pass.

The final report must include:

- exact commits per task;
- exact changed-file list;
- exact commands executed;
- unit, integration, security, failure-path, and regression results;
- static-analysis results;
- reviewer verdicts;
- unresolved limitations, accurately classified;
- rollback points;
- draft PR number and head SHA.

## Start command

Execute the full plan now using subagent-driven development. Continue through all five tasks without asking whether to proceed. Stop only for a genuine blocker or protected human decision.