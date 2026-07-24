# PH-3 (Section 3) — Watchdog, Permissions, Approval, Audit & Tools — Implementation Plan

**Status:** Approved planning order (L25.1) · **Governing:** `01M`, `01K`, `01 §3/§11`, `01R` R1/Dec A/B. Roadmap spec: `docs/10` PH-3. In force with `01R`.

**R1:** the Watchdog is a **separate, independently supervised, normally read-only** process — not the state writer. **Decision A** (autonomy envelope) and **Decision B** (deletion approval-required) are applied here.

## Task decomposition
### Task 3.1 — Independent Watchdog process + narrow control interface
- Owned paths: `src/factory/watchdog/**`. Deliverables: separately supervised OS process/service; the 7 predefined interventions (`01M §3.2`); monotonic heartbeats; staged thresholds. Tests (`01M` 32): detects stalled Orchestrator from a separate process; read-only normal monitoring; arbitrary mutation rejected; **cannot modify own authority**; Watchdog loss pauses/blocks high-risk work. Evidence: Watchdog ETM (VM-2/RM-1). Completion: `01M` acceptance.
### Task 3.2 — Permission enforcement + path authority + **deletion policy (Dec B)** + **autonomy envelope (Dec A)**
- Owned paths: `src/factory/permission/**`. Deliverables: least-privilege decisions; TOCTOU pre-use revalidation; **all file deletion approval-required**; autonomy-level parameter scoping automatic actions. Contracts: CTR-PERMISSION-GRANT. Tests (permission #9, path-safety #10): least-privilege; **deletion approval-gated**; TOCTOU rejection; autonomy-boundary tests (level gates which actions auto-run vs need a card). Evidence: permission ETM. Completion: `01K §2.4-8`; `01 §11`; `01R` Dec A/B.
### Task 3.3 — Approval engine + central queue + complete approval cards
- Owned paths: `src/factory/approval/**`. Deliverables: bound/expiring/revocable approvals; complete card scope (`01L §3.2`); autonomy-level display. Contracts: CTR-APPROVAL-RECORD. Tests: scope/expiry/repetition binding; no reuse; **security violations denied+audited, not offered as approvals**; card completeness. Evidence: approval ETM. Completion: `01K §2.6-8`, `01L §3.2`.
### Task 3.4 — Tamper-evident audit writer + chain validator
- Owned paths: `src/factory/audit/**`. Deliverables: append-only hash-chained audit writer (sole audit writer); startup/export/recovery integrity validation. Contracts: CTR-AUDIT-RECORD. Tests (audit-chain #32): append-only (no update/delete); detects deletion/truncation/reorder/invalid anchor; audit non-authoritative while invalid. Evidence: audit ETM. Completion: `01K §3.2`.
### Task 3.5 — Tool registry + gateway + safe file-op service + Safe Mode
- Owned paths: `src/factory/tools/**`, `src/factory/fileops/**` (full), `src/factory/diagnostics/safe_mode/**`. Deliverables: default-deny tool registry; single gateway (schema-validates output); full safe file-op; restricted Safe Mode. Contracts: CTR-TOOL-DECLARATION. Tests: unregistered denied; models cannot bypass gateway; **Safe Mode no autonomous writes**; process-tree termination (#14). Evidence: tool/security ETM. Completion: `01K` acceptance.

## Acceptance & handoff
Acceptance: `01M`(32)+`01K`(25) PASS (VM-2); autonomy-envelope (Dec A) and approval-gated deletion (Dec B) proven. Rollback boundary: Watchdog holds no writable state; permission/approval reversible; audit append-only. Promotion gate: PH-3 exit approval + begin `01B` St.2 cutover. Handoff → PH-4/PH-5 (both consume the frozen permission/tool-gateway/secret interfaces).
