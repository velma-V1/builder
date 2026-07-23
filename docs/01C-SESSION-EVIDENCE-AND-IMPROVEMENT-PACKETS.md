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

## 3. Rolling raw-session retention

Full redacted raw terminal and execution logs use a rolling lifecycle based on each record's Factory ingestion timestamp:

- **Age 0 through 30 days — Hot:** indexed, searchable, visible in the Dashboard, and eligible for active Watchdog monitoring.
- **Age 31 through 60 days — Cold:** compressed, read-only, hidden from normal Dashboard views, and searchable through the archive index.
- **Age 61 days or older — Expired:** eligible raw files are purged individually only after every retention gate passes.

This is a rolling per-file policy, not a monthly bulk deletion. Only records that have reached their lifecycle boundary are transitioned or removed.

Factory records and sandbox or container records remain logically and physically separated for auditing and traceability. They are linked only through approved identifiers and integrity references, including task ID, sandbox ID, project ID, timestamps, evidence references, artifact hashes, and promotion or disposal result.

## 4. Retention processing schedule

Retention processing runs once daily during the first safe idle window.

If no safe idle window occurs, processing is deferred until the next safe idle window. Overdue records remain protected and are marked pending; retention work must not be forced during active Factory work.

Overdue work is processed:

1. in five-minute bounded batches;
2. oldest eligible records first;
3. in consecutive five-minute batches while Factory remains safely idle and resource limits remain satisfied;
4. with immediate pause when active Factory work resumes.

## 5. Safe-idle policy

Retention processing may begin only when all of the following are true:

- no Factory task is active;
- no model inference is active;
- no terminal command is active;
- no test run is active;
- no approval workflow is active;
- resource use remains below the configured limits.

The fixed default thresholds are:

- CPU below 25 percent;
- RAM below 75 percent;
- GPU below 10 percent;
- disk activity below 20 percent.

All thresholds are user-configurable and must be visible in the Dashboard.

The complete safe-idle condition must remain satisfied for two continuous minutes before retention processing starts or resumes.

When active Factory work begins, retention processing pauses immediately. A resource-threshold breach alone pauses processing only after the threshold remains exceeded for 15 continuous seconds, preventing brief spikes from causing unnecessary interruption.

## 6. Checkpoint, interruption, and retry behavior

Retention processing writes a persistent checkpoint after every completed file.

If a batch is interrupted:

- processing resumes from the last completed-file checkpoint;
- a partially processed file is never deleted;
- the interrupted file is restored to a valid retained state when necessary;
- the interrupted file is revalidated and retried first during the next safe-idle batch.

A file may be retried no more than three times for the same unresolved processing failure. After the third failed attempt, Factory must quarantine the file for review, preserve its error and evidence, place it on retention hold, and prevent automatic deletion.

## 7. Purge eligibility and retention holds

A raw record is purge-eligible only when all of the following are true:

```text
age > 60 days
AND hold == false
AND investigation is closed or absent
AND structured evidence is complete
AND evidence integrity and traceability checks pass
AND cold-archive integrity is verified
AND applicable monthly Improvement Packet analysis is complete
```

A retention hold blocks deletion when caused by:

- an unresolved failure or investigation;
- an audit;
- an active or unresolved rollback;
- a security event;
- a quarantined processing failure;
- an explicit user hold;
- another approved legal, recovery, or evidence-preservation requirement.

Viewing or reading a record does not extend retention by itself. Retention is extended only by an active investigation, explicit hold, or another approved preservation rule.

Deletion removes only eligible raw logs. Structured evidence, verified lessons, audit records, checkpoints, Improvement Packet decisions, required rollback records, and other permanent records remain under their separate retention policies.

## 8. Monthly analysis scope

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

## 9. Improvement Packet

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

## 10. User actions

For each Improvement Packet proposal, the Dashboard must allow the user to:

- **Test** — create a bounded experimental task and sandbox without changing approved production behavior;
- **Apply** — begin the normal protected change process after required tests and approvals;
- **Archive** — store the proposal and its evidence in the improvement database without applying it;
- **Delete** — remove the proposal while preserving any evidence that must remain for audit, security, recovery, or retention policy.

Factory must never automatically apply an Improvement Packet proposal.

## 11. Improvement database

The improvement database stores approved or archived proposals, linked evidence, test outcomes, measured effects, regressions, rollback results, status, and review dates.

A proposal becomes a verified reusable improvement only after controlled testing proves the claimed benefit without reducing a higher-priority requirement. Failed and rejected experiments remain recorded as lessons so Factory does not repeatedly retry disproven approaches without new evidence.

## 12. Acceptance criteria

This decision is satisfied only when tests prove that:

1. a disposable session cannot be destroyed before its required evidence is safely recorded;
2. missing or unknown root cause is represented honestly and cannot be silently guessed;
3. protected values are redacted before logs or evidence are stored;
4. every raw record follows the 0-to-30-day hot, 31-to-60-day cold, and 61-day purge-eligibility lifecycle individually;
5. Factory and sandbox raw records remain independently stored but traceably linked;
6. retention processing runs only in a verified safe-idle window and never interrupts active Factory work;
7. five-minute batches, oldest-first ordering, pause behavior, and two-minute resume confirmation work as specified;
8. checkpoints prevent partial processing or deletion after interruption;
9. a repeatedly failing file is quarantined after three failed retries and cannot be deleted automatically;
10. raw-log deletion is blocked until evidence, archive, monthly-analysis, investigation, and hold gates pass;
11. monthly analysis uses evidence and logs by default and cannot inspect project source without project-scoped permission;
12. every proposal contains evidence, benefit, risk, validation, confidence, and rollback information;
13. proposals cannot auto-apply;
14. test, apply, archive, and delete actions follow their permission and evidence rules;
15. archived and applied improvements retain complete provenance and measured results.
