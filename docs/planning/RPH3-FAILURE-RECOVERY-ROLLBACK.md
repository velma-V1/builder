# Roadmap PH-3 — Failure / Recovery / Rollback Plan (FRR-RPH3)

**Document ID:** FRR-RPH3 · **Repository path:** `docs/planning/RPH3-FAILURE-RECOVERY-ROLLBACK.md`
**Status:** Active plan (subordinate to `01M` / `04` / ROLLBACK-PLAN) · **Owner:** RPH3 planning (Pass 7) ·
**Established:** 2026-07-26. **Governing:** `01M` (fail-closed core controls, quarantine-first, no blind
resume, Watchdog dependency), `01K` (§3.1/§3.4 termination+quarantine), `04` (recovery policy). **Namespace:**
RPH3. Builds only on frozen PH-2 (PLAN-S3 §1); consumes no substrate code.

## 1. Purpose & resilience posture

Defines the failure modes, recovery behavior, and rollback boundary for the roadmap PH-3 security spine. The
governing posture is **fail closed**: failure of any core control (permission, approval, audit, state
authority, Watchdog supervision) stops the affected work rather than degrading to allow/unaudited
(`01M-AC-19`; rationale `01M-DEC-25`). Unknown/inconsistent/security-sensitive state → `BLOCKED`/`QUARANTINED`,
never silent resume (`01M-AC-14`; rationale `01M-DEC-21`). Recovery is bounded, journaled (via frozen CMP-JOURNAL), and conditional on deterministic
reconciliation.

## 2. Failure-mode register (per component)

| ID | Component | Failure mode | Detection | Response (fail-closed) |
|---|---|---|---|---|
| FM-RPH3-01 | CMP-WATCH | Orchestrator stall/deadlock | separate-process heartbeat (monotonic) | staged threshold → PAUSE/CONTAIN via narrow interface; audited |
| FM-RPH3-02 | CMP-WATCH | missing/unreliable sensor | sensor read returns absent | REDUCED_MONITORING (declared); never fabricates a reading |
| FM-RPH3-03 | CMP-WATCH | Watchdog process loss | supervisor / absent heartbeat | existing high-risk work pauses, new high-risk work blocked (`01M` #35) |
| FM-RPH3-04 | CMP-WATCH | attempted self-authority modification | interface validation | rejected, fail closed, audited |
| FM-RPH3-05 | CMP-AUDITW | audit store unavailable / append fails | append transaction error | privileged action fails closed (not performed unaudited) |
| FM-RPH3-06 | CMP-AUDITW | concurrent append on one head | sequence/predecessor check | one wins; loser retries against head; no fork/gap |
| FM-RPH3-07 | CMP-AUDITV | chain break (deletion/truncation/reorder/rewrite/anchor) | recompute + verify | verdict=broken; audit non-authoritative; security event → CMP-WATCH |
| FM-RPH3-08 | CMP-APPROVAL | reuse/expired/out-of-scope consume | is_valid check | denied; no action proceeds without a valid approval |
| FM-RPH3-09 | CMP-APPROVAL | security-violation request enqueued | classification | denied + audited; never queued as a card |
| FM-RPH3-10 | CMP-PERM | grant exceeds task approval / TOCTOU drift | least-priv check + revalidate | deny; stale grant rejected at point of use |
| FM-RPH3-11 | CMP-PERM/CMP-FILEOP | path escape (symlink/junction/reserved/traversal/case/archive) | canonicalize | reject + security event |
| FM-RPH3-12 | CMP-FILEOP | delete without approval (Dec B) | approval_ref check | denied (no auto-delete path exists) |
| FM-RPH3-13 | CMP-FILEOP | archive bomb (entry/depth/size over cap) | archive limits | abort extraction |
| FM-RPH3-14 | CMP-TOOLGW | unregistered/unpermitted tool call | registry + permission check | denied (default-deny; no bypass) |
| FM-RPH3-15 | CMP-TOOLGW | resource/idle/timeout breach | resource monitor | RPH3: issue termination **request** + fail-closed when no executor. **Enforcement (process-tree kill, cred revoke, sandbox quarantine, no-orphan) = PH-5** (EG-PH5-05/06/07) |
| FM-RPH3-16 | CMP-TOOLGW | oversized/invalid tool output | schema/limit validation | fail closed; output not delivered (contrast substrate XIB-03 — external) |
| FM-RPH3-17 | CMP-TOOLREG | repeated equivalent tool failure | deterministic failure identity | quarantine tool; unusable until reviewed+released |
| FM-RPH3-18 | CMP-DIAG | unapproved repair / out-of-scope capability in Safe Mode | permission+approval+scope | denied; no autonomous write |

## 3. Recovery behavior

- **Startup:** integrity checks first — CMP-AUDITV verifies the audit chain before audit is trusted; CMP-WATCH
  and CMP-DIAG consume frozen CMP-JOURNAL `reconcile_startup` outcomes (RESUMABLE/BLOCKED/FAILED/QUARANTINED/
  COMPLETED/CANCELLED). No task resumes before reconciliation succeeds (`01M` #14, PH-2-provided).
- **No blind resume:** in-flight security-spine operations reconcile to `BLOCKED` on restart; resuming a
  BLOCKED item is an explicit operator/approval action.
- **Quarantine-first:** unknown tools/resources are quarantined before any cleanup decision (`01M-AC-15`,
  rationale `01M-DEC-22`; **tool** quarantine `01K-AC-18`; sandbox quarantine `01K-AC-16` = PH-5 EG-PH5-07).
  Quarantine state is durable across restart; no auto-release.
- **Bounded restart:** CMP-WATCH `RESTART_SERVICE` uses bounded retries + exponential backoff + circuit
  breaker; exhaustion → BLOCKED/QUARANTINED (`01M-AC-10`; rationale `01M-DEC-10`).
- **Idempotent recovery:** interventions and audit appends are replayable without duplication (`01M-AC-18`).
- **Cross-store audit-before-success:** every privileged/security/approval/intervention/tool-file operation
  follows the crash-consistent protocol in `docs/planning/RPH3-CROSS-STORE-CONSISTENCY.md` (XSC-RPH3) — audit
  is the commit point; audit-absent operations reconcile fail-closed (`authoritative ⟺ audited`).

## 4. Rollback boundary (per task)

| Task | Rollback boundary |
|---|---|
| RPH3-T1 (Watchdog) | holds **no** writable authoritative state → `git revert`; nothing to unwind |
| RPH3-T4 (Audit) | append-only chain: rollback = "the append transaction did not commit"; `git revert` |
| RPH3-T3 (Approval) | approvals reversible/expiring/revocable; `git revert` |
| RPH3-T2 (Permission) | grants reversible/expiring; `git revert` |
| RPH3-T5 (Tools/FileOp/SafeMode) | registry/quarantine reversible; file-op atomic (no partial artifact); `git revert` |

Cross-task: the security-spine store + separate audit store are the failure domain; no cross-component
rollback coordination is needed because each domain has a single writer (single-writer discipline,
ODI-RPH3-01) and audit is append-only. Migrations are transactional + SHA-pinned (fail closed on partial).

## 5. Failure injections (required failure-path tests)

Watchdog-loss (RM-1); Orchestrator event-loop stall; audit-store-unavailable → privileged action fails
closed; mid-append rollback leaves chain unchanged; restart with in-flight op → BLOCKED (no blind resume);
resource-limit breach → **fail-closed when no valid sandbox executor exists** (process-tree kill + no-orphan
are PH-5 enforcement `01K-AC-14/15` → EG-PH5-05/06); archive bomb aborted (`01K-AC-11`);
TOCTOU race → deny; forced expired-approval reuse → deny. Each maps to a VR-RPH3 (VEP-RPH3 §2) and an ETM row.

## 6. Resilience scenarios

- **Watchdog loss (RM-1):** high-risk work (privileged/credentialed/network/write/destructive/promotion)
  pauses; new high-risk work blocked; low-risk read-only inspection continues only while permission/audit/
  state-authority remain healthy.
- **Audit loss / break:** audit becomes non-authoritative; privileged actions fail closed until integrity is
  restored under operator-governed recovery (no silent repair).
- **Core-control failure:** permission/approval/state-authority failure fails closed (deny), never degrades.
- **External (substrate) failures are out of scope here:** the four PR #10 blockers (PLAN-S3 §7, XIB-01..04)
  are substrate failure modes owned by a dedicated PR #10 correction / PH-5; they are not RPH3 failure modes
  and are not recovered by RPH3 components.

## 7. Traceability

Every FM-RPH3 maps to a component spec failure_modes entry + a VR-RPH3 failure-path/security test + an ETM
row. Rollback boundaries match PLAN-S3 per-task entries. Recovery consumes frozen PH-2 (CMP-JOURNAL/CMP-ORCH),
adds no PH-2 change. Resource envelopes: see `docs/planning/RESOURCE-ALLOCATION-PLAN.md` (G-02, this pass).
