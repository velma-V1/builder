# Approved Repository Intelligence and Graph Mapping Decision

**Status:** Approved architecture supplement  
**Recorded:** July 23, 2026

## 1. Governing graph boundary

Factory uses local, derived, rebuildable repository-intelligence indexes to support navigation, impact analysis, traceability, planning, verification, and graph visualization. Git repositories, approved contracts, project records, tests, and evidence remain authoritative. Graph output can inform work but cannot grant permission, replace deterministic evidence, or authorize changes.

Static, runtime, declared, proposed, and inferred relationships must remain distinguishable. Models receive bounded task-relevant graph slices rather than unrestricted graph dumps. Every published index is tied to an exact, stable source state and exposes its completeness, freshness, schema, parser, and provenance status.

## 2. Approved Stage 13 decisions

1. **Project indexing:** Every imported project receives a repository-intelligence index.
2. **Fast initial scan:** Initial indexing begins with a bounded structural scan before deeper analysis.
3. **Incremental deep analysis:** Deeper semantic analysis runs incrementally and on demand.
4. **Exact source identity:** Every index is tied to an exact commit, approved snapshot, or deterministically identified content state.
5. **Targeted invalidation:** Changed files invalidate only affected graph regions when deterministic impact boundaries are known.
6. **Broader rebuild on uncertainty:** Uncertain dependency impact triggers broader re-indexing.
7. **Modular language adapters:** Language support uses replaceable parser and semantic-analysis adapters.
8. **Semantic-source preference:** Factory prefers AST, compiler, language-server, symbol-index, or equivalent semantic data over text matching.
9. **Bounded heuristics:** Text heuristics may be used when semantic parsing is unavailable, but findings are labeled lower-confidence.
10. **Edge provenance:** Every graph relationship records its source, extraction method, adapter, source state, and evidence class.
11. **Relationship classes:** Graph edges distinguish at least `STATIC`, `RUNTIME`, `DECLARED`, and `INFERRED` relationships.
12. **No inferred authority:** Inferred relationships are not authoritative until independently supported.
13. **Confidence and freshness:** Graph nodes and edges expose confidence and freshness status where applicable.
14. **Source graph coverage:** The source graph maps files, symbols, imports, calls, dependencies, tests, configurations, data flows, and change impact when supported.
15. **Requirement-code linkage:** Requirements and acceptance criteria may link to relevant code and tests.
16. **Test traceability:** Tests may link to the code and requirements they verify.
17. **No name-similarity proof:** Similar names alone cannot prove a requirement-code-test relationship.
18. **Suggested links:** Factory may propose likely traceability links as unverified suggestions.
19. **Cycle detection:** Dependency and execution cycles are detected and displayed.
20. **Candidate dead-code findings:** Unused or unreachable code findings remain candidates until verified.
21. **File classification:** Generated, vendor, dependency, cache, and build-output files are classified separately.
22. **Bounded third-party indexing:** Third-party and generated directories receive metadata-first indexing and deeper analysis only when relevant.
23. **Binary handling:** Binary files receive structural metadata rather than guessed source analysis.
24. **Archive safety:** Archives remain unopened by default and require relevance and path-safety checks before extraction.
25. **Chunked large-repository indexing:** Large repositories are indexed in resource-bounded chunks.
26. **Task-relevant priority:** Indexing prioritizes task-relevant and recently changed paths.
27. **Operator pins:** The operator may pin important files, folders, components, symbols, or graph regions.
28. **No authority from priority:** Pinning affects priority only and never grants permission or authority.
29. **Bounded model graph context:** Models receive task-specific graph slices instead of the full graph.
30. **Controlled expansion:** Graph retrieval may expand outward by dependency relevance when necessary.
31. **Query source disclosure:** Every graph query reports indexed source state, freshness, completeness, and schema identity.
32. **Pre-change impact analysis:** Factory performs applicable change-impact analysis before code-changing work.
33. **No impact-analysis authorization:** Graph impact analysis informs scope but cannot authorize edits.
34. **Before-and-after comparison:** Significant changes compare graph state before and after implementation.
35. **Structural-diff report:** Architecture changes produce an explicit structural-diff report.
36. **Meaningful snapshot retention:** Graph versions are retained for meaningful checkpoints, commits, and verified baselines rather than every editor save.
37. **Verified graph snapshots:** Graph snapshots correspond to verified checkpoints and releases.
38. **Multi-repository relationships:** Cross-repository relationships are supported inside approved multi-repository projects.
39. **No automatic cross-project linking:** Cross-project graph relationships are not created automatically.
40. **External reusable references:** Approved reusable global tools and libraries may appear as external references without copying project data.
41. **Authoritative live graph:** The live-execution graph is built from authoritative task, state, and event records.
42. **Selective runtime tracing:** Runtime tracing is enabled when required for debugging, verification, or analysis rather than continuously for every task.
43. **Static-runtime separation:** Runtime relationships remain separate from static relationships.
44. **Architecture status classes:** Architecture graph components distinguish `APPROVED`, `IMPLEMENTED`, `OBSERVED`, and `PROPOSED` states.
45. **Workflow visibility:** Agent-workflow graphs show handoffs, approvals, retries, failures, recovery, and evidence gates.
46. **Manual annotations:** Operators may add graph annotations.
47. **Annotation separation:** Annotations are stored separately with author, provenance, scope, and timestamp and do not rewrite derived facts.
48. **Conflict visibility:** Conflicting annotations and derived findings remain visible until resolved.
49. **No automatic code action:** Graph findings cannot automatically trigger code changes.
50. **Proposal generation:** Graph findings may generate proposed tasks or Improvement Packets through the normal approval workflow.
51. **Explicit unresolved references:** Unresolved symbols, imports, calls, references, and dependency identities are reported explicitly.
52. **Integrity-dependent high-risk work:** Graph integrity failure blocks graph-dependent high-risk work.
53. **Automatic derived-index rebuild:** Corrupted derived indexes may be rebuilt automatically.
54. **Source-authority protection:** Index rebuilds never overwrite authoritative project records.
55. **Graph integrity testing:** Integrity tests verify node identity, edge references, source-state identity, provenance, schema compatibility, and deterministic rebuild consistency.
56. **Resource limits:** Indexing has CPU, RAM, disk, time, process, and concurrency limits.
57. **Priority-aware pausing:** Low-priority indexing may pause during active model, build, verification, or release work.
58. **Portable exports:** Graph exports use documented standard formats where practical.
59. **No default external upload:** Repository graph data remains local and is not uploaded externally by default.
60. **Release alignment:** Release graph indexes and architecture maps must match the exact verified source commit or approved source state.

## 3. Six binding graph-integrity clarifications

### 3.1 Deterministic node identity

Graph node identity must use documented deterministic identifiers derived from repository identity, source state, path, symbol scope, language adapter, and symbol type.

The identity design must explicitly handle:

- file renames;
- symbol moves;
- duplicate symbol names;
- generated files;
- branch and source-state changes;
- cross-repository references.

Rename or move continuity may be recorded as a separate evidence-backed relationship, but Factory must not silently reuse the prior node identity without evidence.

### 3.2 Graph schema versioning

Every graph index and snapshot records:

- graph-schema version;
- parser and semantic-adapter versions;
- extraction configuration;
- Factory version;
- source-state identity.

An incompatible index must be migrated deterministically or rebuilt before use. Old indexes cannot appear current under incompatible graph code.

### 3.3 Mixed-state prevention

Each indexing operation must use a stable source snapshot or detect source changes before publication. An index assembled from inconsistent working-tree, branch, or repository states cannot be marked `CURRENT` or `COMPLETE`.

### 3.4 Isolated semantic tooling

Repository parsers, compilers, language servers, build analyzers, plugins, and related tooling must run with task-scoped permissions inside resource-limited isolation whenever they can execute project-controlled code, load untrusted extensions, evaluate configuration, invoke build hooks, or access external resources.

### 3.5 Graph operating states

Every graph exposes one explicit state:

```text
COMPLETE
PARTIAL
STALE
UNSUPPORTED
CORRUPT
REBUILDING
```

`PARTIAL` or `UNSUPPORTED` graphs may assist low-risk navigation but cannot be presented as complete dependency coverage. `STALE`, `CORRUPT`, or `REBUILDING` graphs cannot support graph-dependent high-risk decisions.

### 3.6 Verified traceability promotion

A requirement-code-test relationship becomes `VERIFIED` only through one or more of:

- explicit approved project metadata;
- deterministic instrumentation;
- approved recorded manual confirmation;
- reproducible test evidence.

Model inference, naming similarity, proximity, or graph heuristics alone cannot promote traceability to `VERIFIED`.

## 4. Operating boundaries

- Semantic parsing is preferred; heuristics remain clearly lower-confidence.
- Graphs analyze project state but never replace Git, contracts, tests, evidence, permissions, or approvals.
- Static, runtime, declared, proposed, and inferred relationships remain distinguishable.
- Graph findings may propose work but cannot initiate unauthorized changes.
- Derived indexes are local, rebuildable, schema-versioned, resource-limited, and tied to stable exact source states.
- Unsupported or partial coverage must never be described as complete.

## 5. Acceptance criteria

This decision is satisfied only when tests prove that:

1. indexes are deterministically tied to stable source states;
2. graph node identity behaves predictably across renames, moves, duplicate names, branches, generated files, and cross-repository references;
3. incompatible schemas and adapters trigger deterministic migration or rebuild;
4. mixed-state indexes cannot be published as current;
5. executable semantic tooling remains isolated and permission-controlled;
6. graph states and coverage limitations are visible and enforced;
7. traceability cannot become verified through model inference alone;
8. graph integrity failure blocks applicable high-risk work;
9. rebuilding a derived index never changes authoritative project records;
10. release graph artifacts match the exact verified source state.