# 01 — Host / Environment Inventory (read-only)

The inventory is produced by `scripts/live_gate/run_readiness.py`, which performs **only** read-only
probes (`--version` / `list` / `status` queries and Python stdlib inspection). It writes a
**redacted** JSON report to the git-ignored `.livegate-out/readiness.json`. Nothing is installed or
started.

## How to run (on the WSL2 target host)

```bash
python scripts/live_gate/run_readiness.py      # exit 0 iff every mandatory gate is PASS
cat .livegate-out/readiness.json               # redacted; safe to attach to an evidence record
```

## Redaction

Before anything is written or printed, `factory.livegate.redaction` masks credentials
(tokens/keys/passwords/PEM blocks), home paths (`/home/<user>` → `/home/[USER]`), and routable IPv4
literals (→ `a.b.x.x`), preserving only documentation/infra literals (`127.0.0.1`, `0.0.0.0`,
`169.254.169.254`). Over-redaction is acceptable; leaking a secret is not.

## Captured facts (advisory)

`system`, `release`, `machine`, `python`, `processor`. These are advisory context, not a gate — the
inventory check is non-mandatory. The mandatory gates are Docker, WSL2, NVIDIA/CUDA, Ollama models,
and (first) the SQLite engine floor.

## Builder-container baseline (NOT the target host)

Running the probe inside the ephemeral Linux builder container (for artifact validation only)
produced: SQLite `FAIL` (3.50.4), Docker `PASS` (read-only `--version`), WSL2/NVIDIA/Ollama
`UNAVAILABLE`, overall **NOT READY** — the honest result, because this container is not the WSL2
live target. The authoritative inventory must be captured on the operator's WSL2 host.
