# 11 — Preinstallation Completion

**`PREINSTALLATION_PACKAGE := COMPLETE` · `PC_IMPLEMENTATION := NOT_STARTED`.** This records the
finished preinstallation package. No software, service, container, network, model, or durable store
was installed, started, pulled, or activated. No phase was promoted. No change was made to any target
PC.

## Repo anchors

| Anchor | Value |
|---|---|
| Repository | `velma-V1/builder` |
| Working branch | `claude/ph4-ph5-ph6-preinstall` |
| `origin/main` | `04e7ff4714568a7bc2b26e4590ccb923ebd6b014` (unchanged) |
| PR #11 | **merged** (its merge commit is `04e7ff4`; source parent `4c6b5196`) |
| Stage-3 base commit | `3ca06ce` (this completion work is committed on top) |
| Draft PR (this work) | opened `claude/ph4-ph5-ph6-preinstall → main`, **not merged** |

## Completed work

- **Static hardening** (merged) + **Stage-3 live-gate preparation** (`factory.livegate`, readiness
  runner, compose templates, durable schema, acceptance matrices, evidence docs).
- **SQLite remediation corrected** (Option A selected, execution deferred): SHA3-256 verification,
  official source-of-truth, removed the guessed `2025/` URL and `sha256sum`, per-interpreter paths
  (`uv_managed | distro | custom`), venv-rebuild-on-interpreter-change, authoritative Python check.
- **Preinstall package** (`factory.preinstall`): prerequisite manifest (fail-closed), interpreter
  classification + linked-SQLite detection, local-only network policy (hosted egress disabled),
  phase-order enforcement (PH-4→PH-5→PH-6), rollback completeness, dry-run-by-default installer
  framework, source checksum manifest (`deploy/preinstall/source-checksums.sha256`).
- **Preinstall docs** (`docs/preinstall/00..10`) + this completion doc; compose README; evidence
  templates.
- **Tests + verifiers**: `tests/preinstall/*`, `tests/livegate/*`, `scripts/verify_stage3_livegate_prep.py`,
  `scripts/verify_preinstall_complete.py`.

## Remaining PC (target-host) actions

Everything requiring a host is deferred to the operator (see `docs/live-gate/08` — the single action
list). In order: (1) upgrade SQLite ≥ 3.51.3 on WSL2; (2) confirm Docker/WSL2/NVIDIA-CUDA; (3) install
Ollama + pull `qwen3:8b`, `qwen3:14b`; (4) run readiness until all mandatory gates PASS; (5) authorize
PH-4 only.

## Install order

`SQLite gate PASS → PH-4 → PH-5 → PH-6`, each installed/tested/verified/recorded and authorized
independently (`factory.preinstall.phase_order`; `docs/preinstall/10`).

## Evidence requirements

Per readiness gate and per acceptance criterion, capture a redacted record
(`docs/live-gate/09-evidence-record-templates.md`); the readiness runner writes redacted output to
the git-ignored `.livegate-out/readiness.json`. A phase promotes only when the SQLite gate is PASS,
its readiness gates are PASS, and every acceptance criterion has a filled record.

## Rollback boundaries

Every mutating step captures state before change and has a concrete rollback (`docs/preinstall/08`,
`docs/live-gate/07`). A rolled-back SQLite change returns the gate to `FAIL` (safe). Rollback never
rewrites git history or force-pushes.

## Unresolved risks

- **SQLite availability:** this environment cannot reach `sqlite.org`, so the exact current release
  ≥ 3.51.3 and its SHA3-256 were **not** verified here. If no official release ≥ 3.51.3 exists yet,
  Option A cannot complete — STOP; do not lower the floor or use an unapproved build.
- **uv-managed interpreter linkage:** a uv-standalone Python may statically bundle SQLite; an OS
  upgrade or `LD_PRELOAD` may not move it — a venv rebuild on a suitable interpreter is required.
- **GPU/VRAM sufficiency** for one resident GPU-heavy model at a time — operator confirms on host.

## Prohibited actions (still in force)

No install / host mutation / services / containers / model pulls / live API / durable-store
activation / phase promotion; do not touch PR #10; push only the source branch; never merge or push
to `main`.

## Promotion state

`PH4/PH5/PH6_LIVE_*_INTEGRATION := PENDING` · `PROM_PH4/PH5/PH6 := NOT_AUTHORIZED` ·
`SQLITE_REMEDIATION := OPTION_A_SELECTED_EXECUTION_DEFERRED` · `PC_IMPLEMENTATION := NOT_STARTED`.

## Future first PC command

The first thing to run on the WSL2 target host (after `git pull` of this branch):

```bash
.venv/bin/python -c "import sqlite3; print(sqlite3.sqlite_version)"   # authoritative baseline
# then follow docs/live-gate/10-sqlite-upgrade-runbook-wsl2.md
```
