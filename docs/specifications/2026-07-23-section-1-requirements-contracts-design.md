# Section 1 Design — Requirements and Contracts

**Status:** Proposed for user approval  
**Date:** July 23, 2026  
**Scope:** Factory Build Section 1 only  
**Governing sources:** `PROJECT_DEFINITION.md`, `docs/01-APPROVED-DECISIONS.md`, and `docs/02-FACTORY-ARCHITECTURE.md`

## 1. Purpose

Section 1 creates the contract system that tells the Factory exactly:

- what project is being built;
- what requirements must be satisfied;
- what one task may do;
- which files and interfaces it owns;
- which actions are automatic or approval-gated;
- what evidence proves completion;
- how approved scope changes are recorded.

The design must keep work moving automatically whenever safety can be proven. It must prevent a lane from deleting, overwriting, expanding authority, or changing another component without detection and control.

## 2. Design principles

1. **Automatic inside proven boundaries.** Safe, bounded, reversible work proceeds without human interruption.
2. **Strict only where authority is granted.** Identity, paths, permissions, limits, dependencies, state, and completion are deterministic.
3. **Flexible where engineering intent is expressed.** Goals, notes, rationale, and implementation guidance may use natural language.
4. **No model self-certification.** Models propose and perform work; deterministic validation and evidence gates decide whether it is accepted.
5. **Contracts are code.** Human-authored contracts are versioned, reviewable, schema-validated repository files.
6. **Activated versions are immutable.** Changes create new versions through Change Contracts.
7. **Live state is not stored in contract files.** High-frequency state belongs in the transactional runtime database.
8. **Fail closed at trust boundaries, not on every read.** Full validation occurs at ingestion boundaries; runtime reads use validated canonical data.
9. **Previous states remain recoverable.** Every activation preserves the previous version, hash, generation, evidence, and rollback reference.

## 3. Architecture

```text
Human or model-authored YAML contract
                |
                v
Safe YAML parser
                |
                v
JSON Schema structural validation
                |
                v
Semantic and cross-contract validation
                |
                v
Canonical JSON + SHA-256 content hash
                |
                v
Policy and impact gate
       +--------+---------+
       |                  |
       v                  v
Automatic safe       Protected or
activation           ambiguous change
       |                  |
       |              Human decision
       +--------+---------+
                |
                v
Watchdog assigns activation generation
                |
                v
SQLite activation record + immutable cache
                |
                v
Watchdog, lanes, tools, and dashboard read
validated canonical contracts
```

## 4. Contract family

Section 1 defines seven linked contract families.

### 4.1 Project Contract

Defines project identity and the approved top-level boundary.

Must include:

- project ID and name;
- contract version and schema version;
- project root and repository identity;
- project type and intended deliverables;
- approved operating environments;
- high-level goals and explicit exclusions;
- protected branches and protected path classes;
- privacy and cloud-use default;
- system-wide resource ceilings;
- source, provenance, status, and related contract references.

The Project Contract cannot grant a task access to paths outside the project root.

### 4.2 Requirement Contract

Defines one independently traceable requirement.

Must include:

- requirement ID and version;
- owning project ID;
- source and rationale;
- requirement statement;
- measurable acceptance criteria;
- dependencies and affected requirement references;
- priority and criticality;
- evidence categories required;
- permitted limitations, when explicitly approved;
- status and supersession history.

Acceptance criteria may contain readable natural language but must identify objective evidence whenever deterministic verification is possible.

### 4.3 Task Contract

Defines one bounded unit of execution.

Must include:

- task ID and version;
- project and parent requirement IDs;
- objective and deliverables;
- linked Ownership, Permission, and Evidence Contract IDs;
- frozen interfaces and dependency references;
- permitted abstract model routes;
- resource, request, token, retry, and time ceilings;
- execution environment class;
- checkpoint requirements;
- recovery and escalation behavior;
- completion conditions;
- current contract status.

A Task Contract does not directly assign a live lane or current model. Those are runtime-state decisions stored in SQLite.

### 4.4 Ownership Contract

Defines the task's exact file and interface boundary.

Must include:

- ownership contract ID and version;
- project and task IDs;
- allowed paths;
- forbidden paths;
- protected path classifications;
- read-only paths;
- shared interfaces consumed or provided;
- expected generated and disposable artifacts;
- overlap policy;
- ownership lease requirements;
- path normalization policy.

Rules:

- path patterns are repository-relative and normalized;
- traversal outside the project root is denied;
- symlinks, junctions, reparse points, case differences, and Windows path behavior must be resolved before authority is granted;
- allowed paths cannot override forbidden or protected paths;
- another active task's exclusive ownership prevents concurrent writes;
- shared interface changes enter serialized impact handling.

### 4.5 Permission Contract

Defines what the task may do automatically and what requires approval.

Must include:

- permission contract ID and version;
- project and task IDs;
- permitted tools and command classes;
- network and cloud permissions;
- secret, device, process, mount, and environment permissions;
- file-operation permissions;
- dependency-installation boundary;
- approval-required actions;
- denied actions;
- expiration and revocation behavior.

Default automatic actions inside an approved disposable sandbox:

- create files in owned paths;
- edit files in owned paths;
- install task-required dependencies inside the disposable environment;
- run approved commands and tests;
- create automatic checkpoint commits on the isolated branch;
- rebuild validated contract caches;
- recover and restart from a verified checkpoint.

Automatic deletion is permitted only when the artifact is:

- explicitly classified as disposable by contract;
- created by the current task or generated inside its disposable environment;
- inside the task's owned paths;
- not referenced by another active component;
- covered by a verified rollback or recreation path.

Human approval is required for deletion of pre-existing source, tests, decisions, contracts, schemas, shared files, user-authored material, or anything outside that narrow disposable class.

### 4.6 Evidence Contract

Defines exactly what must pass before a task can be complete.

Must include:

- evidence contract ID and version;
- project, task, and requirement IDs;
- required deliverables;
- required test categories and commands or command references;
- required environment identity;
- scope and path checks;
- failure-path, regression, security, visual, installation, launch, packaging, or documentation checks when applicable;
- Worker and Reviewer record requirements;
- exact artifacts and retention rules;
- completion formula;
- permitted limitations and their required disclosure.

A task enters `COMPLETE` only when every applicable requirement and evidence gate passes and no required approval remains outstanding.

### 4.7 Change Contract

Defines a proposed revision to an activated contract or approved scope.

Must include:

- change ID and version;
- project ID;
- target contract ID and target version;
- reason and source;
- exact proposed difference;
- affected requirements, tasks, paths, interfaces, permissions, tests, and components;
- compatibility classification;
- protected-boundary classification;
- impact-analysis result;
- evidence required before activation;
- rollback target;
- approval requirement and decision record;
- resulting contract version reference after activation.

An approved Change Contract creates a new immutable contract version. It never mutates the activated version in place.

## 5. Common contract envelope

Every YAML contract shares a strict common envelope:

- `contract_type`;
- `id`;
- `version`;
- `schema_version`;
- `project_id`;
- `status`;
- `source` and provenance;
- `created_at` and `created_by`;
- related contract references;
- supersedes or superseded-by references when applicable.

The editable YAML does not contain authoritative runtime generation or canonical content hash. The Watchdog records those during activation.

## 6. Status model

Contract-file statuses:

- `DRAFT` — editable and not usable for execution;
- `VALIDATED` — structurally and semantically valid but not active;
- `APPROVAL_REQUIRED` — crosses a protected boundary;
- `APPROVED` — eligible for Watchdog activation;
- `SUPERSEDED` — replaced by a newer activated version;
- `REJECTED` — denied with a recorded reason;
- `RETIRED` — intentionally removed from future use while history remains.

Runtime activation state and task-execution state are stored separately in SQLite. A YAML status cannot directly force an authoritative runtime transition.

## 7. Pragmatic validation pipeline

### 7.1 Full validation boundaries

Full ingestion runs when a contract is:

- created or saved;
- imported from another repository or source;
- checked out or merged from another branch;
- restored from backup;
- migrated to another schema version;
- loaded at startup when no trusted matching activation exists;
- re-ingested after integrity failure or cache quarantine.

### 7.2 Structural validation

The Factory must:

- use a safe YAML loader;
- reject duplicate keys;
- disable executable custom tags;
- bound aliases and nested structures;
- validate against the exact versioned JSON Schema;
- reject malformed identifiers and unsupported schema versions;
- reject unknown authority fields;
- normalize approved scalar types and defaults.

Descriptive intent fields may remain flexible strings or bounded structured maps. Authority fields remain strongly typed.

### 7.3 Semantic validation

The Factory must verify at least:

- referenced contracts exist and belong to the same project where required;
- version and supersession relationships are legal;
- permitted route identities exist in the approved routing registry;
- cloud routes are allowed by project and task privacy policy;
- paths normalize inside the project root;
- allowed, forbidden, protected, read-only, and active ownership rules do not conflict;
- shared interfaces and dependency directions are known;
- resource limits do not exceed project or Factory ceilings;
- evidence requirements are valid and reachable;
- status transitions are legal;
- a new version cannot silently reduce required evidence or expand authority.

### 7.4 Canonical serialization

After validation, the Factory:

1. normalizes the contract;
2. creates canonical JSON using deterministic field and scalar rules;
3. computes a SHA-256 hash over the canonical bytes;
4. records the validated representation and validation report;
5. supplies only canonical validated data to runtime consumers.

YAML comments, whitespace, and key order do not affect identity. Canonical JSON is generated and is not independently edited.

## 8. Runtime cache and integrity

The contract service publishes immutable, replace-only cache entries.

Each active entry includes:

- contract ID and contract version;
- project ID;
- schema version;
- activation generation;
- canonical content hash;
- enabled and activation status;
- immutable canonical JSON reference.

Normal runtime reads do not reparse YAML or rerun JSON Schema.

A runtime request performs a cheap check that:

- the entry is enabled and active;
- ID, project, version, schema version, generation, and expected hash match the authoritative SQLite activation record.

A mismatch quarantines only the affected cache entry and triggers isolated re-ingestion. Periodic or suspicious-state integrity checks may recompute the canonical hash outside the critical execution path.

## 9. Activation and generation

The Watchdog is the sole authority that activates a validated contract version.

Activation occurs transactionally:

1. verify expected current activation state;
2. verify validation and impact evidence;
3. confirm required approval or automatic-policy eligibility;
4. assign the next project activation generation;
5. store version, hash, generation, status, evidence, and rollback reference;
6. append the audit event;
7. atomically publish the immutable cache entry.

Generation changes only on authoritative activation, replacement, disablement, or rollback. Parsing, startup, cache rebuilding, or re-ingestion does not increment it.

## 10. Automatic-change policy

The Watchdog may automatically activate a new version when it proves all of the following:

- the change stays within owned authority;
- no protected material is deleted or replaced;
- no unresolved ownership conflict exists;
- dependent interfaces remain compatible, or affected work is safely serialized and verified;
- architecture, security, privacy, and intended product behavior remain unchanged;
- required tests and impact evidence pass;
- a verified rollback target exists;
- the change is reversible and does not expand authority;
- no required human decision remains.

A cross-component effect does not automatically require human approval. The Factory first:

1. identifies affected components through contracts, imports, schemas, tests, and dependency graphs;
2. pauses only conflicting work;
3. creates linked impact tasks;
4. serializes shared changes;
5. runs integration and regression evidence;
6. continues automatically when compatibility is proven.

## 11. Protected decision policy

Human approval is required when the Factory cannot deterministically prove safe compatibility or when the proposed change:

- deletes or replaces protected or pre-existing material;
- changes intended product behavior where requirements are ambiguous;
- modifies another task's exclusive ownership;
- introduces an unresolved breaking shared-interface change;
- changes approved architecture, security, permissions, privacy, or cloud policy;
- expands authority or weakens required evidence;
- installs persistent host software or changes the host system;
- sends private project material to a cloud provider without existing permission;
- merges into `main` or another protected branch;
- publishes, releases, or spends money.

Security violations are denied and audited rather than presented as ordinary approval requests.

## 12. Runtime-state boundary

Contracts define approved intent and authority. SQLite stores live execution state.

The runtime database stores:

- active contract versions, hashes, and generations;
- task and lane state;
- queue and dependency readiness;
- ownership leases and heartbeats;
- current model route assignments;
- request, token, quota, and retry counters;
- approvals and checkpoint references;
- append-only events;
- failures, recoveries, and integration state.

The Watchdog is the sole authoritative writer. Other components submit validated commands or events through controlled interfaces.

SQLite uses WAL mode, foreign-key enforcement, explicit transactions, migrations, integrity checks, and controlled backups. A storage abstraction keeps control logic independent of SQLite-specific calls.

## 13. Error handling

Contract errors produce explicit classifications:

- `PARSE_REJECTED`;
- `SCHEMA_REJECTED`;
- `REFERENCE_REJECTED`;
- `SEMANTIC_REJECTED`;
- `AUTHORITY_CONFLICT`;
- `IMPACT_UNPROVEN`;
- `APPROVAL_REQUIRED`;
- `CACHE_QUARANTINED`;
- `ACTIVATION_ROLLED_BACK`.

Invalid contracts cannot create tasks, grant permissions, assign lanes, or start execution.

A failed activation transaction leaves the prior activation and cache entry unchanged. Failure records and evidence remain available.

## 14. Security requirements

Section 1 must defend against:

- malicious or malformed YAML;
- duplicate-key ambiguity;
- unsafe YAML tags and alias expansion;
- path traversal and Windows path-prefix errors;
- symlink, junction, and reparse-point escapes;
- case and separator inconsistencies;
- stale cache use;
- unsupported schema downgrade;
- cross-project reference injection;
- unapproved route identities;
- authority expansion through new contract versions;
- test or evidence weakening;
- direct lane mutation of authoritative state;
- time-of-check/time-of-use gaps between policy decisions and file operations.

The implementation plan must define deterministic tests for each applicable threat.

## 15. Repository layout

```text
contracts/
├── projects/
├── requirements/
├── tasks/
├── ownership/
├── permissions/
├── evidence/
└── changes/

schemas/
├── contracts/
│   ├── project/
│   ├── requirement/
│   ├── task/
│   ├── ownership/
│   ├── permission/
│   ├── evidence/
│   └── change/
└── common/

src/factory/contracts/
├── parsing/
├── validation/
├── canonicalization/
├── references/
├── impact/
├── policy/
├── activation/
├── cache/
└── repository/

tests/contracts/
├── unit/
├── integration/
├── security/
├── failure_paths/
└── fixtures/
```

These paths define the intended Section 1 boundary; exact implementation files are created by the implementation plan after this design is approved.

## 16. Section 1 task decomposition

### Task 1 — Common envelope and seven JSON Schemas

Deliver:

- common definitions;
- seven versioned schemas;
- valid and invalid fixtures;
- schema compatibility rules.

### Task 2 — Safe ingestion and canonicalization

Deliver:

- safe YAML parsing contract;
- structural validation;
- canonical JSON rules;
- deterministic hashing;
- ingestion reports.

### Task 3 — Semantic, reference, and impact validation

Deliver:

- cross-contract resolution;
- project and version checks;
- path and ownership validation;
- routing and resource validation;
- dependency and interface impact results.

### Task 4 — Policy, change, activation, and cache contracts

Deliver:

- automatic-versus-protected decision policy;
- immutable revision flow;
- Watchdog activation interface;
- generation and cache integrity rules;
- rollback behavior.

### Task 5 — Verification package

Deliver:

- unit, integration, security, and failure-path tests;
- requirement-to-test traceability;
- exact evidence report;
- documentation and handoff into Section 2.

## 17. Acceptance criteria

Section 1 is complete only when evidence proves that:

1. all seven contract types have versioned schemas and fixtures;
2. valid YAML becomes deterministic canonical JSON with a stable SHA-256 hash;
3. invalid, ambiguous, malicious, stale, or cross-project contracts fail closed;
4. semantic validation detects missing references, invalid routes, ownership conflict, authority expansion, and evidence weakening;
5. activated contract versions cannot be edited in place;
6. safe bounded revisions can create and activate new versions without human interruption;
7. protected or ambiguous changes pause for human decision;
8. runtime reads use immutable canonical cache entries and detect stale or mismatched generations;
9. failed activation leaves the previous active version intact;
10. lanes cannot directly alter authoritative contract or activation state;
11. deletion policy protects pre-existing, shared, test, contract, decision, schema, and user-authored files;
12. all defined unit, integration, security, and failure-path tests pass in the approved Windows 11 Home development path;
13. every claim in the completion report is classified and supported by retained evidence.

## 18. Non-goals

Section 1 does not implement:

- the complete runtime task queue;
- the full state-machine engine;
- the continuous Watchdog loop;
- provider adapters or token accounting;
- Git worktree automation;
- Docker lifecycle management;
- the three active Worker–Reviewer lanes;
- the dashboard or installer.

It defines the contracts and interfaces those later sections must consume.

## 19. Design result

This design keeps the Factory permissive enough to work continuously while making destructive, cross-boundary, authority-changing, and completion decisions deterministic and auditable.

The core rule is:

> Automatically continue when the Factory can prove that a change is owned, bounded, reversible, non-destructive, and compatible. Serialize and verify cross-component effects. Ask the user only when a protected decision remains.