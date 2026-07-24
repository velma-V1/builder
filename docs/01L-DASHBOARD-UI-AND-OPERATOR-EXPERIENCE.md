# Approved Dashboard, UI, and Operator Experience Decision

**Status:** Approved architecture supplement  
**Recorded:** July 23, 2026

## 1. Governing interface boundary

Factory uses one primary local Dashboard as the operator interface. The Dashboard presents authoritative backend state but is not itself the authoritative data store. It must remain fully usable offline, expose active work and controls clearly, and never hide autonomous or background activity.

The interface uses progressive disclosure: essential information is visible by default and technical detail is expandable. Separate simple and expert applications are not required.

## 2. Approved Stage 10 decisions

1. **Single primary Dashboard:** Factory uses one primary Dashboard rather than several separate control applications.
2. **Expandable technical detail:** The default view shows essential information while deeper technical detail remains expandable.
3. **Structured and conversational task entry:** Task creation is available through both structured forms and chat.
4. **Active project identity:** The Dashboard clearly shows the active project, repository, branch or baseline, and selected task context.
5. **Visible workstream cards:** Each workstream has a visible lane card showing scope, status, owner, dependencies, model, sandbox, resources, and completion gate.
6. **Fixed status vocabulary:** Workstream and task states use a defined vocabulary such as `QUEUED`, `PLANNING`, `RUNNING`, `BLOCKED`, `VERIFYING`, `COMPLETE`, `FAILED`, `PAUSED`, and `QUARANTINED`.
7. **Visible gates:** Dependency, approval, integration, verification, and promotion gates are visible with the reason work is waiting.
8. **Resource visibility:** CPU, RAM, GPU, VRAM, storage, model, sandbox, and material process use are visible.
9. **Central approval queue:** Approvals appear in one dedicated queue.
10. **Approval context:** Every approval shows action, purpose, scope, risk, affected files or resources, evidence, expiration, reversibility, and consequences.
11. **Diff review:** File changes are shown as diffs before approval or promotion.
12. **Linked evidence:** Evidence is directly accessible from tasks, workstreams, approvals, improvements, pull requests, and releases.
13. **Memory provenance:** Retrieved memory displays source, authority, status, scope, evidence, and supersession state.
14. **Controlled terminal:** The Dashboard includes a controlled terminal view for sandbox command visibility and approved manual input.
15. **Terminal policy parity:** Manual terminal input follows the same sandbox, permission, evidence, and audit controls as automated commands.
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
30. **Optional Dashboard lock:** An optional Dashboard lock or PIN is available for shared or unattended machines.
31. **Exportable records:** Evidence, reports, audit packages, and approved records are exportable through controlled operations.
32. **Deferred VS Code button:** A VS Code launch or connect button is not required until the optional integration is implemented and approved.
33. **No automatic analytics:** Factory does not send analytics, telemetry, or crash reports automatically.
34. **Accessibility from initial design:** Keyboard navigation, readable focus states, scalable text, accessible labels, and other core accessibility requirements are included from the initial UI design.
35. **Appearance separation:** Appearance preferences remain separate from safety, authority, permissions, and workflow behavior.

## 3. Operating boundaries

- Factory uses one interface with expandable detail rather than separate simple and expert modes.
- Monaco edits follow the same protected workflow as model edits.
- Remote access, multi-user roles, and VS Code launching are deferred.
- The Dashboard is never the sole source of project, evidence, memory, or audit truth.
- Active operations remain observable and no telemetry is transmitted automatically.

## 4. Acceptance criteria

This decision is satisfied only when tests prove that:

1. the active project, repository, task, lane state, and blocking gates are always visible;
2. approvals expose sufficient scope, risk, evidence, expiration, and consequences for an informed decision;
3. manual terminal and Monaco actions cannot bypass sandbox, permission, evidence, or promotion controls;
4. resource use and active model or sandbox assignments are visible;
5. real-time model testing is clearly distinguished from live project work;
6. errors expose the safe remaining state and next valid action;
7. autonomous activity cannot be hidden from the operator;
8. a Dashboard crash does not destroy authoritative task or project state;
9. core operation works without internet access;
10. remote access and automatic telemetry remain disabled by default;
11. evidence and audit records can be exported through controlled actions;
12. accessibility and keyboard navigation are present in the initial interface design;
13. visual appearance settings cannot change system authority or safety behavior.