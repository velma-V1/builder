# 08 — Consolidated Operator Decisions & Actions (ONE LIST)

Every item below requires **explicit operator authorization**. Nothing here has been executed.
Items are ordered; **#1 (SQLite) is the mandatory first gate** — no durable store activates and no
phase promotes until it is `PASS`.

| # | Decision / action | Type | Blocks | Reference |
|---|---|---|---|---|
| 1 | **SQLite — Option A SELECTED (upgrade Python-linked engine to ≥ 3.51.3), execution deferred.** Option B not selected. Read the exact version/URL/**SHA3-256** from official SQLite data; follow the per-interpreter runbook; re-run readiness until `sqlite-engine-floor` is `PASS`. If no official release ≥ 3.51.3 exists yet, STOP (do not lower the floor). | Host change (operator-executed) | ALL durable stores; PH-4/PH-6 live | 05, 10 |
| 2 | Install / confirm **Docker Engine ≥ 24.0** on the WSL2 host and confirm cgroup v2. | Host change | PH-5, PH-6 live | 02 |
| 3 | Confirm **WSL2 is the default** (`Default Version: 2`) and the distro is provisioned. | Host confirm | PH-5, PH-6 live | 02 |
| 4 | Install / confirm **NVIDIA driver + CUDA ≥ 12.0** in WSL2, GPU passthrough, and the NVIDIA Container Toolkit. | Host change | PH-4 GPU-heavy, PH-6 | 03 |
| 5 | Install **Ollama** and pull approved local models (`qwen3:8b`, `qwen3:14b`); confirm no excluded model. | Host change | PH-4 live | 04 |
| 6 | Approve the **image digests** to replace `__PINNED_DIGEST__` in the Compose templates (pin by `@sha256:`). | Decision | PH-5, PH-6 live | 02, deploy/compose |
| 7 | Authorize **PH-4 live runtime integration** (install → test → verify → record) after gates 1,4,5 pass. | Authorization | Promotion PH-4 | 06 |
| 8 | Authorize **PH-5 live sandbox integration** after gates 1,2,3,6 pass. | Authorization | Promotion PH-5 | 06 |
| 9 | Authorize **PH-6 live full integration** after PH-4 and PH-5 are verified. | Authorization | Promotion PH-6 | 06 |

## Decisions needing your explicit choice

- **SQLite path:** ✅ **DECIDED — Option A (upgrade to ≥ 3.51.3).** Option B (backport) not selected.
  Remaining: execute on the target host (item #1) and re-run the readiness probe.
- **Egress policy for hosted routes:** confirm which hosted providers (Groq / Cerebras / NVIDIA) are
  authorized through the broker, and how their credentials are provisioned to the secret broker.
- **Sequencing:** confirm phases are integrated independently in order PH-4 → PH-5 → PH-6, each with
  its own separate authorization and evidence record.

## What remains blocked until you act

`SQLITE_REMEDIATION = PREPARED_NOT_EXECUTED`; `PH4/PH5/PH6_LIVE_*_INTEGRATION = PENDING`;
`PROM_PH4/PH5/PH6 = NOT_AUTHORIZED`. This document is the single place to grant the authorizations
above; grant them one at a time so each change stays reversible and independently recorded.
