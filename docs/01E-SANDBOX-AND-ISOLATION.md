# Approved Sandbox and Isolation Decision

**Status:** Approved architecture supplement  
**Recorded:** July 23, 2026

## 1. Governing boundary

All code-changing, command-executing, package-installing, build, test, repair, and real-time model-testing work must run inside an isolated sandbox or container linked to the responsible task and workstream.

Models and tools cannot directly modify the host, live project, protected branch, or approved Factory state. Promotion requires the normal verification, policy, evidence, and approval gates.

Read-only repository inspection does not require a full execution sandbox when Factory can enforce a controlled read-only workspace with no command execution, package installation, writable project mount, or external side effect.

## 2. Approved Stage 3 decisions

1. **Read-only analysis:** Safe repository inspection may use a controlled read-only workspace instead of a full sandbox.
2. **Per-workstream isolation:** Each active code-changing workstream receives its own sandbox unless a later approved task design proves shared execution is required and equally isolated.
3. **Task reuse:** A workstream may reuse its sandbox throughout one task to preserve legitimate build state and avoid unnecessary recreation.
4. **Traceability:** Every sandbox is linked to its Task ID, workstream, project, environment identity, evidence, checkpoints, and disposal result.
5. **Versioned environments:** Sandbox base images and environment definitions are versioned and identifiable in retained evidence.
6. **Shared caches:** Sandboxes may share dependency or model caches only when project state cannot be written through the cache. Read-only access is preferred.
7. **Default network denial:** Network access is disabled by default.
8. **Scoped network access:** Temporary network access requires task-scoped approval defining destinations or purpose, allowed operations, duration, and evidence requirements.
9. **Credential handling:** Credentials are never stored in sandbox images. Approved task-specific credentials may be injected temporarily, minimized to required scope, redacted from records, and revoked or removed after use.
10. **Host mounts:** Direct host-directory mounts are limited to explicit read-only inputs and approved output locations. No implicit writable host mount is allowed.
11. **Resource limits:** Each sandbox has bounded CPU, RAM, GPU, disk, process, and storage-I/O limits appropriate to the task and current hardware.
12. **Runtime limits:** Commands use configurable maximum-runtime and inactivity limits selected by task type. Legitimate long-running work may receive an approved higher limit.
13. **Checkpointing:** Factory does not continuously snapshot complete sandboxes. It stores lightweight verified task checkpoints sufficient for safe recovery.
14. **Failed sandbox retention:** Evidence, logs, required artifacts, and recovery information are retained. The full failed sandbox is preserved only under an explicit investigation, audit, security, or recovery hold.
15. **Untrusted repositories:** Untrusted repositories receive stricter isolation, including denied network, denied credentials, denied writable host mounts, restricted execution, and blocked promotion until inspection and verification pass.
16. **Package installation:** New packages are installed only inside the sandbox or its approved versioned environment, never directly into the host or protected Factory runtime.
17. **Promotion gate:** Sandbox outputs cannot enter the live project or approved Factory state automatically. They must pass applicable tests, verification, policy checks, evidence requirements, and user approval.
18. **Disposal:** A sandbox is cleaned up after required evidence and approved outputs are secured, unless an active hold requires preservation.

## 3. Disposable-session relationship

Sandbox disposal remains governed by the approved evidence and retention policy. A sandbox or interactive session cannot be destroyed until required evidence is complete, validated, stored, and linked to its task, checkpoints, artifacts, and rollback record.

Sandbox and Factory records remain separately managed while linked through approved identifiers and integrity references.

## 4. Acceptance criteria

This decision is satisfied only when tests prove that:

1. code-changing or command-executing work cannot run directly against the host or live project;
2. controlled read-only analysis cannot execute commands, install packages, or modify repository state;
3. concurrent code-changing workstreams receive isolated project and execution state;
4. every sandbox is traceable to its task, workstream, environment, evidence, checkpoints, and disposal result;
5. versioned environment identity is included in reproducibility evidence;
6. shared caches cannot carry writable project state between sandboxes;
7. network access is denied by default and cannot be enabled without bounded task-scoped approval;
8. credentials cannot be embedded in images or retained unredacted in evidence;
9. unauthorized writable host mounts are blocked;
10. configured CPU, RAM, GPU, disk, process, and runtime limits are enforced;
11. recovery uses verified checkpoints rather than mandatory continuous full-sandbox snapshots;
12. failed sandboxes are disposed after evidence capture unless a valid hold requires preservation;
13. untrusted repositories cannot access network, credentials, writable host paths, or promotion before required inspection passes;
14. package installation cannot modify the host or protected Factory runtime;
15. sandbox outputs cannot reach live project state without the required promotion gates;
16. disposal cannot occur before evidence and approved outputs are secured;
17. real-time model testing remains isolated and cannot modify or promote live project state directly.