# Approved Sandbox and Isolation Decision

**Status:** Approved architecture supplement  
**Recorded:** July 23, 2026  
**Clarified:** July 23, 2026

## 1. Governing boundary

All code-changing, command-executing, package-installing, build, test, repair, and real-time model-testing work must run inside an isolated sandbox or container linked to the responsible task and workstream.

Models and tools cannot directly modify the host, live project, protected branch, or approved Factory state. The host project is never exposed as a writable sandbox mount. Sandbox output exits only through a Factory-controlled quarantined staging area and enters approved state only through hashing, inspection, verification, policy checks, evidence completion, approval, and promotion.

A reduced read-only repository workspace is allowed only for non-executing inspection. Any operation capable of executing repository-controlled hooks, scripts, plugins, macros, build logic, package lifecycle actions, development-container configuration, IDE tasks, or repository-provided executables requires a sandbox.

## 2. Approved Stage 3 decisions

1. **Non-executing read-only analysis:** Safe repository inspection may use a controlled read-only workspace only when hooks, plugins, macros, scripts, package actions, build logic, IDE tasks, and repository executables cannot run.
2. **Per-workstream isolation:** Each active code-changing workstream receives its own sandbox unless a later approved task design proves shared execution is required and equally isolated.
3. **Task reuse:** A workstream may reuse its sandbox throughout one task to preserve legitimate build state and avoid unnecessary recreation.
4. **Traceability:** Every sandbox is linked to its Task ID, workstream, project, environment identity, evidence, checkpoints, staging exports, and disposal result.
5. **Versioned environments:** Sandbox base images and environment definitions are versioned and identifiable in retained evidence.
6. **Trusted shared caches:** Sandboxes may share dependency or model caches only when the cache is immutable or content-addressed, contains no credentials or writable project state, and is updated only through a trusted cache-management process.
7. **Default network denial:** Network access is disabled by default.
8. **Scoped network access:** Temporary network access requires a task-scoped approval contract defining destination allowlists, protocols, operations, duration, transfer limits, request logging, inbound-access policy, and automatic revocation.
9. **Brokered secret handling:** Credentials are short-lived, least-privilege, task-scoped, broker-injected, redacted from logs, and removed before checkpointing, staging export, or disposal.
10. **No writable host-project mounts:** Direct writable mounts to the host project, protected Factory state, or arbitrary host output locations are prohibited. Sandbox outputs may be exported only to a Factory-controlled quarantined staging area.
11. **Resource enforcement:** Sandboxes receive hard CPU, RAM, GPU, disk, process, and storage-I/O limits where the platform supports them. Where reliable hard isolation is unavailable, the Resource Scheduler enforces admission, reservation, monitoring, throttling, checkpointed pause, and bounded termination thresholds.
12. **Runtime limits:** Commands use configurable wall-clock and inactivity limits selected by task type. Legitimate long-running work may receive an approved higher limit.
13. **Checkpointing:** Factory does not continuously snapshot complete sandboxes. It stores lightweight verified task checkpoints sufficient for safe recovery.
14. **Failed sandbox retention:** Evidence, logs, required artifacts, and recovery information are retained. The full failed sandbox is preserved only under an explicit investigation, audit, security, or recovery hold.
15. **Untrusted repositories:** Untrusted repositories receive stricter isolation and pre-execution inspection, including denied network, denied credentials, denied writable host mounts, restricted execution, and blocked promotion until required checks pass.
16. **Package installation:** New packages are installed only inside the sandbox or its approved versioned environment, never directly into the host or protected Factory runtime.
17. **Promotion gate:** Sandbox outputs cannot enter the live project or approved Factory state automatically. Promotion requires a complete Promotion Package from quarantined staging and all applicable verification, policy, evidence, and approval gates.
18. **Disposal:** A sandbox is cleaned up after required evidence and approved staging outputs are secured, unless an active hold requires preservation.

## 3. Binding sandbox controls

### 3.1 Prohibited privileges and host control

The following are prohibited by default and cannot be granted through an ordinary task approval:

- privileged containers;
- host Docker or container-runtime socket access;
- host process namespace access;
- host IPC namespace access;
- host network namespace control;
- unapproved device access;
- nested container or sibling-container control;
- host-level service installation, start, stop, or configuration;
- host registry, scheduled-task, startup, driver, kernel, or firewall management;
- unrestricted host filesystem mounts.

A separately approved architecture or maintenance workflow may define a narrow host-management operation, but it remains outside ordinary sandbox execution and must use dedicated controls, evidence, rollback, and operator approval.

### 3.2 Sandbox execution identity

Sandbox processes run as a dedicated non-root user by default. The execution identity records user and group IDs, granted capabilities, mounts, network policy, devices, secrets, and resource policy.

Root inside the sandbox requires explicit task-specific approval, a declared reason, bounded commands, retained evidence, and a disposable environment. Sandbox root must not provide host root, administrator authority, container-runtime control, host namespaces, or protected host access.

### 3.3 Network approval contract

Every temporary network approval defines:

- exact allowed destinations or approved destination classes;
- permitted protocols, ports, request methods, and operations;
- start time, expiration, and maximum duration;
- per-request, per-download, and total-transfer limits;
- redirect handling that cannot escape the allowlist;
- full request metadata logging with secret redaction;
- whether project data may be transmitted and the exact permitted fields;
- credential scope and broker identity when applicable;
- no unsolicited inbound access;
- automatic revocation after the approved operation or expiration.

The sandbox remains denied from all destinations and operations not explicitly included in the contract.

### 3.4 Secret lifecycle

Approved credentials and secrets must be:

- short-lived and revocable;
- least-privilege and task-scoped;
- injected at execution time through the secret broker;
- unavailable to unrelated processes and lanes;
- redacted from commands, environment displays, output, logs, evidence, crash records, and exports;
- excluded from container images, layers, caches, checkpoints, artifacts, and Promotion Packages;
- revoked and removed before sandbox checkpointing, staging export, task completion, or disposal.

Secret scanning occurs before evidence finalization and staging export. A detected secret blocks export until it is removed or separately protected under an approved exception.

### 3.5 Shared-cache trust boundary

A shared cache must be immutable or content-addressed to consumers. It cannot contain:

- credentials, tokens, private keys, or personal secrets;
- writable project files or authoritative Factory state;
- mutable build outputs that one sandbox can replace beneath another;
- unverified executable content presented as trusted.

Cache additions occur only through a trusted cache-management process that verifies source, immutable identity, integrity, compatibility, license when applicable, and malware or policy checks. Consumers cannot mutate shared entries in place.

### 3.6 Untrusted repository pre-execution controls

Before executing an imported or untrusted repository, Factory inspects, disables, removes, or separately approves applicable execution paths including:

- Git hooks and hook configuration;
- symlink, junction, reparse-point, archive, and path-traversal escapes;
- submodule URLs, update actions, and recursive checkout behavior;
- Git LFS filters and custom clean or smudge drivers;
- package manager lifecycle and post-install scripts;
- build hooks, code generators, compiler plugins, and test plugins;
- development-container and container-compose configuration;
- IDE workspace tasks, launch configurations, and extension recommendations;
- repository-provided executables, installers, binaries, macros, and scripts;
- environment files and configuration capable of changing tool execution.

Inspection does not establish trust by itself. Any approved execution remains sandboxed, default-deny, resource-bounded, and evidence-recorded.

### 3.7 Quarantined staging export

Sandbox output may leave the sandbox only into a Factory-controlled quarantined staging area that is separate from:

- the live project;
- protected branches and refs;
- authoritative Factory state;
- trusted caches;
- release output directories.

Staged output is non-authoritative and non-promotable until Factory:

1. inventories every file and directory;
2. canonicalizes paths and rejects traversal, symlink, junction, reparse-point, reserved-name, and device escapes;
3. records file type, size, permissions, provenance, and cryptographic hash;
4. scans for secrets, unexpected executables, archive bombs, malicious content, and policy violations;
5. compares the exact changes with approved task scope and expected diffs;
6. verifies dependencies, generated content, and artifact identities;
7. links all required test, verification, policy, and evidence records;
8. receives required approval;
9. promotes through the approved safe file and Promotion Service interfaces.

No sandbox process receives write access to the live project through staging.

### 3.8 Promotion Package manifest

Every proposed sandbox promotion contains a machine-readable Promotion Package with at least:

- Project, Task, stage, workstream, lane, and sandbox identities;
- source repository identity, approved source commit, task branch, and checkout identity;
- environment, base image, runtime, tool, model, and dependency versions;
- exact added, modified, deleted, renamed, and generated files;
- cryptographic hashes for staged files and promoted artifacts;
- complete diff and scope comparison;
- dependency, lockfile, model, image, schema, migration, and configuration changes;
- test and verification results linked through the Evidence Traceability Manifest;
- security, path, secret, license, resource, and policy results;
- unresolved risks, limitations, and non-promotable items;
- approver identity and approval-record reference;
- checkpoint and rollback reference;
- staging-area identity and integrity status.

A Promotion Package with missing, ambiguous, stale, or hash-mismatched contents is blocked.

### 3.9 Resource-control fallback

Where the platform supports hard isolation, Factory applies enforceable cgroup, container, job-object, quota, or equivalent limits. Where a resource cannot be hard-limited reliably, Factory must still use:

- pre-execution reservation and admission control;
- monitored warning, throttle, pause, and critical termination thresholds;
- sustained-duration windows and hysteresis;
- deterministic cancellation order;
- checkpointing before noncritical pause or termination when safe;
- fail-closed denial when safe bounded execution cannot be established.

A missing hard-limit mechanism cannot be represented as equivalent hard isolation.

## 4. Disposable-session and record relationship

Sandbox execution logs, recordings, temporary files, raw artifacts, downloaded material, and temporary evidence remain in a separate sandbox evidence store.

Factory may retain immutable indexes, hashes, Task IDs, decisions, approvals, Promotion Package references, evidence-package identities, and integrity links to those sandbox records.

Sandbox data follows the approved rolling retention period but is independently indexed, held, expired, exported, and deleted. Deleting a sandbox or expiring raw sandbox data must not delete:

- required finalized evidence packages;
- promoted artifacts and their hashes;
- authoritative audit records;
- approvals and decisions;
- protected checkpoints;
- rollback and recovery references.

A sandbox or interactive session cannot be destroyed until required evidence is complete, validated, stored, integrity-protected, and linked to its task, checkpoints, artifacts, Promotion Package, and rollback record.

## 5. Operating boundaries

- Read-only workspaces permit non-executing inspection only.
- Ordinary sandboxes cannot receive privileged host-control capabilities.
- Sandbox execution is non-root by default and root cannot confer host privilege.
- Network, secrets, caches, mounts, and resources remain explicit, bounded, and task-scoped.
- Host projects are never writable sandbox mounts.
- All output exits through quarantined staging and a verified Promotion Package.
- Sandbox raw records remain separately managed while required evidence and authoritative references survive disposal.

## 6. Acceptance criteria

This decision is satisfied only when tests prove that:

1. code-changing or command-executing work cannot run directly against the host or live project;
2. controlled read-only analysis cannot execute hooks, plugins, macros, scripts, package actions, build logic, IDE tasks, or repository executables;
3. an operation capable of repository-controlled execution is forced into a sandbox;
4. concurrent code-changing workstreams receive isolated project and execution state;
5. every sandbox is traceable to its task, workstream, environment, evidence, staging exports, checkpoints, and disposal result;
6. versioned environment identity is included in reproducibility evidence;
7. shared caches are immutable or content-addressed, credential-free, project-state-free, and updated only through the trusted cache process;
8. network access remains denied without a complete task-scoped network approval contract;
9. redirects, protocols, destinations, transfers, project-data transmission, and expiration cannot exceed the approved network contract;
10. unsolicited inbound network access remains blocked;
11. credentials cannot be embedded in images, caches, checkpoints, artifacts, Promotion Packages, or retained unredacted in evidence;
12. credentials are brokered, scoped, revoked, and removed before checkpointing, export, or disposal;
13. privileged containers, host runtime sockets, host namespaces, nested container control, unapproved devices, and host service management remain denied;
14. non-root execution is the default and approved sandbox root cannot gain host privilege;
15. direct writable mounts to the host project, protected Factory state, or arbitrary host output locations are blocked;
16. sandbox output can reach only the Factory-controlled quarantined staging area before promotion;
17. staging inspection detects path escapes, secrets, unexpected executables, archive hazards, scope violations, and hash mismatches;
18. a complete Promotion Package is required before any staged output can enter approved state;
19. Promotion Package hashes, diffs, dependencies, policy results, evidence, approval, and rollback references match the promoted content;
20. hard resource limits are enforced where supported;
21. scheduler admission, monitoring, throttling, pause, or termination controls apply where reliable hard limits are unavailable;
22. Factory fails closed when safe bounded execution cannot be established;
23. wall-clock, inactivity, process-tree, storage, and transfer limits are enforced;
24. recovery uses verified checkpoints rather than mandatory continuous full-sandbox snapshots;
25. failed sandboxes are disposed after evidence capture unless a valid hold requires preservation;
26. untrusted repositories cannot execute before hooks, path escapes, submodules, lifecycle scripts, build hooks, dev-container settings, IDE tasks, and repository executables are inspected or disabled;
27. package installation cannot modify the host or protected Factory runtime;
28. sandbox outputs cannot reach live project state without staging, verification, evidence, policy, approval, and Promotion Service gates;
29. sandbox raw records remain separate from authoritative Factory project and audit records;
30. sandbox disposal or raw-data expiration cannot delete required finalized evidence, promoted hashes, audit records, approvals, checkpoints, or rollback references;
31. disposal cannot occur before required evidence and approved staging outputs are secured;
32. real-time model testing remains isolated and cannot modify or promote live project state directly.