# Roadmap PH-3 — Authoritative Traceability (01M / 01K → RPH3)

**Document ID:** TRACE-RPH3 · **Repository path:** `docs/planning/RPH3-TRACEABILITY.md`
**Status:** Active traceability record (subordinate to `01M`/`01K`/`01R`) · **Owner:** RPH3 planning (repair)
· **Established:** 2026-07-26. **Namespace:** RPH3. This is the single source of truth for how every
governing criterion maps to RPH3; PLAN-S3, VEP-RPH3, FRR-RPH3, SEC-RPH3, and CERT-RPH3 cite these identifiers.

## 0. Identifier discipline (the defect this document fixes)

`01M` and `01K` each contain **two separate numbered lists**. They must never be conflated:

| Doc | Approved-decision list (`§2`) | Acceptance-criteria list |
|---|---|---|
| `01M` | **`01M-DEC-01…36`** (`§2` "Approved Stage 11 decisions", 36 items) | **`01M-AC-01…32`** (`§6` "Acceptance criteria", 32 items) |
| `01K` | **`01K-DEC-01…33`** (`§2` "Approved Stage 9 decisions", 33 items) | **`01K-AC-01…25`** (`§5` "Acceptance criteria", 25 items) |

**Rule:** the phase-exit gate `PROM-RPH3` is defined over **acceptance criteria** (`-AC-`). Decisions
(`-DEC-`) are cited only where a control's rationale needs the decision text. **Ambiguous `01M #NN`/`01K #NN`
references are prohibited.** Decisions **A** and **B** are `01R` decisions (autonomy envelope / deletion
approval-required) — distinct from `01M-DEC`/`01K-DEC`.

## 1. `01M` acceptance-criteria disposition (`01M-AC-01…32`)

Disposition: **RPH3** (verified at PROM-RPH3) · **PH-2** (frozen, re-verified via consumed interface) ·
**PH-5**/**PH-7** (enforcement/artifact deferred; RPH3 defines interface only).

| ID | Criterion (`01M §6`) | Disposition | Task/Comp · VR |
|---|---|---|---|
| 01M-AC-01 | detect unresponsive Orchestrator from a separate process | RPH3 | T1 · VR-RPH3-01 |
| 01M-AC-02 | operational when Orchestrator loop/pool stalls | RPH3 | T1 · VR-RPH3-01 |
| 01M-AC-03 | normal monitoring cannot silently alter state | RPH3 | T1 · VR-RPH3-01 |
| 01M-AC-04 | intervention limited to predefined interface; arbitrary mutation rejected | RPH3 | T1 · VR-RPH3-01/04 |
| 01M-AC-05 | timing correct across Windows wall-clock changes | RPH3 | T1 · VR-RPH3-02 |
| 01M-AC-06 | staged thresholds use sustained windows + hysteresis | RPH3 | T1 · VR-RPH3-02 |
| 01M-AC-07 | missing sensors → REDUCED_MONITORING, no fabricated readings | RPH3 | T1 · VR-RPH3-02 |
| 01M-AC-08 | only enumerated critical triggers cause termination/containment | RPH3 | T1 · VR-RPH3-03 |
| 01M-AC-09 | bounded restart + exponential backoff + circuit breaker | RPH3 | T1 (receiver: RESTART_SERVICE supervisor) · VR-RPH3-03 |
| 01M-AC-10 | restart exhaustion → BLOCKED/QUARANTINED | RPH3 | T1 · VR-RPH3-03 |
| 01M-AC-11 | deterministic failure normalization (counters not reset by superficial change) | RPH3 | T1 · VR-RPH3-03 |
| 01M-AC-12 | critical transition success not reported before durable journal + state commit | PH-2 (CMP-JOURNAL/ORCH), re-verified | cross-store protocol · VR-RPH3-19 |
| 01M-AC-13 | stale lease owner cannot write after a newer fencing token | **PH-2 (CMP-LEASE)** — NOT RPH3-consumed | — |
| 01M-AC-14 | no resume before complete reconciliation | PH-2 (CMP-JOURNAL); T1 consumes read-only | T1 · VR-RPH3-05 |
| 01M-AC-15 | unknown resources quarantined before cleanup | **split:** task/tool → RPH3 (T1/T5); sandbox/worktree → PH-5 | T1/T5 |
| 01M-AC-16 | orphan cleanup cannot destroy evidence/checkpoint/recovery/retention holds | **PH-5/PH-7** | deferred |
| 01M-AC-17 | startup reconciliation incl. model workers/containers/worktrees/volumes/promotions | PH-2 (tasks) + **PH-5/PH-6** (containers/worktrees/volumes) | partial; T1 tasks subset |
| 01M-AC-18 | degraded operation capability-scoped; weakens no mandatory control | RPH3 (Safe Mode / REDUCED_MONITORING) | T1/T5 · VR-RPH3-06 |
| 01M-AC-19 | core-control failure fails closed | **split by control:** permission/approval/audit/state-authority → **RPH3** (T1/T2/T4); **isolation** control → **PH-5** (EG-PH5-11); **evidence/promotion** control → **PH-7** (EG-PH7-01) | RPH3 part · VR-RPH3-03 |
| 01M-AC-20 | Safe Mode no autonomous execution/unrestricted writes | RPH3 | T5 (CMP-DIAG) · VR-RPH3-06 |
| 01M-AC-21 | every Watchdog intervention → traceable integrity-protected audit record | RPH3 | T1+T4 · VR-RPH3-04 |
| 01M-AC-22 | Watchdog cannot modify its own governing rules/config | RPH3 | T1 · VR-RPH3-04 |
| 01M-AC-23 | crash/interruption/partial-write/lease-fencing/restart-exhaustion/Watchdog-loss sims | RPH3 (Watchdog-loss) + PH-2 (partial-write/lease) | T1 failure-path · VR-RPH3-05 |
| 01M-AC-24 | candidate snapshots restore-tested in isolation before replacing active | **PH-7** | deferred |
| 01M-AC-25 | snapshot restoration validates checksums/schema/replay/refs/permissions/startup | **PH-7** | deferred |
| 01M-AC-26 | failed candidate snapshot leaves active unchanged; quarantined | **PH-7** | deferred |
| 01M-AC-27 | snapshot restoration cannot overwrite GitHub project repos | **PH-7** | deferred |
| 01M-AC-28 | emergency reserve pauses new work before consumption | **PH-7/storage**; Watchdog monitors the threshold | RES-ALLOC · T1 (monitor only) |
| 01M-AC-29 | protected records not auto-deleted for storage recovery | **PH-7 retention** | deferred |
| 01M-AC-30 | Watchdog-loss pauses existing + blocks new high-risk work | **split:** **RPH3** issues the pause **transition request** for existing high-risk tasks + **blocks new admission** + fails closed (T1/WIR); **PH-5** actually suspends/terminates the already-running sandbox process (EG-PH5-12) | RPH3 part · VR-RPH3-07 |
| 01M-AC-31 | low-risk read-only inspection continues only while controls healthy | RPH3 | T1 · VR-RPH3-07 |
| 01M-AC-32 | Windows auto-launch disabled unless explicitly enabled | RPH3 | T1 · VR-RPH3-02 |

**RPH3-scoped `01M-AC`:** 01,02,03,04,05,06,07,08,09,10,11,14(read),15(task/tool),18,19,20,21,22,23(Watchdog-loss),
28(monitor),30,31,32. **PH-2 frozen (re-verified):** 12,13,14,17(tasks),23(partial-write/lease). **PH-5/PH-7
deferred (interface-only in RPH3):** 15(sandbox),16,17(containers),24,25,26,27,28(reserve),29.

`01M-DEC` note: the 36 `01M §2` decisions are the rationale source (e.g. `01M-DEC-01` independent Watchdog,
`01M-DEC-02` read-only monitoring, `01M-DEC-10` bounded service restart, `01M-DEC-35` Watchdog dependency for
high-risk work, `01M-DEC-36` optional Windows auto-launch). They are **not** acceptance criteria and are never
counted toward `PROM-RPH3`; the corresponding *tested* criteria are the `01M-AC` rows above (e.g. the
`01M-DEC-35` behavior is tested as `01M-AC-30`/`01M-AC-31`; `01M-DEC-36` as `01M-AC-32`).

## 2. `01K` acceptance-criteria disposition (`01K-AC-01…25`) — with PH-3 / PH-5 enforcement split

| ID | Criterion (`01K §5`) | Disposition | Task/Comp · VR |
|---|---|---|---|
| 01K-AC-01 | unregistered tools cannot execute | RPH3 | T5 (TOOLREG/TOOLGW) · VR-RPH3-08 |
| 01K-AC-02 | tool permissions cannot exceed current task approval | RPH3 | T2 (PERM) · VR-RPH3-09 |
| 01K-AC-03 | approvals not reusable outside task/action/path/scope/repetition/expiration | RPH3 | T3 (APPROVAL) · VR-RPH3-10 |
| 01K-AC-04 | permanent unrestricted tool authority cannot be created | RPH3 | T2/T3 · VR-RPH3-09/10 |
| 01K-AC-05 | destructive + external actions require separate confirmation | RPH3 | T3 · VR-RPH3-10 |
| 01K-AC-06 | shell/elevated cannot run directly on the host | **PH-5 ENFORCEMENT** (sandbox); RPH3 = seam contract + fail-closed when no valid executor | T5 interface + PH-5 gate |
| 01K-AC-07 | credentials temporary/scoped/redacted/revocable/removed | **PH-5** (secret broker); RPH3 = credential permission class only | PH-5 gate |
| 01K-AC-08 | denied network destinations/protocols/redirects/limits inaccessible | **PH-5** (network broker) | PH-5 gate |
| 01K-AC-09 | downloaded components retain provenance + integrity records | RPH3 | T5 (TOOLREG) · VR-RPH3-13 |
| 01K-AC-10 | path/symlink/junction/reserved-name/archive escapes blocked | RPH3 | T2/T5 (PERM/FILEOP) · VR-RPH3-11 |
| 01K-AC-11 | archive entry/depth/decompression limits prevent bombs | RPH3 | T5 (FILEOP) · VR-RPH3-11 |
| 01K-AC-12 | repo/downloaded instructions cannot override governing policy | RPH3 | T2 · VR-RPH3-16 |
| 01K-AC-13 | wall-clock/idle/CPU/RAM/storage/process/file/output/log/download limits enforced | **split:** RPH3 = limit **request contract** + fail-closed; **PH-5** = actual OS enforcement | T5 interface + PH-5 gate |
| 01K-AC-14 | quota/timeout termination kills complete owned process tree | **PH-5 ENFORCEMENT**; RPH3 = termination **request contract** | T5 interface + PH-5 gate |
| 01K-AC-15 | abnormal termination leaves no surviving orphan | **PH-5 ENFORCEMENT** | PH-5 gate |
| 01K-AC-16 | abnormal termination quarantines the sandbox | **PH-5 ENFORCEMENT** | PH-5 gate |
| 01K-AC-17 | evidence preserved before abnormal sandbox disposal | **PH-5/PH-7 ENFORCEMENT** | PH-5/PH-7 gate |
| 01K-AC-18 | unsafe repeated tool failures trigger tool quarantine | RPH3 | T5 (TOOLREG) · VR-RPH3-13 |
| 01K-AC-19 | privileged actions produce append-only hash-chained tamper-evident audit | RPH3 | T4 (AUDITW) · VR-RPH3-14 |
| 01K-AC-20 | audit truncation/rewriting/chain-break/invalid-anchor detectable | RPH3 | T4 (AUDITV) · VR-RPH3-14 |
| 01K-AC-21 | emergency stop terminates unsafe activity without waiting | **split:** **RPH3** issues containment, revokes authority, blocks admission, requests task-state transition, fails closed (T1 CONTAIN + operator stop); **PH-5** performs the actual process-tree termination + proves no surviving orphan (EG-PH5-05/06) | RPH3 part · VR-RPH3-15 |
| 01K-AC-22 | Safe Mode cannot perform autonomous writes / bypass approvals | RPH3 | T5 (CMP-DIAG) · VR-RPH3-06 |
| 01K-AC-23 | sandbox recordings/logs/evidence remain separate from authoritative records | **PH-5/PH-7 ENFORCEMENT** | PH-5/PH-7 gate |
| 01K-AC-24 | sandbox expiration/disposal cannot delete promoted evidence/audit | **PH-5/PH-7 ENFORCEMENT** | PH-5/PH-7 gate |
| 01K-AC-25 | no telemetry leaves without explicit approval | RPH3 emits none + PH-1 config default | cross · VR-RPH3-12 |

**RPH3-verifiable `01K-AC`:** 01,02,03,04,05,09,10,11,12,13(request-contract),18,19,20,21,22,25. **PH-5 (or
PH-5/PH-7) enforcement gates — NOT certifiable by PROM-RPH3:** 06,07,08,13(OS-enforcement),14,15,16,17,23,24.

`01K-DEC` note: the 33 `01K §2` decisions are rationale (e.g. `01K-DEC-01` central tool registry,
`01K-DEC-02` default denial, `01K-DEC-25` **untrusted tool output** — the basis for gateway output validation,
`01K-DEC-29` tamper-evident privileged audit, `01K-DEC-32` diagnostic Safe Mode). They are **not** acceptance
criteria. In particular, **tool-output validation traces to `01K-DEC-25` (decision)**, not to `01K-AC-25`
(which is "no telemetry") — the prior corpus conflated these.

## 3. PH-5 / PH-7 enforcement gates (moved out of PROM-RPH3)

The following are **enforcement** properties requiring a real sandbox/executor (PH-5) or the promotion/
evidence/snapshot machinery (PH-7), and are certified there — **never by `PROM-RPH3`**. **RPH3 obligation for
each:** define the request/decision contract (limits, termination request, containment request, permission
class) and prove **fail-closed behavior when the enforcing executor does not exist** (consistent with XIB-02).
RPH3 must not claim actual proof of process-tree termination, orphan prevention, sandbox quarantine, sandbox
recording separation, evidence-before-disposal, isolation-control failure, or promotion/evidence/snapshot
enforcement.

**PH-5 enforcement gates (`EG-PH5-*`):**

| Gate | Acceptance / property | RPH3 interface obligation (verified here) |
|---|---|---|
| EG-PH5-01 | `01K-AC-06` no host shell/elevated | seam contract; fail-closed when no executor |
| EG-PH5-02 | `01K-AC-07` credential lifecycle | credential permission class |
| EG-PH5-03 | `01K-AC-08` network denial | network permission class |
| EG-PH5-04 | `01K-AC-13` OS enforcement of resource limits | limit request contract + fail-closed |
| EG-PH5-05 | `01K-AC-14` complete process-tree termination | termination **request**; RPH3 issues containment + proves no direct host execution |
| EG-PH5-06 | `01K-AC-15` / `01K-AC-21` no surviving orphan (proof) | RPH3 issues the emergency-stop/containment request only |
| EG-PH5-07 | `01K-AC-16` sandbox quarantine on abnormal exit | — |
| EG-PH5-08 | `01K-AC-17` evidence before sandbox disposal | — |
| EG-PH5-09 | `01K-AC-23,24` sandbox-record separation / disposal-safety | — |
| EG-PH5-10 | sandbox parts of `01M-AC-15,17` | task/tool quarantine is RPH3; sandbox/worktree is PH-5/6 |
| EG-PH5-11 | `01M-AC-19` **isolation-control** fail-closed | RPH3 fails closed on permission/approval/audit/state-authority; isolation control does not exist until PH-5 |
| EG-PH5-12 | `01M-AC-30` suspend/terminate an **already-running** high-risk sandbox process after Watchdog loss | RPH3 issues the pause transition + blocks new admission; PH-5 suspends the live process |

**PH-7 enforcement gates (`EG-PH7-*`):**

| Gate | Acceptance / property | RPH3 obligation |
|---|---|---|
| EG-PH7-01 | `01M-AC-19` **evidence/promotion-control** fail-closed | RPH3 defines audit/permission fail-closed only |
| EG-PH7-02 | `01M-AC-24..29` snapshot restore-test / activation / emergency-reserve / no-emergency-deletion | RPH3 defines the `ACTIVATE_VERIFIED_SNAPSHOT` request typing (INERT until PH-7) |
| EG-PH7-03 | promotion blocking, evidence enforcement, promotion-package verification | none (PH-7 owns; RPH3 audit records feed it) |

**No obligation is removed — each is split into exact phase-owned criteria with end-to-end traceability:** the
RPH3 half (request/containment/fail-closed) is verified at `PROM-RPH3`; the enforcement half is verified at
its `EG-PH5-*`/`EG-PH7-*` gate.

## 4. Decisions A / B (01R)

| Decision | Requirement | RPH3 mapping |
|---|---|---|
| **Dec A** (autonomy envelope) | autonomy level gates auto vs approval-card actions | T2 `AutonomyEnvelope.classify` + T3 card display · VR-RPH3-17-A |
| **Dec B** (deletion approval-required) | ALL file deletion approval-gated; no auto-delete path | T2 decision + T3 card + T5 `FileOpService.delete(approval_ref)` · VR-RPH3-18-B |
