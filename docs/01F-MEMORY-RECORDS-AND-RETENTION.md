# Approved Memory, Records, and Retention Decision

**Status:** Approved architecture supplement  
**Recorded:** July 23, 2026

## 1. Governing memory boundary

Factory separates temporary task context, project-scoped permanent records, approved user preferences, reusable global engineering knowledge, raw session records, and derived indexes.

Only verified evidence, approved decisions, approved outcomes, and explicitly promoted reusable lessons may become authoritative long-term memory. Model conversations, drafts, guesses, abandoned plans, and unverified claims do not become permanent memory automatically.

GitHub remains the source of truth for committed project source and history. Factory memory stores the minimum authoritative requirements, decisions, evidence links, lessons, task state, and retrieval metadata needed to operate safely without duplicating repository history.

## 2. Approved Stage 4 decisions

1. **Temporary and permanent separation:** Factory must separate temporary task context from long-term memory.
2. **Conversation handling:** Model prompts, responses, and conversations do not automatically enter permanent memory.
3. **Verified project decisions:** Approved project decisions become permanent, versioned, searchable records.
4. **Preference separation:** Approved user preferences are stored separately from project facts, requirements, and engineering evidence.
5. **Provenance:** Every permanent memory record includes its source, status, scope, timestamps, authority, and supporting evidence or approved decision reference.
6. **Record status:** Permanent records support at least `PROPOSED`, `VERIFIED`, `SUPERSEDED`, `REFUTED`, and `ARCHIVED` states.
7. **Conflict history:** Later approved decisions do not delete older conflicting decisions. Older records are marked `SUPERSEDED` and remain traceable.
8. **Conflict resolution:** Factory may resolve conflicting records only through deterministic authority, recency, scope, and supersession rules. Models may identify conflicts but cannot choose authority by guessing.
9. **Versioned correction:** Permanent authoritative records are not silently edited in place. Corrections create a new version linked to the prior record and preserve the audit trail.
10. **Task-context disposal:** Temporary task memory is deleted after task closure only after required evidence, approved outputs, checkpoints, and reusable verified lessons are extracted and secured.
11. **Raw model records:** Complete prompts and model responses follow the approved raw-session retention policy unless a valid hold requires longer preservation.
12. **Reusable lessons:** Verified reusable lessons remain after eligible raw logs are deleted.
13. **Project namespaces:** Each project has a separate memory namespace and retrieval boundary.
14. **Global engineering memory:** Factory may maintain a small global namespace containing verified, reusable engineering knowledge.
15. **Global promotion:** Project knowledge cannot enter global memory automatically. Promotion requires evidence of general applicability, conflict review, and user approval.
16. **Sensitive values:** Secrets, credentials, tokens, private keys, and protected values cannot be stored in memory. Memory may store only approved references to secure credential locations and non-secret metadata.
17. **Retrieval priority:** Current approved decisions and verified project requirements rank above superseded records, historical evidence, raw conversations, and unverified material.
18. **Dashboard provenance:** Retrieved memory shown in the Dashboard must expose its project or global scope, status, source, authority, evidence link, and supersession state.
19. **Duplicate detection:** Factory detects duplicate and near-duplicate records and presents their relationship without discarding provenance.
20. **Deterministic merging:** Duplicate records may merge automatically only when their meaning, scope, authority, status, and evidence are deterministically identical. Otherwise they remain separate and linked for review.
21. **Archived search:** Archived project records remain searchable under their project namespace and archive controls.
22. **Project deletion boundary:** Closing, archiving, or deleting a project does not automatically delete its permanent records. Record deletion requires a separate explicit decision and applicable retention checks.
23. **Project retention holds:** Factory supports project-specific investigation, recovery, audit, security, dispute, and user-requested retention holds.
24. **Integrity checks:** Factory periodically checks authoritative memory for corruption, missing evidence, broken references, invalid status transitions, namespace leakage, and supersession errors.
25. **Rebuildable indexes:** Search indexes, embeddings, caches, summaries, and other derived retrieval structures are rebuildable from authoritative records. Derived indexes are never the sole source of truth.

## 3. Memory classes

Factory uses the following logical classes:

- **Active task context:** temporary plans, current state, open dependencies, pending approvals, and checkpoint data required to continue a task.
- **Project authority records:** approved requirements, decisions, contracts, evidence summaries, releases, supersessions, and verified project lessons.
- **User preference records:** explicitly approved operator preferences that affect presentation or workflow but do not override project authority or safety rules.
- **Global verified knowledge:** approved reusable engineering lessons proven to apply beyond one project.
- **Raw session records:** prompts, responses, terminal logs, tool output, and execution records governed by the approved hot, cold, purge, and hold lifecycle.
- **Derived retrieval data:** indexes, embeddings, summaries, caches, and rankings that can be regenerated from authoritative records.

Records from one class cannot silently change class. Promotion into a more authoritative or broader scope requires the applicable verification and approval gate.

## 4. Authority and retrieval order

When retrieved records conflict, Factory applies this default order within the applicable scope:

1. current governing project definition and explicit approved decisions;
2. current verified requirements, contracts, and release records;
3. verified evidence summaries and accepted task outcomes;
4. verified reusable project lessons;
5. approved global engineering knowledge;
6. superseded, refuted, or archived historical records;
7. raw conversations, drafts, and unverified material.

Scope-specific authority takes precedence over broad general guidance. A global lesson cannot override a project's explicit approved requirement.

## 5. Retention relationship

Memory retention remains governed by record class:

- temporary task context is removed after safe closure and evidence extraction;
- raw session records follow the approved rolling retention lifecycle;
- verified decisions, structured evidence, supersession history, required audit records, approved lessons, holds, and Improvement Packet decisions follow their permanent or separately approved retention rules;
- derived indexes may be deleted and rebuilt without deleting authoritative records;
- project closure alone does not authorize deletion of permanent records.

## 6. Acceptance criteria

This decision is satisfied only when tests prove that:

1. temporary task context cannot be retrieved as authoritative permanent memory;
2. raw model conversations cannot become permanent records without an explicit verified promotion path;
3. every permanent record exposes source, scope, status, authority, and evidence or decision provenance;
4. user preferences cannot be mistaken for project facts or override governing requirements;
5. superseded and refuted records remain traceable but cannot rank as current authority;
6. conflicting records are resolved only by deterministic authority rules or explicit review;
7. corrections preserve prior versions and cannot silently rewrite history;
8. task context cannot be deleted before required evidence, outputs, checkpoints, and verified lessons are secured;
9. eligible raw prompts and responses follow the approved session-retention lifecycle;
10. verified reusable lessons survive deletion of eligible raw logs;
11. project memory cannot leak into another project's retrieval results;
12. project knowledge cannot enter global memory without evidence, conflict review, and approval;
13. secrets cannot be stored directly in memory or exposed through retrieval;
14. Dashboard retrieval displays provenance, scope, status, and supersession information;
15. duplicate detection preserves provenance and automatic merging occurs only for deterministically identical records;
16. archived project records remain searchable while protected by archive controls;
17. closing or deleting a project cannot silently delete permanent records;
18. valid project-specific retention holds block deletion;
19. integrity checks detect corruption, broken evidence links, invalid statuses, namespace leakage, and supersession errors;
20. all derived indexes can be rebuilt from authoritative records and cannot become the sole source of truth.