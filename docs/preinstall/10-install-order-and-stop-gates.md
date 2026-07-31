# Preinstall 10 — Install Order, Stop Gates & Acceptance Evidence

## Strict install order (enforced in code)

`factory.preinstall.phase_order` enforces **PH-4 → PH-5 → PH-6**. A phase is eligible only when every
earlier phase is complete; gaps are not skippable; an already-complete phase is rejected. Each phase
is installed, tested, verified, and recorded **independently** before the next is authorized.

```
SQLite gate PASS  →  PH-4 (install → test → verify → record → authorize)
                  →  PH-5 (only after PH-4 passes independently)
                  →  PH-6 (only after PH-5 passes independently)
```

## Operator stop gates (must hold before proceeding)

1. **SQLite compliance** — `.venv/bin/python` reports SQLite ≥ 3.51.3; gate `PASS`. **First; blocks all.**
2. **All mandatory readiness gates PASS** — WSL2, Docker, NVIDIA/CUDA, Ollama + approved models.
3. **Per-phase acceptance** — every criterion in the phase's matrix has a filled evidence record.
4. **Explicit authorization** — a separate operator authorization per phase; never implied.

Stop immediately if: SQLite < 3.51.3, any mandatory gate ≠ PASS, repository drift, an unapproved
remediation, or any request to activate durable storage / start PH components before their gate.

## Acceptance evidence matrix

The PH-4/5/6 acceptance criteria (18 total, each with a deterministic fake-parity pointer) are in
`factory.livegate.acceptance` and rendered in `docs/live-gate/06-live-gate-acceptance-criteria.md`.
Evidence is captured per criterion using the templates in
`docs/live-gate/09-evidence-record-templates.md`.

## Hosted egress

`HOSTED_EGRESS := DISABLED_BY_DEFAULT` (Preinstall 06). Enabling it and approving specific hosted
providers is a separate operator decision, off unless explicitly turned on.
