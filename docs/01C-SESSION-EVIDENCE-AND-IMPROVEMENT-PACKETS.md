# Approved Session Evidence and Improvement Packet Decision

**Status:** Approved architecture supplement  
**Recorded:** July 23, 2026

## 1. Disposable-session evidence rule

A task sandbox and its interactive terminal session may be disposed only after the required evidence record is complete, validated, written to approved storage, and linked to the task checkpoint and rollback record.

Secrets, credentials, tokens, and other protected values must be redacted before persistence. Redaction must preserve enough context to understand the command and result without retaining the protected value.

## 2. Required retained evidence

Every material test, simulation, build, repair, or verification run must retain:

- test or simulation purpose, including why it was run;
- inputs and configuration;
- environment identity, operating system, tool versions, dependency versions, model identity, and relevant hardware or sandbox limits;
- expected outcome;
- actual outcome;
- explicit pass, fail, blocked, not-testable, or inconclusive classification;
- failure root cause when proven, or an explicit `UNKNOWN` or `UNCONFIRMED` classification when it is not known;
- evidence supporting the conclusion;
- commands executed, outputs, errors, exit codes, and timestamps;
- files created, changed, deleted, or left unchanged;
- changes made to resolve the issue;
- validation proving whether the correction worked;
- regressions checked and their results;
- resources and elapsed time consumed;
- confidence level and basis for that confidence;
- checkpoint and rollback information;
- lessons learned;
- task, requirement, project, environment, and evidence identifiers needed for traceability.

A model statement is not sufficient evidence. Conclusions must reference deterministic tests, tool output, inspection records, or another approved verification method.

## 3. Raw-session retention

Full redacted raw terminal and execution logs are retained for a limited configured period. The retention duration is a configurable policy value and must be visible in the Dashboard.

Raw logs cannot be deleted until:

1. the structured evidence record is complete;
2. its integrity and traceability checks pass;
3. the applicable monthly Improvement Packet analysis has completed;
4. any hold caused by an unresolved failure, audit, rollback, security event, or user request is cleared.

Deletion removes only eligible raw logs. Structured evidence, verified lessons, audit records, checkpoints, and user-retained Improvement Packets remain according to their own retention policies.

## 4. Monthly analysis scope

Once each month, Factory analyzes eligible retained evidence, including:

- terminal and command records;
- failures and root-cause records;
- repairs and validation results;
- test and simulation outcomes;
- regression results;
- resource and time consumption;
- repeated warnings, bottlenecks, and recovery patterns;
- verified lessons and prior improvement outcomes.

Project source files are not inspected by default. Source inspection requires explicit project-scoped permission that identifies the project, paths, purpose, duration, and allowed analysis operations.

## 5. Improvement Packet

The monthly analysis produces one or more reviewable Improvement Packets before eligible raw-log deletion.

Each proposal must include:

- proposal identifier and date;
- affected Factory component or workflow;
- problem or opportunity detected;
- linked supporting evidence;
- proposed change;
- expected measurable benefit;
- risks and possible regressions;
- affected interfaces, contracts, permissions, tests, storage, models, tools, or components;
- required source-file permission, when applicable;
- validation and test plan;
- rollback plan;
- resource and time estimate based on retained evidence;
- confidence level and its basis;
- known limitations and unresolved uncertainty;
- whether the proposal duplicates, conflicts with, or supersedes an earlier proposal.

Unsupported suggestions, guessed root causes, and unverified claimed benefits must be marked unverified and cannot be presented as proven improvements.

## 6. User actions

For each Improvement Packet proposal, the Dashboard must allow the user to:

- **Test** — create a bounded experimental task and sandbox without changing approved production behavior;
- **Apply** — begin the normal protected change process after required tests and approvals;
- **Archive** — store the proposal and its evidence in the improvement database without applying it;
- **Delete** — remove the proposal while preserving any evidence that must remain for audit, security, recovery, or retention policy.

Factory must never automatically apply an Improvement Packet proposal.

## 7. Improvement database

The improvement database stores approved or archived proposals, linked evidence, test outcomes, measured effects, regressions, rollback results, status, and review dates.

A proposal becomes a verified reusable improvement only after controlled testing proves the claimed benefit without reducing a higher-priority requirement. Failed and rejected experiments remain recorded as lessons so Factory does not repeatedly retry disproven approaches without new evidence.

## 8. Acceptance criteria

This decision is satisfied only when tests prove that:

1. a disposable session cannot be destroyed before its required evidence is safely recorded;
2. missing or unknown root cause is represented honestly and cannot be silently guessed;
3. protected values are redacted before logs or evidence are stored;
4. monthly analysis uses evidence and logs by default and cannot inspect project source without project-scoped permission;
5. raw-log deletion is blocked until analysis and retention gates pass;
6. every proposal contains evidence, benefit, risk, validation, confidence, and rollback information;
7. proposals cannot auto-apply;
8. test, apply, archive, and delete actions follow their permission and evidence rules;
9. archived and applied improvements retain complete provenance and measured results.
