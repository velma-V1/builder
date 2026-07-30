# Contract Registry

**Status:** Derived/non-overriding reference (L25.D) — aggregates authoritative contract facts; never overrides a source
**Recorded:** July 24, 2026
**Sources:** Section 1 §4 (seven families), `02 §5`, and each supplement's manifests. In force with `01R` (R1–R5, Decisions A–C).

Regenerated when a contract is added or versioned. Shared-contract fields per `01D §3.2`.

## Shared policy defaults (per contract states only deltas)
- **VAL:** safe-YAML → JSON Schema Draft 2020-12 → semantic/reference → canonical JSON (RFC 8785) + SHA-256; fail closed at ingestion (Section 1 §7).
- **COMPAT:** additive/backward-compatible only without a major bump; authority-expansion or evidence-weakening flagged by the impact analyzer (`01G`, `01H`).
- **DEP:** deprecate via `SUPERSEDED` status + supersession link; prior version retained.
- **CHG:** immutable activated version; change = Change Contract → impact → policy → Orchestrator activation (Section 1 §4.7, `01 §17`); protected-boundary → approval.
- **MIG:** versioned `schema_version`; transactional SHA-verified runner (`01O §2.19`).
- **RB:** prior activated version + hash + generation retained; failed activation leaves prior active (Section 1 §9).
- **RT:** schema fixtures (valid/invalid) + canonicalization determinism + semantic/impact tests.

## Registry

Fields: ID · Owner (phase) · Ver · Producers · Consumers · Deltas.

| Contract ID | Owner (phase) | Ver | Producers | Consumers | Deltas |
|---|---|---|---|---|---|
| CTR-ENVELOPE | Contract system (PH-1) | v1 | contract authors | all schemas | strict envelope; unknown keys rejected |
| CTR-PROJECT | Contract system (PH-1) | v1 | operator/Factory | Orchestrator, all | cannot grant paths outside project root |
| CTR-REQUIREMENT | Contract system (PH-1) | v1 | requirements author | tasks, verification matrix, ETM | acceptance criteria carry evidence categories |
| CTR-TASK | Contract system (PH-1) | v1 | phase/task specs | Orchestrator, lanes, router | **risk_class required** (R5, `01M §3.11`); **autonomy level** (Dec A); links Ownership/Permission/Evidence |
| CTR-OWNERSHIP | Contract system (PH-1) | v1 | task specs | path authority, Git mgr | allowed cannot override forbidden/protected; path normalization |
| CTR-PERMISSION | Contract system (PH-1) | v1 | task specs | permission enforcement, brokers | **deletion approval-gated** (Dec B); autonomy envelope (Dec A) |
| CTR-EVIDENCE | Contract system (PH-1) | v1 | task specs | verification engine, ETM | **verdict enum = 01G five values** (R5); anti-weakening on change |
| CTR-CHANGE | Contract system (PH-1) | v1 | change authors | Orchestrator activation | JSON-Patch add/replace/remove only; new ver = target+1 |
| CTR-CANONICAL | Contract system (PH-1) | v1 | canonicalizer | hashing/cache/signing | RFC 8785 + SHA-256; identity stable across key-order/whitespace |
| CTR-ROUTE-REGISTRY | model router (PH-4)/config | v1 | config | router, semantic validation | abstract routes only; **no GLM-4.7** (`03 §6`); change = approval |
| CTR-RUNTIME-STATE-DB | Orchestrator (PH-2) | v1 | Orchestrator (sole) | read-only readers | SQLite WAL, FK, explicit tx; files not committed |
| CTR-ACTIVATION-STORE | Orchestrator (PH-2) | v1 | Orchestrator | ActivationReader, cache | append-only events; generation only on activation |
| CTR-TASK-WS-SM | Orchestrator (PH-2) | v1 | state-machine | task engine, Dashboard | legal-transition table (`01L §3.1`) |
| CTR-LANE-LIFECYCLE | workstream engine (PH-6) | v1 | lane SM | Orchestrator, Dashboard | consistent with CTR-TASK-WS-SM (`01D §3.1`) |
| CTR-LEASE-FENCING | Orchestrator (PH-2) | v1 | lease system | all lock holders | monotonic tokens; stale-owner write rejected |
| CTR-RECOVERY-JOURNAL | Orchestrator (PH-2) | v1 | Orchestrator | Watchdog, recovery | durable-flush-before-success; idempotent replay |
| CTR-MODEL-FINGERPRINT | model router (PH-4) | v1 | router | model-exec records, evidence | full fingerprint (`01J §3.1`); mutable tag insufficient |
| CTR-MODEL-EXEC-RECORD | model router (PH-4) | v1 | model calls | audit, evidence, quotas | append-only; fallback = new record |
| CTR-ETM | ETM system (PH-7) | v1 | verification engine | Promotion, evidence store | `01G §3.1`; broken link blocks promotion; protected component |
| CTR-EVIDENCE-PACKAGE | evidence store (PH-7) | v1 | verification | Promotion, release, checklist | `01G §6`; integrity-protected once finalized |
| CTR-VERDICT | verification engine (PH-7) | v1 | verification | Promotion, release | `PASS/FAIL/BLOCKED/INCONCLUSIVE/NOT_TESTABLE` (R5); change = verification-change process |
| CTR-PROMOTION-PACKAGE | Promotion Service (PH-7; staging partial PH-5) | v1 | integration/lanes | Promotion Service | `01E §3.8`; blocked on missing/stale/hash-mismatch |
| CTR-BASELINE-MANIFEST | Git/workspace mgr (PH-5) | v1 | multi-repo projects | Promotion, release | `01I §3.3`; independent vs atomic promotion |
| CTR-COMMIT-TRAILER | Git/workspace mgr (PH-5) | v1 | Factory commits | audit, traceability | `Factory-Task/Stage/Workstream/Checkpoint/Verification-Status` (`01I §3.4`) |
| CTR-APPROVAL-RECORD | approval engine (PH-3) | v1 | approval engine | audit, Promotion, Dashboard | `01L §3.2` full card fields; bound/expiring/revocable |
| CTR-PERMISSION-GRANT | permission enforcement (PH-3) | v1 | permission engine | tool gateway, brokers | scoped/expiring runtime grant; batch grants narrow |
| CTR-TOOL-DECLARATION | tool registry (PH-3) | v1 | tool authors | tool gateway | `01K §2.3`; unregistered denied |
| CTR-NETWORK-APPROVAL | network broker (PH-5) | v1 | approval | network broker | `01E §3.3`; inbound denied; redirects cannot escape |
| CTR-SECRET-REF | secret broker (PH-5) | v1 | secret broker | consumers via broker | references only, never the secret; revoked pre-disposal |
| CTR-AUDIT-RECORD | audit writer (PH-3) | v1 | audit writer (sole) | audit validator, exports | append-only hash-chained (`01K §3.2`); protected component |
| CTR-SNAPSHOT-MANIFEST | snapshot mgr (PH-7) | v1 | snapshot mgr | Watchdog, updater | `01M §3.9`; Factory-state only, GitHub excluded |
| CTR-MEMORY-RECORD | memory system (PH-2) | v1 | verified decisions/lessons | retrieval, Dashboard | `01F` provenance/status/namespace; no auto-persist |
| CTR-RETENTION-POLICY | retention system (PH-7) | v1 | config | retention processing | `01C` hot/cold/purge + holds |
| CTR-IMPROVEMENT-PACKET | self-improvement (deferred) | v1 | monthly analysis | operator, sandbox | `01C §9`/`01H §3`; **never auto-apply** (R3); lifecycle `01H §4.2` |
| CTR-RESEARCH-PACKET | research system (deferred) | v1 | research | memory, proposals | `01Q §2.50`; no implementation authority |
| CTR-GRAPH-INDEX | graph-mapping (PH-8) | v1 | repo index/graph | Dashboard, impact | `01P §3.1/§3.2`; derived, rebuildable, never sole truth |
| CTR-CONFIG | configuration system (PH-1) | v1 | config authors | all components | versioned, explicit; no secrets |
| CTR-MIGRATION | schema&migration (PH-1/PH-7) | v1 | migration authors | Orchestrator, updater | SHA-verified transactional; incompatible downgrade fails closed |
| CTR-RELEASE-MANIFEST | release verification (PH-8) | v1 | packaging/release | updater, operator | `01O §3.9` provenance/SBOM/digests/signing |
| CTR-WORKSTREAM | workstream engine (PH-6) | v1 | workstream declaration | scheduler, integration | `01D §2.4` owner/scope/inputs/outputs/deps/completion gate |
