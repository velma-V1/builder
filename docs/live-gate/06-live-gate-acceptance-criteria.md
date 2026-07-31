# 06 — PH-4 / PH-5 / PH-6 Live-Gate Acceptance Matrices

Each criterion must be demonstrated **on live infrastructure** before its phase may be promoted.
Every live criterion has a `fake_parity` pointer to the deterministic test that already proves the
same invariant against the fakes — so live integration is a **confirmation on real components**, not
a first test. The machine-readable source of truth is `factory.livegate.acceptance`
(`tests/livegate/test_acceptance.py` checks it is well-formed: 18 criteria, unique ids, all
mandatory, all with parity pointers).

Evidence kinds: `runtime_log`, `container_inspect`, `ledger_query`, `network_trace`, `repo_state`.

## PH-4 — Model & coding-tool routing / quotas (live runtime)

| ID | Invariant to demonstrate live | Evidence | Fake parity |
|---|---|---|---|
| AC4.1 | Real Ollama dispatcher (`qwen3:8b`) answers a routed request following roster order. | runtime_log | tests/routing/integration :: route order honored |
| AC4.2 | Single-active GPU-heavy reservation serializes concurrent `qwen3:14b`/Aider requests. | ledger_query | tests/routing/unit :: single-active GPU-heavy |
| AC4.3 | Quota charged on every real attempt (success **and** failure); accounting == ledger. | ledger_query | tests/routing/failure_paths :: all-outcome accounting |
| AC4.4 | No excluded model (`glm-4.7`) reachable at runtime; never invoked. | runtime_log | verify_ph4 :: GLM exclusion |
| AC4.5 | Fallback selects an approved secondary only; no silent substitution. | runtime_log | verify_ph4 :: approved-only fallback |
| AC4.6 | Kill mid-flight then restart: history rebuilt, sequence advanced, no ID collision. | ledger_query | tests/routing/integration :: restart hardening |

## PH-5 — Git / sandbox / secret / network isolation (live sandbox)

| ID | Invariant to demonstrate live | Evidence | Fake parity |
|---|---|---|---|
| AC5.1 | Real worker container runs read-only-rootfs, caps-dropped, no-new-privs, non-root. | container_inspect | tests/sandbox :: hardened topology |
| AC5.2 | Internal-network worker cannot reach the internet; only the broker egresses. | network_trace | tests/network :: default-deny + broker |
| AC5.3 | Infrastructure destinations denied unless `allow_infrastructure` set. | network_trace | tests/network :: infra destination denial |
| AC5.4 | Checkpoint commits only owned paths on a real repo; protected-ref writes refused. | repo_state | tests/git :: owned-path + protected-ref |
| AC5.5 | Secret broker redacts + revoke-and-forgets against a real secret store. | runtime_log | tests/secret :: redaction + revoke-and-forget |
| AC5.6 | Live launcher refuses published-ports / runtime-socket / host-network specs. | container_inspect | tests/sandbox :: prohibited-privilege denials |

## PH-6 — Three-workstream full integration (live)

| ID | Invariant to demonstrate live | Evidence | Fake parity |
|---|---|---|---|
| AC6.1 | Three real workstreams admitted (cap 3), independence enforced; a 4th denied. | runtime_log | tests/workstream :: admission cap + independence |
| AC6.2 | Single-writer ownership holds under real concurrency; no lost update. | ledger_query | tests/workstream :: ownership single-writer |
| AC6.3 | Lane state machine drives real tasks; illegal/inconsistent transitions fail closed. | runtime_log | tests/workstream :: lane lifecycle |
| AC6.4 | Conflict detector catches semantic (non-file) conflicts on real branches. | repo_state | tests/workstream :: conflict beyond files |
| AC6.5 | Three real worker failures quarantine the lane; transient failures excluded. | runtime_log | tests/workstream :: 3-failure quarantine |
| AC6.6 | Integration coordinator assigns remediation and never edits source on a real run. | repo_state | tests/integration :: coordinator never edits source |

## Promotion rule

A phase is promoted **only** after (a) the SQLite gate is `PASS`, (b) all readiness gates for that
phase are `PASS`, and (c) every acceptance criterion for that phase has a filled evidence record
(document 09). Phases are installed, tested, verified, and recorded **independently** — PH-4, then
PH-5, then PH-6 — each behind its own separate authorization.
