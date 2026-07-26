# Roadmap PH-3 — Security & Trust-Boundary Plan (SEC-RPH3)

**Document ID:** SEC-RPH3 · **Repository path:** `docs/planning/RPH3-SECURITY-TRUST-BOUNDARIES.md`
**Status:** Active plan (subordinate to `01K` / `01E` / `01M`) · **Owner:** RPH3 planning (Pass 8) ·
**Established:** 2026-07-26. **Governing:** `01K` (tool/permission/audit security), `01E` (isolation
boundaries — enforcement PH-5), `01M` (fail-closed controls, Watchdog). **Namespace:** RPH3; security-test
labels are **`SEC-RPH3-*`** (NOT the substrate's `SEC-PH3-*`). Builds only on frozen PH-2 (PLAN-S3 §1).

## 1. Purpose

Roadmap PH-3 *is* the security spine, so this plan is central: it enumerates the assets PH-3 protects, the
threats it defends against, the trust zones and boundaries, the mapping of each control to a component, and
the security tests that gate promotion. A failing `SEC-RPH3-*` test **blocks** `PROM-RPH3` (VEP-RPH3 §3/§6).

## 2. Protected assets

| Asset | Owner | Protection |
|---|---|---|
| Runtime authoritative state | CMP-ORCH (PH-2, R1) | single-writer; PH-3 never writes it directly (BASE-X) |
| Tamper-evident audit chain | CMP-AUDITW | append-only, hash-chained, sole writer, break-detected |
| Permission grants | CMP-PERM | scoped/expiring/revocable; least-privilege |
| Approval records / queue | CMP-APPROVAL | bound/expiring/revocable; non-reusable |
| Tool registry + declarations | CMP-TOOLREG | default-deny; complete declaration + provenance |
| Governing controls/policy | governing corpus | not weakenable via a normal Improvement Packet (`01K §4`) |
| Watchdog authority/config | CMP-WATCH | immutable to itself (`01M §2.28`) |
| Credentials / secrets | CMP-SECRET (**PH-5**) | RPH3 defines the credential permission class; broker is PH-5 |

## 3. Threat model → control → component

| Threat | Control | Component | Test |
|---|---|---|---|
| Privilege escalation beyond task approval | least-privilege + TOCTOU revalidation | CMP-PERM | SEC-RPH3-01 |
| Permission/gateway bypass (tool runs unapproved/unregistered) | default-deny registry + single gateway path | CMP-TOOLREG/TOOLGW | SEC-RPH3-02 |
| Audit tampering (delete/truncate/reorder/rewrite) | append-only hash chain + validator | CMP-AUDITW/AUDITV | SEC-RPH3-03 |
| Approval reuse / forgery / permanent authority | bound/expiring/non-reusable approvals | CMP-APPROVAL | SEC-RPH3-04 |
| Unauthorized deletion (Dec B) | all deletion approval-gated; no auto-delete path | CMP-PERM/FILEOP/APPROVAL | SEC-RPH3-05 |
| Autonomy-envelope violation (Dec A) | level gates auto vs approval-card | CMP-PERM/APPROVAL | SEC-RPH3-06 |
| Path/escape (symlink/junction/reserved/traversal/case/archive) | canonicalize + escape blocking + archive limits | CMP-FILEOP/PERM | SEC-RPH3-07 |
| Resource exhaustion / DoS / orphan processes | per-execution caps + complete process-tree kill | CMP-TOOLGW | SEC-RPH3-08 |
| Untrusted tool output injection | schema-validate output; oversized fails closed | CMP-TOOLGW | SEC-RPH3-09 |
| Instruction injection (repo/downloaded/external as commands) | instructions are untrusted data, cannot widen grants | CMP-PERM (BASE-T) | SEC-RPH3-10 |
| Watchdog subversion (self-authority modification / arbitrary mutation) | narrow interface only; authority immutable | CMP-WATCH | SEC-RPH3-11 |
| Safe-Mode abuse (autonomous write / approval bypass) | inspection/approved-repair only; no autonomous write | CMP-DIAG | SEC-RPH3-12 |
| Security violation smuggled as an approval | denied + audited, never queued as a card | CMP-APPROVAL | SEC-RPH3-04 |

## 4. Trust zones & boundaries

```
Zone-0  Governing corpus + activated contracts        TRUSTED (read-only inputs; change = architecture process)
Zone-1  Factory security core                          TRUSTED CODE: CMP-PERM, CMP-APPROVAL, CMP-AUDITW/V, CMP-WATCH
Zone-2  Registered tools (via CMP-TOOLGW)              CONDITIONALLY TRUSTED: default-deny, permission-scoped, resource-bounded
Zone-3  Models, repo content, tool OUTPUT, downloads,  UNTRUSTED: validated before use; never governing commands
        external instructions
```

- **Z3→Z2 boundary:** all tool output is untrusted until schema/integrity/scope-validated (CMP-TOOLGW).
- **Z2→Z1 boundary:** no tool/model reaches a security-core write except through permission + approval + audit;
  models cannot bypass the gateway (no-bypass invariant).
- **Z1 internal:** the audit writer is the sole audit-chain writer; the Watchdog is read-only + narrow
  interface and cannot mutate its own authority; no PH-3 component writes the runtime-state DB (R1).
- **Z1↔PH-5 (forward):** the credential/network/sandbox boundaries (`01E`, `01K` #7/#8/#23/#24) are enforced
  by PH-5 brokers/sandbox; RPH3 defines the permission classes but does not enforce isolation (**not absorbed**).

## 5. Core-control invariants (fail closed)

1. **No-bypass:** default-deny registry + single gateway path (SEC-RPH3-02).
2. **Single audit writer + break detection** (SEC-RPH3-03); audit non-authoritative while broken.
3. **Least-privilege + TOCTOU** (SEC-RPH3-01); no permanent unrestricted authority.
4. **Deletion approval-gated (Dec B)** (SEC-RPH3-05); no auto-delete path exists in code or tests.
5. **Autonomy envelope (Dec A)** (SEC-RPH3-06).
6. **Safe-Mode no autonomous write** (SEC-RPH3-12).
7. **Watchdog self-authority immutability + narrow interface** (SEC-RPH3-11).

Any invariant violation fails closed and is audited. These are the VM-2 security-spine acceptance core.

## 6. Security tests (SEC-RPH3-01..12)

Each label above is a required security/adversarial test in VEP-RPH3 §2 (VR-RPH3 cross-reference) and PLAN-S3
per-task test lists. Adversarial variants (active attack attempts) accompany each: gateway-bypass, forged
audit identity, TOCTOU race, autonomy bypass, archive bomb, path escape, oversized output, expired-approval
reuse, intervention flood, unapproved Safe-Mode repair, self-authority modification.

## 7. Traceability & scope boundary

Every threat → a control → a component → a `SEC-RPH3-*` test → an ETM row (VEP-RPH3). Assets and boundaries
are consistent with `01K`/`01E`/`01M`. **Out of RPH3 security scope (not absorbed, Constraint 7):** sandbox
isolation, secret broker, network broker (PH-5, `01E`); the four substrate blockers XIB-01..04 (PLAN-S3 §7,
owned by a dedicated PR #10 correction / PH-5). RPH3 defines the interface each must satisfy; it does not
enforce or repair them.
