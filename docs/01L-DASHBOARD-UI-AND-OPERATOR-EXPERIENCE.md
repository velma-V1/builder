# Approved Dashboard, UI, and Operator Experience Decision

**Status:** Approved architecture supplement  
**Recorded:** July 23, 2026  
**Clarified:** July 23, 2026

## 1. Governing interface boundary

Factory uses one primary local Dashboard as the operator interface. The Dashboard presents authoritative backend state but is not itself the authoritative data store. It must remain fully usable offline, expose active work and controls clearly, and never hide autonomous or background activity.

The interface uses progressive disclosure: essential information is visible by default and technical detail is expandable. Separate simple and expert applications are not required.

## 2. Approved Stage 10 decisions

1. **Single primary Dashboard:** Factory uses one primary Dashboard rather than several separate control applications.
2. **Expandable technical detail:** The default view shows essential information while deeper technical detail remains expandable.
3. **Structured and conversational task entry:** Task creation is available through both structured forms and chat.
4. **Active project identity:** The Dashboard clearly shows the active project, primary repository, approved baseline commit, task branch, worktree, sandbox identity, selected task context, and loaded model fingerprint or route.
5. **Visible workstream cards:** Each workstream has a visible lane card showing scope, status, owner, dependencies, model, sandbox, resources, and completion gate.
6. **Formal state vocabulary:** Workstream and task state uses the approved deterministic state machine rather than an informal status vocabulary.
7. **Visible gates:** Dependency, approval, integration, verification, and promotion gates are visible with the reason work is waiting.
8. **Resource visibility:** CPU, RAM, GPU, VRAM, storage, model, sandbox, and material process use are visible.
9. **Central approval queue:** Approvals appear in one dedicated queue.
10. **Approval context:** Every approval conditionally shows all applicable action, tool, command, resource, network, credential, consequence, expiration, repetition, evidence, and rollback details required for an informed decision.
11. **Diff review:** File changes are shown as diffs before approval or promotion.
12. **Linked evidence:** Evidence is directly accessible from tasks, workstreams, approvals, improvements, pull requests, and releases.
13. **Memory provenance:** Retrieved memory displays source, authority, status, scope, evidence, and supersession state.
14. **Controlled terminal:** The Dashboard includes a controlled terminal view for sandbox command visibility and approved manual input.
15. **Terminal policy parity:** Manual terminal input follows the same sandbox, permission, evidence, resource, and audit controls as automated commands.
16. **Controlled Monaco editing:** Monaco supports controlled manual file inspection and editing without making VS Code a dependency.
17. **Manual-edit parity:** Dashboard edits enter the same diff, test, evidence, review, and promotion process as model-generated edits.
18. **Operator controls:** Factory exposes pause, resume, cancel, retry, quarantine, rollback, and emergency-stop controls.
19. **Destructive confirmation:** Destructive controls require explicit confirmation and clearly state consequences.
20. **Real-time testing indicator:** Real-time model-testing mode has a dedicated visible indicator and cannot be mistaken for live project work.
21. **Actionable errors:** Error views state what failed, what remains safe, what evidence exists, what is blocked, and the next valid action.
22. **Bounded notifications:** Notifications are limited primarily to approvals, failures, completed milestones, security events, quarantines, rollbacks, and requested updates.
23. **No hidden activity:** Factory does not hide autonomous or background actions from the operator.
24. **Backend authority:** The Dashboard is a view and control surface over authoritative backend records, not the sole source of truth.
25. **UI recovery:** Dashboard state can be reconstructed from authoritative backend records after a crash or restart.
26. **Offline operation:** The Dashboard and core Factory workflow operate fully offline.
27. **No default remote access:** Remote Dashboard access is disabled by default.
28. **Single-operator launch:** Multi-user roles are not required at launch; Factory is designed first for one operator while preserving future separation boundaries.
29. **Windows account boundary:** The local application primarily relies on the authenticated Windows user account and local OS protections.
30. **Optional convenience lock:** An optional Dashboard lock or PIN is available for shared or unattended machines but is not an independent security boundary.
31. **Exportable records:** Evidence, reports, audit packages, and approved records are exportable through controlled operations.
32. **Passive editor adapter boundary:** Factory reserves a versioned local editor-integration adapter interface. It remains disabled by default, creates no VS Code dependency, and provides no Dashboard launch control until implemented and verified.
33. **No automatic analytics:** Factory does not send analytics, telemetry, or crash reports automatically.
34. **Accessibility from initial design:** Keyboard navigation, readable focus states, scalable text, accessible labels, and other core accessibility requirements are included from the initial UI design.
35. **Appearance separation:** Appearance preferences remain separate from safety, authority, permissions, and workflow behavior.

## 3. Binding operator-experience clarifications

### 3.1 Formal workstream state machine

Factory uses at least these states:

```text
QUEUED
PLANNING
RUNNING
AWAITING_APPROVAL
VERIFYING
BLOCKED
PAUSED
FAILED
QUARANTINED
STOPPING
CANCELLED
COMPLETE
ROLLED_BACK
```

Legal transitions are defined in versioned state-machine policy. The minimum permitted transition set includes:

```text
QUEUED -> PLANNING
PLANNING -> RUNNING | AWAITING_APPROVAL | BLOCKED | FAILED | STOPPING
RUNNING -> AWAITING_APPROVAL | VERIFYING | BLOCKED | PAUSED | FAILED | QUARANTINED | STOPPING
AWAITING_APPROVAL -> RUNNING | VERIFYING | BLOCKED | STOPPING
VERIFYING -> COMPLETE | RUNNING | AWAITING_APPROVAL | BLOCKED | FAILED | QUARANTINED | STOPPING
PAUSED -> RUNNING | BLOCKED | STOPPING
BLOCKED -> PLANNING | RUNNING | AWAITING_APPROVAL | FAILED | STOPPING
QUARANTINED -> BLOCKED | FAILED | STOPPING
STOPPING -> CANCELLED
COMPLETE -> ROLLED_BACK
FAILED -> ROLLED_BACK
```

No client, model, workstream, or Dashboard component may invent a transition. Every state change records:

- preceding state;
- new state;
- cause and normalized reason code;
- actor or authoritative service;
- monotonic transition ordering and wall-clock display timestamp;
- linked command, approval, evidence, failure, checkpoint, or recovery record.

Invalid transitions fail closed and create an audit event.

### 3.2 Complete approval-card scope

An approval record conditionally displays every applicable field:

- exact command or normalized action;
- tool identity and version;
- working directory, task branch, worktree, and sandbox identity;
- affected file paths and expected diffs;
- non-file resources and state changes;
- network destinations, protocols, and operations;
- credential identity, broker reference, and granted scope without revealing the secret;
- external side effects and recipients;
- risk class and consequences;
- expiration and permitted repetition count;
- required evidence and current verification status;
- rollback or recovery availability;
- whether the action is reversible, destructive, privileged, promotional, or externally consequential.

Fields that do not apply are marked not applicable rather than silently omitted when their absence could change the operator's understanding.

### 3.3 Passive local editor-integration boundary

Factory reserves a stable versioned editor-adapter interface for a future VS Code or other local editor connection.

The adapter:

- remains disabled by default;
- is not required for Factory operation;
- does not launch VS Code from the Dashboard until separately implemented, tested, and approved;
- uses the same safe file, permission, diff, evidence, test, audit, and promotion services as Monaco;
- cannot expose direct repository, terminal, protected-ref, credential, or host-access bypasses;
- can be removed or disabled without affecting core Factory operation.

### 3.4 Local identity and convenience lock

The authenticated Windows account and operating-system session remain the actual local identity and access boundary. A Dashboard PIN or convenience lock protects casual access only. It must not be represented as equivalent to OS authentication, privilege separation, disk encryption, or multi-user authorization.

### 3.5 Active execution identity

The active-project area and workstream cards show enough exact identity to prevent operator confusion, including:

- Project ID and project name;
- primary and affected repositories;
- approved baseline commit;
- current task branch;
- worktree path or identity;
- sandbox or container identity;
- task and workstream IDs;
- current state and blocking gate;
- loaded model fingerprint or abstract route;
- current checkpoint and pending promotion target.

## 4. Operating boundaries

- Factory uses one interface with expandable detail rather than separate simple and expert modes.
- Monaco, terminal, and future editor-adapter actions follow the same protected workflow as model actions.
- Remote access and multi-user roles remain deferred; the passive editor adapter remains disabled by default.
- The Dashboard is never the sole source of project, evidence, memory, audit, or state-machine truth.
- Active operations and exact execution identities remain observable.
- A Dashboard PIN is a convenience lock, not a security boundary.
- No telemetry is transmitted automatically.

## 5. Acceptance criteria

This decision is satisfied only when tests prove that:

1. the active project displays its Project ID, repositories, baseline commit, task branch, worktree, sandbox, task, workstream, model, checkpoint, and promotion target;
2. workstream cards expose current state, scope, dependencies, resources, gates, and owners;
3. only declared legal workstream transitions can occur;
4. invalid state transitions fail closed and create an audit event;
5. every state change records previous state, new state, cause, actor, ordering, timestamp, and linked evidence;
6. approvals expose all applicable command, tool, directory, sandbox, file, network, credential, side-effect, expiration, repetition, evidence, and rollback information;
7. non-file actions can receive complete informed approval without relying on a file diff;
8. manual terminal and Monaco actions cannot bypass sandbox, permission, resource, evidence, audit, or promotion controls;
9. a future editor adapter cannot bypass Factory controls or become a core dependency;
10. the editor adapter remains disabled and no VS Code launch control appears before implementation and verification;
11. resource use and active model or sandbox assignments are visible;
12. real-time model testing is clearly distinguished from live project work;
13. errors expose the safe remaining state and next valid action;
14. autonomous activity cannot be hidden from the operator;
15. a Dashboard crash does not destroy authoritative task or project state;
16. core operation works without internet access;
17. remote access and automatic telemetry remain disabled by default;
18. the Windows account remains the real identity boundary and the Dashboard PIN is labeled as a convenience lock;
19. evidence and audit records can be exported through controlled actions;
20. accessibility and keyboard navigation are present in the initial interface design;
21. visual appearance settings cannot change system authority or safety behavior.