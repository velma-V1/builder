# Stage-3 Live-Gate Preparation — Evidence Package (Overview)

**Status:** `STAGE_3_LIVE_GATE_PREPARATION_COMPLETE — AWAITING_OPERATOR_REMEDIATION_AUTHORIZATION`

This package prepares — and only prepares — the live integration of PH-4/PH-5/PH-6. **Nothing was
installed, started, configured, pulled, upgraded, or activated.** No live model, sandbox, network,
GPU, or durable store was exercised. Phase promotion remains `NOT_AUTHORIZED`.

## Final state (asserted)

| Marker | Value |
|---|---|
| `SQLITE_REMEDIATION` | `OPTION_A_SELECTED_EXECUTION_DEFERRED` — upgrade selected; runs on the WSL2 target host (this session cannot reach it) |
| `PH4_LIVE_RUNTIME_INTEGRATION` | `PENDING` |
| `PH5_LIVE_SANDBOX_INTEGRATION` | `PENDING` |
| `PH6_LIVE_INTEGRATION` | `PENDING` |
| `PROM_PH4` / `PROM_PH5` / `PROM_PH6` | `NOT_AUTHORIZED` |

## Documents

| # | Document | Purpose |
|---|---|---|
| 01 | `01-host-environment-inventory.md` | Read-only host/environment inventory (how to run; redaction). |
| 02 | `02-wsl2-docker-readiness.md` | WSL2 + Docker readiness report and floors. |
| 03 | `03-nvidia-cuda-compatibility.md` | NVIDIA driver / CUDA compatibility report. |
| 04 | `04-ollama-model-availability.md` | Ollama daemon + approved-model availability. |
| 05 | `05-sqlite-compliance-and-remediation.md` | **First gate.** Compliance + PREPARED (not executed) remediation. |
| 06 | `06-live-gate-acceptance-criteria.md` | PH-4/5/6 acceptance matrices (18 criteria). |
| 07 | `07-rollback-and-cleanup.md` | Rollback and cleanup procedure for any future live step. |
| 08 | `08-OPERATOR-ACTIONS-REQUIRED.md` | **One consolidated list** of operator decisions/actions. |
| 09 | `09-evidence-record-templates.md` | Blank evidence records to fill during live acceptance. |
| 10 | `10-sqlite-upgrade-runbook-wsl2.md` | Turnkey WSL2 runbook for the authorized Option-A SQLite upgrade. |

## Code artifacts (all read-only / unapplied)

- `src/factory/livegate/` — readiness models, redaction, SQLite compliance, compose topology
  validator, version-probe parsers, live-adapter contract, durable-schema pinning, acceptance data.
- `scripts/live_gate/run_readiness.py` — read-only readiness runner (writes to git-ignored
  `.livegate-out/`).
- `deploy/compose/*.compose.yaml` — **unapplied** hardened topology templates + README.
- `deploy/schemas/durable/0001_execution_journal.sql` — **unapplied** SHA-pinned durable schema.
- `scripts/verify_stage3_livegate_prep.py` — deterministic Stage-3 gate (no live probes).
- `tests/livegate/` — full deterministic coverage of the above.

## What this package does NOT do

It does not upgrade or replace SQLite; install packages/components; modify Python, WSL2, Docker,
Windows, Ollama, NVIDIA, or host configuration; activate durable stores; begin PH-4/5/6 live
integration; or authorize phase promotion. Each of those requires separate, explicit operator
authorization (see document 08).
