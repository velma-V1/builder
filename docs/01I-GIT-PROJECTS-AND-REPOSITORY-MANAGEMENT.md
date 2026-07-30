# Approved Git, Projects, and Repository Management Decision

**Status:** Approved architecture supplement  
**Recorded:** July 23, 2026  
**Clarified:** July 23, 2026

## 1. Governing repository boundary

GitHub remains the primary remote protection and history layer for project repositories. Factory also enforces protected-reference policy locally so the same safety boundary remains effective while offline. Factory uses Git for traceability, controlled task branches, verified checkpoints, review, promotion, release identity, and rollback without duplicating committed project history in Factory memory.

Protected branches, protected refs, and original host workspaces are not direct work areas. Every executable code-changing task receives its own controlled task branch from an approved baseline. A stage integration branch is optional and exists only when a stage contains multiple independently verified task branches. Separate lane branches and worktrees are created only for approved parallel work.

Protected refs may change only through the Promotion Service after the applicable verification, evidence, review, approval, and integration gates pass.

## 2. Approved Stage 7 decisions

1. **Factory project record:** Every project has a Factory project record linking repositories, tasks, requirements, evidence, releases, and approved project metadata.
2. **Git requirement:** Every code project managed by Factory uses Git for traceability, comparison, checkpointing, and rollback.
3. **Multiple repositories:** One Factory project may contain multiple repositories when the system legitimately spans them.
4. **Primary repository:** Every multi-repository project identifies one primary repository or governing baseline.
5. **Controlled workspace:** Existing repositories are cloned or materialized into controlled Factory workspaces rather than edited in their original host location.
6. **Trust classification:** Imported repositories receive a trust classification that governs isolation, execution, network, credentials, mounts, and promotion.
7. **Protected branches:** Protected branches and refs remain read-only to workstreams and cannot be modified directly.
8. **Approved baseline:** Every executable task branch starts from an identified approved baseline commit.
9. **Traceable branch names:** Branch names include sufficient project, task, stage, or lane identity for ownership and audit traceability.
10. **Unexplained local changes:** Factory refuses to begin normal work when unexplained local changes exist in the selected workspace.
11. **Importing existing changes:** Existing local changes may be imported into a task only after explicit scope confirmation, ownership assignment, and baseline recording.
12. **Remote synchronization:** Factory synchronizes with the approved remote before task-branch creation when task-scoped network access is available and synchronization is required.
13. **No automatic force-push:** Factory never force-pushes automatically.
14. **History rewriting:** Rebase, reset, force-push, or other history rewriting requires explicit high-risk approval and retained evidence.
15. **Commit traceability:** Factory commits include Task ID, stage or workstream identity, purpose, and verification or checkpoint status.
16. **Coherent commits:** Factory does not commit every small edit. Commits represent coherent verified checkpoints or completed units of work.
17. **Checkpoint commits:** Factory may automatically create verified checkpoint commits on controlled task branches.
18. **Controlled promotion:** Promotion to a protected branch requires a pull request or equivalent controlled Promotion Service boundary.
19. **Automatic pull-request creation:** Factory may create a pull request automatically after the user approves the scope and applicable verification gates pass.
20. **Pull-request evidence:** Pull requests include requirements, changed scope, test results, evidence, known risks, limitations, and rollback information.
21. **Merge gates:** Merge is blocked until required checks, evidence, dependency gates, integration tests, and approvals pass.
22. **Existing merge strategy:** Factory preserves the repository's approved merge strategy unless the project explicitly changes it.
23. **Release identity:** Release tags identify the exact verified commit and applicable artifact integrity hashes.
24. **Conditional advanced Git features:** Submodules, Git LFS, and multi-repository dependency handling are supported only when detected or required by the project.
25. **Destructive repository actions:** Factory never automatically deletes a repository, remote branch, tag, or release. Destructive operations require explicit approval.

## 3. Binding repository-governance clarifications

### 3.1 Branch hierarchy

Factory uses this hierarchy:

1. Every executable task receives a controlled task branch from an approved baseline.
2. A stage integration branch is optional and is created only when multiple independently verified task branches must be combined before protected promotion.
3. Separate lane branches and worktrees exist only for approved parallel work with explicit ownership boundaries.
4. Shared integration changes are serialized through the approved integration process.

A stage branch never replaces task-level ownership, evidence, or checkpoint requirements.

### 3.2 Local and offline protected-ref enforcement

Factory's Promotion Service is the only component permitted to update a protected ref locally or remotely.

- Normal workstreams receive no writable protected-branch checkout.
- Local merges and offline promotions must pass the same gates as remote pull requests.
- Offline promotions are recorded locally with complete evidence and synchronize later when approved network access returns.
- Direct ref mutation outside the Promotion Service is rejected when possible and always recorded as a security event.
- GitHub branch protection remains an additional remote control, not the sole enforcement mechanism.

### 3.3 Versioned multi-repository baseline

Every multi-repository Factory project uses a versioned Project Baseline Manifest containing at least:

- Project ID and primary repository;
- each repository's canonical identity and approved commit;
- dependency relationships and ordering;
- required submodules and Git LFS objects;
- compatible version constraints;
- release artifact hashes when applicable;
- whether repositories promote independently or atomically.

A combined project, integration package, or release cannot be verified solely because each repository passes independently. The declared cross-repository compatibility and promotion mode must also pass.

### 3.4 Standardized commit metadata

Factory-generated commits use standardized Git trailers when applicable, including:

```text
Factory-Task: <task-id>
Factory-Stage: <stage-id>
Factory-Workstream: <workstream-id>
Factory-Checkpoint: <checkpoint-id>
Verification-Status: <status>
```

Trailer values must agree with authoritative task and evidence records. Commit messages do not replace those records.

## 4. Operating boundaries

- GitHub remains the primary remote protection layer, while Factory enforces protected refs locally through the Promotion Service.
- Automatic commits are limited to controlled task branches and verified checkpoints.
- Stage integration branches are optional and never replace task branches.
- Pull-request creation may be automated; protected promotion, merge, history rewriting, and destructive operations remain gated.
- Factory project records reference repository history rather than duplicating it.
- Multi-repository verification uses one versioned Project Baseline Manifest.

## 5. Acceptance criteria

This decision is satisfied only when tests prove that:

1. every managed code project has an identified Git repository and approved baseline;
2. every executable code-changing task receives its own controlled task branch;
3. a stage integration branch is created only for integration of multiple independently verified task branches;
4. code-changing tasks cannot write directly to protected branches, protected refs, or original host workspaces;
5. protected refs can change only through the Promotion Service;
6. local offline promotions enforce the same verification and approval gates as remote pull requests;
7. direct protected-ref mutation outside the Promotion Service is rejected or detected and recorded as a security event;
8. unexplained local changes block normal task start;
9. imported local changes require explicit scope and ownership confirmation;
10. task branches, worktrees, commits, pull requests, evidence, promotions, and releases remain traceably linked;
11. automatic commits occur only on controlled task branches;
12. Factory commit trailers match authoritative task and verification records;
13. force-push and history rewriting cannot occur without high-risk approval;
14. pull requests and equivalent offline promotions cannot advance before required verification, evidence, integration, and approvals pass;
15. a multi-repository Project Baseline Manifest identifies exact compatible repository states and promotion behavior;
16. an incompatible multi-repository combination cannot receive a passing integration or release verdict;
17. release tags identify the exact verified commits and artifacts;
18. repository, branch, tag, and release deletion cannot occur automatically.