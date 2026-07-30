# PH-6 Simulated Integration Point 3 (IP-3) Report

**Status:** `SIMULATED — LIVE_INTEGRATION_PENDING`. This is a deterministic, offline demonstration of
three parallel workstreams integrating through the PH-6 engine against the PH-4/PH-5 fakes. It is
**not** a live integration and makes no live-runtime claim.

## What the demonstration exercises

`factory.integration.run_simulated_ip3()` runs the full PH-6 loop:

1. **Admission (≤3 + independence).** Three independent workstreams (`WS1`, `WS2`, `WS3`) with
   disjoint scopes, distinct owned contracts, no dependencies, and a shared baseline are admitted. A
   fourth workstream is denied by the cap.
2. **Ownership leases.** Each workstream acquires a single-writer lease over its own scope file.
3. **Isolated checkout assignment.** Each lane receives a distinct worktree checkout id
   (`checkouts_isolated == True`).
4. **Fake sandbox assignment (PH-5).** Each workstream provisions a distinct sandbox via
   `FakeWslDockerBackend` (`sbx-1`, `sbx-2`, `sbx-3`).
5. **Fake router assignment (PH-4).** Each workstream routes a `ROUTINE_CODING` task via `ModelRouter`
   (deterministic route `AIDER:aider`).
6. **Lane lifecycle.** Each lane advances PROPOSED → APPROVED → READY → ACTIVE → VERIFICATION →
   HANDOFF through the audited `LaneMachine`.
7. **Conflict detection.** The three change manifests are pairwise-checked; zero conflicts.
8. **Integration.** The `IntegrationCoordinator` confirms consistent baselines, passed local gates,
   and no conflicts, then combines the approved commits — **without editing any source** — and returns
   verdict `INTEGRATED`. Each lane then transitions HANDOFF → INTEGRATED.

## Recorded result (CPython 3.12.11, this environment)

| Field | Value |
|---|---|
| admitted | `("WS1", "WS2", "WS3")` |
| fourth_denied | `True` |
| checkouts_isolated | `True` |
| sandbox_ids | `("sbx-1", "sbx-2", "sbx-3")` |
| routes | `("AIDER:aider", "AIDER:aider", "AIDER:aider")` |
| conflicts | `0` |
| integration_verdict | `INTEGRATED` |
| promoted | `("WS1", "WS2", "WS3")` |
| final_lane_states | `("INTEGRATED", "INTEGRATED", "INTEGRATED")` |
| coordinator_edits_source | `False` |

Asserted by `tests/integration/test_ip3_demo.py::test_simulated_ip3_end_to_end` and by
`scripts/verify_ph6_preinstall.py` check "Simulated three-workstream demonstration (IP-3)".

## What remains for the live IP-3

The live IP-3 replaces the fakes with live backends (real sandboxes, real routing, real Git isolation)
and runs real cross-workstream integration tests before promotion. See
`ph6-pending-live-gate-register.md`. `PROM-PH6 := NOT_AUTHORIZED`.
