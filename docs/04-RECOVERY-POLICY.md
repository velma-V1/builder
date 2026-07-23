# Factory Recovery Policy

**Status:** Approved operating policy  
**Recorded:** July 22, 2026

## 1. Core rule

The Factory must review a failed or drifting task, return to the last verified safe point, correct the task, and start again when recovery is possible.

Failure, failed tests, model disagreement, or scope drift are not automatic reasons to abandon a project.

## 2. Verified safe checkpoint

A checkpoint is safe only when all applicable conditions are recorded:

- repository base commit is known;
- worktree and branch state are valid;
- owned paths match the task contract;
- required tests passed at that point;
- dependency and configuration state is reproducible;
- no known security or permission violation exists;
- checkpoint evidence has not been altered;
- rollback to the checkpoint has been tested or deterministically validated.

A model statement alone cannot make a checkpoint safe.

## 3. Scope-drift procedure

When a lane exceeds its task contract:

1. freeze the lane and prevent additional writes;
2. preserve the complete diff, log, commands, model calls, test results, and sandbox metadata;
3. identify the first change that violated scope, ownership, architecture, or permission limits;
4. classify the cause as contract ambiguity, model error, dependency effect, integration conflict, malicious instruction, or unknown;
5. restore the last verified safe checkpoint;
6. narrow or correct the task contract;
7. recreate the disposable sandbox if its state may be contaminated;
8. restart the task with fresh model context;
9. rerun all tests required from the restored checkpoint forward;
10. escalate only when the contract remains ambiguous, recovery is unsafe, or bounded retries are exhausted.

## 4. Failed-test procedure

When a test fails:

1. preserve the exact command, environment, output, and affected commit;
2. determine whether the failure is new, pre-existing, flaky, environmental, or caused by the task;
3. return to the most recent safe point if continuing would make diagnosis unreliable;
4. create a bounded repair task;
5. repair without weakening protected tests;
6. rerun the failed test;
7. rerun applicable regression and failure-path tests;
8. record what failed, what changed, and what now passes.

Existing tests may not be silently changed merely to obtain a passing result.

## 5. Repeated-failure procedure

Repeated failures must not create an infinite loop.

The exact retry count is set in the task contract. When the limit is reached, the watchdog must:

- preserve all attempts and evidence;
- compare failure causes;
- verify that retries are not repeating the same ineffective repair;
- use the stronger approved model or local supervisor when allowed;
- reformulate the task contract once when evidence supports doing so;
- escalate when no materially different safe repair remains.

## 6. Provider or model failure

When a model is unavailable, exhausted, or unsuitable:

1. preserve the provider error and usage state;
2. attempt the paired approved model when suitable;
3. attempt the approved local fallback path;
4. pause only the affected task when no approved path remains;
5. never insert an unapproved replacement model.

## 7. Sandbox failure

If the sandbox boundary, mount policy, network policy, secret handling, or process isolation may have failed:

- stop the lane immediately;
- preserve external evidence without trusting sandbox state;
- destroy the disposable environment;
- inspect host-visible effects;
- restore from the last checkpoint proven safe before the boundary failure;
- require security clearance before restarting.

## 8. Repository corruption or conflict

The Factory must not repair repository corruption by guessing.

It must preserve refs, commits, worktree state, reflog-equivalent evidence when available, and uncommitted diffs before recovery. Shared integration conflicts are handled by the serialized integration coordinator, not independently by competing lanes.

## 9. Recovery result states

Every recovery ends in one of these outcomes:

- `RECOVERED` — restored, corrected, retested, and safe to continue;
- `DEGRADED` — safe continuation exists with reduced lane or provider capacity;
- `BLOCKED` — verified external condition prevents progress;
- `ESCALATED` — a required user decision or protected architecture/security decision remains;
- `STOPPED` — continuing would violate security, permission, legal, or project boundaries.

## 10. Evidence preservation

Rollback removes unsafe working state; it does not erase history. Failed attempts remain in the audit record so the Factory can prove what happened and avoid repeating the same failure.