# Roadmap PH-3 — RPH3-T3 Implementation Note (NON-NORMATIVE)

**Document ID:** NOTE-RPH3-T3 · **Repository path:** `docs/planning/RPH3-T3-IMPLEMENTATION-NOTE.md`
**Status:** **NON-NORMATIVE** implementation note, subordinate to the frozen normative plans
(`DEP-RPH3`, `XSC-RPH3`, `approval-spec`). It records **how RPH3-T3 realized the approval domain** and
one **bounded, recorded deviation** from the literal frozen wording of `DEP-RPH3 §3/§3.1`. It changes
no contract and grants no authority. **Established:** 2026-07-26. **Namespace:** RPH3.

> This note exists because a frozen normative document (`DEP-RPH3`) must **not** be edited to fit an
> implementation. An earlier T3 draft edited `DEP-RPH3 §3` in place; that edit was reverted. The
> divergence is instead disclosed here and in the continuation ledger, for explicit operator
> acceptance, rather than hidden by mutating the frozen plan.

## 1. What T3 built in the security-spine store

`migrations/security/0001_security_spine.sql` (RPH3-T3) creates **only the approval domain** of the
security-spine store:

- `approval_records` (CTR-APPROVAL-RECORD; adds `commit_state` + `prior_state` for the XSC-RPH3
  Class-1 durability marker, and `requires_confirmation` for 01K §2.10-11),
- `approval_queue`,
- `approval_intents` (the XSC-RPH3 §3.1 operation-intent shape, **verbatim** — same columns, checks,
  and the three indexes `INDEX(status)`, `INDEX(operation_class,status)`, `INDEX(target_ref)`).

It does **not** create the permission, tool, or watchdog tables. Those are owned by RPH3-T2
(`permission_*`), RPH3-T5 (`tool_*`), and the WIR (`intervention_journal`) — tasks that are **not**
authorized in the T3 gate. Their domain-record column schemas are **not specified** by any frozen
document (only the shared `*_intents` shape in §3.1 is), so creating them now would require doing
T2/T5 schema-design work, which the T3 boundary forbids.

## 2. The deviation from `DEP-RPH3 §3/§3.1` (stated honestly)

The frozen `DEP-RPH3 §3` table pins `migrations/security/0001_security_spine.sql` to **all** the
security-spine tables, and §3.1's crash-recovery paragraph says "domain + intent + journal tables are
created in the **single** `0001_security_spine.sql` transaction." A migration that creates only the
three approval tables **does deviate from that literal wording** — it is not the all-tables `0001` the
frozen text describes, and (because a SHA-pinned, already-applied migration cannot later be edited) the
permission/tool/journal tables will arrive in **subsequent** versioned migrations (`0002+`) rather than
inside `0001`. This note does **not** claim the deviation is invisible; it claims it is **bounded and
safe** (§3) and must be **formally reconciled** (§4).

**Point-of-fact confirmation (requested by the operator):** the approval-only migration **is a recorded
deviation from the frozen §3/§3.1 wording**, not a silent conformance. It preserves every frozen
*invariant* (see §3) but not the frozen *literal single-file table inventory*; that inventory needs a
formal amendment (§4). T3 deliberately does **not** self-certify this away.

## 3. Why the deviation is bounded and safe (no frozen invariant is broken)

- **Store boundary preserved (ODI-RPH3-01).** The approval tables live in the PH-3-owned security-spine
  store, **not** the frozen runtime-state DB. R1 is preserved: no PH-3 code writes the runtime DB.
- **Single-writer discipline preserved (§4A).** `CMP-APPROVAL` is the sole writer of `approval_*` via
  the private, un-exported `_ApprovalWriter`, whose connection installs an authorizer that denies any
  write outside the three approval tables. Consumers get a `mode=ro` reader. No cross-domain writer.
- **Intent shape preserved verbatim (§3.1).** `approval_intents` matches the frozen column/CHECK/index
  spec exactly. The audit store (`0001_audit_chain.sql`, RPH3-T4) is unchanged.
- **XSC-RPH3 invariants preserved.** Every enqueue/decide/consume/revoke/expire is a Class-1 operation:
  a durable intent + a non-authoritative `PENDING` mutation, then a durable completion audit
  (commit point, INV-1), then a flip to `COMMITTED` (INV-2); startup reconciliation rolls each `PENDING`
  intent forward (audit present) or back (audit absent) before serving (INV-3); the audit chain is
  verified first (invalid ⇒ fail closed).
- **Runner preserved.** The migration applies under the same PH-1 SHA-256-pinned transactional runner;
  a mid-apply failure leaves no partial schema and no `schema_migrations` version row.
- **End-state inventory unchanged.** The *set* of tables the security-spine store will ultimately hold
  is exactly the frozen §3 inventory. Only the *packaging* (one file vs. per-task files) diverges.

## 4. Required reconciliation (planning debt — must be resolved, not absorbed)

Because a SHA-pinned `0001` cannot be retro-edited, the frozen "single `0001` = all tables" wording can
no longer be met literally once this approval-only `0001` is committed. When RPH3-T2 / RPH3-T5 / WIR are
authorized, **`DEP-RPH3 §3/§3.1` must be formally amended** (through the normal change process, with
operator sign-off — not unilaterally mid-task) to describe the security-spine store as realized by an
**ordered set of per-task migrations** (`0001` approval, `0002` permission, `0003` tools, `0004`
watchdog-journal, or equivalent), each SHA-pinned, cumulatively yielding the same §3 inventory. Until
that amendment lands, this note is the standing disclosure of the divergence.

**Operator decision surface.** If instead the operator requires the literal single-file `0001` (all
tables in one transaction), T3's migration must be redesigned and this would necessarily pull
permission/tool schema-design (T2/T5) into T3's scope — which the current T3 boundary forbids. That
trade-off is the operator's to make; T3 chose the narrow, boundary-respecting migration and disclosed
the debt here.

## 5. Traceability

- Frozen normative source: `DEP-RPH3 §2/§3/§3.1/§4A`, `XSC-RPH3 §3 (Class 1)/§5/§10`, `approval-spec`.
- Implementation: `migrations/security/0001_security_spine.sql`, `src/factory/approval/**`.
- Divergence + resolution also recorded in `docs/planning/00-CONTINUATION-LEDGER.md` (RPH3-T3 entry).
- Verification: `docs/verification/roadmap-ph3-t3-approval-evidence.md`,
  `scripts/verify_roadmap_ph3_t3.py`.
