# Component Implementation Map

**Status:** Authoritative planning record (L25.1) — parent of the individual `<component>-spec.md` files
**Recorded:** July 24, 2026
**Sources:** `02` + supplements `01C`–`01Q`; in force with `01R` (R1–R5, Decisions A–C). Individual component specs are spun out from this map using `docs/templates/component/COMPONENT-SPECIFICATION.template.md`.

## Inherited baselines (every component; blocks state only deltas)
- **BASE-P (permitted):** act only within the active Task/Permission contract's granted scope; read validated canonical contracts + cache; submit commands/appendable events to the **Orchestrator** (R1).
- **BASE-X (prohibited):** no direct write to the runtime-state DB (Orchestrator only, R1); cannot bypass permission/approval/evidence/audit/isolation/Promotion gates; cannot self-certify completion/promotion (`01 §3`, `02 §17`, `01G §1`); cannot expand own authority or exceed granted paths; cannot alter governing controls except via the architecture-change process (`01H §2.30/§4.1`); no default telemetry/network/downloads.
- **BASE-T (trust):** model/repo/tool/external data untrusted until validated (`01K §1`, `01Q §1`); least privilege; repo-controlled execution forced into a sandbox (`01E §1`).
- **BASE-S (security):** least-privilege scoped/expiring grants; secrets via broker, redacted (`01E §3.4`); path canonicalization + escape blocking (`01K §2.26-27`); privileged/destructive/external/promotion actions → tamper-evident audit (`01K §3.2`).
- **BASE-D (degradation):** capability-scoped; never weakens verification/permission/audit/evidence/isolation/state-authority (`01M §2.24`).
- **BASE-R (recovery):** fail closed on unknown/inconsistent/corrupt/security state → BLOCKED/QUARANTINED (`01M §2.25`); resume only after reconciliation (`01M §2.12`); preserve evidence before restart (`01M §2.15`).
- **BASE-RES (resource):** bounded by versioned Resource Scheduler policy; reservations before use (`01J §3.3`, `01K §3.1`); ≤1 GPU-heavy on 12 GB (`01D §2.13`).

## Components (40)

> **Change-control note (2026-07-26, RPH3 Pass 4):** #40 **CMP-FILEOP** added to correct a prior omission —
> roadmap §PH-3 names a "safe file-op" component and the section-3 plan owns `src/factory/fileops/**`, but no
> dedicated row existed. This records an existing roadmap component, not a new architectural decision.

Fields: responsibility · authoritative state · inputs/outputs · interfaces · dependencies · owned contracts · +/− authority · trust · failure/degrade/recovery · security · resource · tests · phase.

1. **CMP-DASH — Dashboard** [Shell+PH-8]: view+control surface, no authoritative state; owns no contract; −Auth: broken panel gains no authority (`06 §3`); offline-capable, PIN≠security (`01L §3.4`); tests `01L`(21).
2. **CMP-ORCH — Orchestrator** [PH-2, R1]: **sole authoritative writer**; owns runtime-state DB, activation, journal, leases; every transition atomic; external Watchdog detects deadlock; tests atomicity/fencing/no-direct-write.
3. **CMP-TASKENG — Task engine** [PH-2]: task states/queue/deps (Orchestrator-written); legal transition table; idempotent restart.
4. **CMP-LANESM — Lane state machine** [PH-6]: lane lifecycle (`01D §3.1`); consistent with task/workstream SM; owns CTR-LANE-LIFECYCLE.
5. **CMP-WSSM — Workstream state machine** [PH-2]: authoritative `01L §3.1` states; owns CTR-TASK-WS-SM; no client invents a transition.
6. **CMP-RESSCHED — Resource Scheduler** [PH-4]: executable reservations/admission; missing sensor→REDUCED_MONITORING; no evict without checkpoint.
7. **CMP-ROUTER — Model router** [PH-4]: deterministic/visible/overridable routing; owns CTR-ROUTE-REGISTRY/MODEL-FINGERPRINT; **no silent substitution**; fallback=new record.
8. **CMP-MODELREC — Model-execution records** [PH-4]: append fingerprints/provenance; owns CTR-MODEL-EXEC-RECORD.
9. **CMP-TOOLREG — Tool registry** [PH-3]: approved-tool registry, default-deny; owns CTR-TOOL-DECLARATION.
10. **CMP-TOOLGW — Tool gateway** [PH-3]: single controlled tool-call path; validates output schema; models cannot bypass.
11. **CMP-APPROVAL — Approval engine** [PH-3]: central queue, bound/expiring/revocable; owns CTR-APPROVAL-RECORD; **autonomy envelope (Dec A)**; security violations denied+audited.
12. **CMP-PERM — Permission enforcement** [PH-3]: least-privilege decisions; owns CTR-PERMISSION-GRANT; **deletion approval-gated (Dec B)**; TOCTOU revalidation.
13. **CMP-SECRET — Secret broker** [PH-5]: ephemeral scoped injection; owns CTR-SECRET-REF; never in images/caches/checkpoints/packages/memory.
14. **CMP-SANDBOX — Sandbox manager** [PH-5]: disposable non-root **WSL2+Docker only (Dec C)**; no host mount/socket/namespaces; tests `01E`(32).
15. **CMP-NETBROKER — Network broker** [PH-5]: default-deny task-scoped network; owns CTR-NETWORK-APPROVAL; no inbound; redirects cannot escape.
16. **CMP-CACHE — Cache manager** [PH-5]: immutable/content-addressed caches; no credentials/writable state.
17. **CMP-STAGING — Quarantined staging** [PH-5]: only sandbox-output exit; inventory/hash/scan/scope-compare; non-promotable until inspected.
18. **CMP-PROMO — Promotion Service** [PH-7]: **sole protected-ref writer** (local/offline); owns CTR-PROMOTION-PACKAGE; blocks on incomplete package; direct ref mutation→security event.
19. **CMP-GIT — Git & workspace manager** [PH-5]: task branches/worktrees, checkpoint commits; owns CTR-BASELINE-MANIFEST/COMMIT-TRAILER; no auto force-push/protected-write; no auto repo/branch/tag/release deletion.
20. **CMP-EVID — Evidence store** [PH-7]: owns finalized evidence packages (integrity); owns CTR-EVIDENCE-PACKAGE; deterministic evidence authoritative.
21. **CMP-ETM — Evidence Traceability Manifest system** [PH-7, R5]: per-criterion ETM; owns CTR-ETM; broken link blocks promotion; protected component.
22. **CMP-AUDITW — Audit writer** [PH-3]: owns append-only hash-chained audit; owns CTR-AUDIT-RECORD; no update/delete; protected component.
23. **CMP-AUDITV — Audit-chain validator** [PH-3]: integrity verification; break→security event.
24. **CMP-MEM — Memory system** [PH-2, cross]: owns project-authority+global records; owns CTR-MEMORY-RECORD; no auto-persist; project→global needs approval; no secrets.
25. **CMP-RETAIN — Retention system** [PH-7, cross]: rolling raw-session lifecycle; owns CTR-RETENTION-POLICY; hold blocks purge; never deletes finalized evidence/audit.
26. **CMP-WATCH — Watchdog** [PH-3, R1]: independent, normally read-only supervisor; 7 narrow interventions; **no arbitrary edits, cannot modify own authority**; loss pauses/blocks high-risk work.
27. **CMP-JOURNAL — Recovery journal** [PH-2]: owns durable journal; owns CTR-RECOVERY-JOURNAL; flush-before-success; idempotent replay.
28. **CMP-LEASE — Lease & fencing system** [PH-2]: expiring fenced leases; owns CTR-LEASE-FENCING; stale owner cannot write post-supersession.
29. **CMP-SNAP — Snapshot manager** [PH-7]: single active rolling snapshot + candidate; owns CTR-SNAPSHOT-MANIFEST; **never overwrites GitHub repos**.
30. **CMP-REPOIDX — Repository-intelligence index** [PH-8]: derived rebuildable indexes; owns CTR-GRAPH-INDEX; cannot grant permission; inferred≠authoritative.
31. **CMP-GRAPH — Graph-mapping system** [PH-8]: four graph views; findings cannot auto-trigger code; traceability VERIFIED only via approved means.
32. **CMP-RESEARCH — Research & source-evidence** [deferred/Stage 14]: task-scoped research; owns CTR-RESEARCH-PACKET; cannot authorize implementation/disclosure/release; internet off by default.
33. **CMP-CONFIG — Configuration system** [PH-1]: versioned config + route registry; owns CTR-CONFIG; no secrets; governing-control change=architecture process.
34. **CMP-SCHEMA — Schema & migration system** [PH-1/PH-7]: schemas + SHA-verified transactional migrations; owns CTR-MIGRATION; incompatible downgrade fails closed.
35. **CMP-UPDATER — Updater** [PH-8]: signed/staged/transactional/snapshot-protected updates; no unattended install; no unsigned exception; snapshot-gate.
36. **CMP-INSTALL — Installer** [PH-8]: guided installer, Windows 11 Home ±activation; **no activation gate**; no auto BIOS/model download; minimal host mod.
37. **CMP-DIAG — Diagnostics** [PH-8/Safe Mode PH-3]: inspection + approved repair; **Safe Mode no autonomous writes**.
38. **CMP-PKG — Packaging** [PH-8]: build from clean commit; immutable identities, SBOM, hashes; co-owns CTR-RELEASE-MANIFEST.
39. **CMP-RELVER — Release verification** [PH-8]: lifecycle/failure-path release verification on Windows 11 Home ±activation; co-owns CTR-RELEASE-MANIFEST; stable requires zero critical/high; verdict `PASS/FAIL/BLOCKED/INCONCLUSIVE`.

40. **CMP-FILEOP — Safe file-op service** [PH-3]: single safe file-operation path; canonicalizes+validates every path and blocks symlink/junction/reserved-name/traversal/case/archive escapes; **all deletion approval-gated (Dec B)**; archive entry/depth/decompression limits; atomic in-scope writes; owns no contract (consumes CTR-PERMISSION-GRANT/CTR-APPROVAL-RECORD); tests `01K-AC-10/11`.

Full 18-field specifications per component are in `docs/specifications/components/<component>-spec.md` (authored per phase); this map is the authoritative index and cross-reference.
