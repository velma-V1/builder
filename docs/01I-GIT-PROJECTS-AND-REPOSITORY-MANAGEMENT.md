# Approved Git, Projects, and Repository Management Decision

**Status:** Approved architecture supplement  
**Recorded:** July 23, 2026

## 1. Governing repository boundary

GitHub remains the primary protection and history layer for project repositories. Factory uses Git for traceability, controlled task branches, verified checkpoints, review, promotion, release identity, and rollback without duplicating committed project history in Factory memory.

Protected branches and original host workspaces are not direct work areas. Code-changing work occurs in controlled workspaces and enters protected project state only through the approved verification, evidence, review, and promotion process.

## 2. Approved Stage 7 decisions

1. **Factory project record:** Every project has a Factory project record linking repositories, tasks, requirements, evidence, releases, and approved project metadata.
2. **Git requirement:** Every code project managed by Factory uses Git for traceability, comparison, checkpointing, and rollback.
3. **Multiple repositories:** One Factory project may contain multiple repositories when the system legitimately spans them.
4. **Primary repository:** Every multi-repository project identifies one primary repository or governing baseline.
5. **Controlled workspace:** Existing repositories are cloned or materialized into controlled Factory workspaces rather than edited in their original host location.
6. **Trust classification:** Imported repositories receive a trust classification that governs isolation, execution, network, credentials, mounts, and promotion.
7. **Protected branches:** Protected branches remain read-only to workstreams and cannot be modified directly.
8. **Approved baseline:** Every task branch starts from an identified approved baseline commit.
9. **Traceable branch names:** Branch names include sufficient project, task, or stage identity for ownership and audit traceability.
10. **Unexplained local changes:** Factory refuses to begin normal work when unexplained local changes exist in the selected workspace.
11. **Importing existing changes:** Existing local changes may be imported into a task only after explicit scope confirmation, ownership assignment, and baseline recording.
12. **Remote synchronization:** Factory synchronizes with the approved remote before task-branch creation when task-scoped network access is available and synchronization is required.
13. **No automatic force-push:** Factory never force-pushes automatically.
14. **History rewriting:** Rebase, reset, force-push, or other history rewriting requires explicit high-risk approval and retained evidence.
15. **Commit traceability:** Factory commits include Task ID, stage or workstream identity, purpose, and verification or checkpoint status.
16. **Coherent commits:** Factory does not commit every small edit. Commits represent coherent verified checkpoints or completed units of work.
17. **Checkpoint commits:** Factory may automatically create verified checkpoint commits on controlled task branches.
18. **Controlled promotion:** Promotion to a protected branch requires a pull request or equivalent controlled review boundary.
19. **Automatic pull-request creation:** Factory may create a pull request automatically after the user approves the scope and applicable verification gates pass.
20. **Pull-request evidence:** Pull requests include requirements, changed scope, test results, evidence, known risks, limitations, and rollback information.
21. **Merge gates:** Merge is blocked until required checks, evidence, dependency gates, integration tests, and approvals pass.
22. **Existing merge strategy:** Factory preserves the repository's approved merge strategy unless the project explicitly changes it.
23. **Release identity:** Release tags identify the exact verified commit and applicable artifact integrity hashes.
24. **Conditional advanced Git features:** Submodules, Git LFS, and multi-repository dependency handling are supported only when detected or required by the project.
25. **Destructive repository actions:** Factory never automatically deletes a repository, remote branch, tag, or release. Destructive operations require explicit approval.

## 3. Operating boundaries

- GitHub remains primary, while Factory uses standard Git abstractions where practical so non-GitHub remotes can be supported.
- Automatic commits are limited to controlled task branches and verified checkpoints.
- Pull-request creation may be automated; merge and destructive operations remain gated.
- History rewriting and deletion always require explicit approval.
- Factory project records reference repository history rather than duplicating it.

## 4. Acceptance criteria

This decision is satisfied only when tests prove that:

1. every managed code project has an identified Git repository and approved baseline;
2. code-changing tasks cannot write directly to protected branches or original host workspaces;
3. unexplained local changes block normal task start;
4. imported local changes require explicit scope and ownership confirmation;
5. task branches, commits, pull requests, evidence, and releases remain traceably linked;
6. automatic commits occur only on controlled task branches;
7. force-push and history rewriting cannot occur without high-risk approval;
8. pull requests cannot merge before required verification, evidence, and approvals pass;
9. release tags identify the exact verified commit and artifacts;
10. repository, branch, tag, and release deletion cannot occur automatically.