# 09 — Evidence Record Templates

Fill one record per readiness gate and per acceptance criterion during live integration. Keep all
output redacted (the readiness runner already redacts; redact any manual paste the same way). These
are blank templates — no live run has occurred.

## Readiness gate record

```
Gate id            : <sqlite-engine-floor | docker-engine | wsl2-default | nvidia-cuda | ollama-models>
Host               : <WSL2 distro / build>            (hostname redacted)
Date / operator    : <YYYY-MM-DD> / <name>
Probe command      : <exact read-only command>
Result             : <PASS | FAIL | UNAVAILABLE>
Facts (redacted)   : <version(s) / flags>
Readiness report   : .livegate-out/readiness.json  (attach redacted copy)
Notes              : <blockers, follow-ups>
```

## Acceptance criterion record

```
Criterion id       : <AC4.x | AC5.x | AC6.x>
Phase              : <PH-4 | PH-5 | PH-6>
Invariant          : <statement from doc 06>
Evidence kind      : <runtime_log | container_inspect | ledger_query | network_trace | repo_state>
Fake parity ref    : <deterministic test that proves the same invariant>
Live evidence      : <log excerpt / inspect output / query result — redacted>
Result             : <PASS | FAIL>
Date / operator    : <YYYY-MM-DD> / <name>
Rollback needed?   : <no | yes — see doc 07, describe restored state>
```

## Phase promotion record (one per phase, after all its criteria PASS)

```
Phase              : <PH-4 | PH-5 | PH-6>
SQLite gate        : PASS   (prerequisite; see doc 05)
Readiness gates    : <list — all PASS>
Acceptance records : <AC list — all PASS, linked>
Authorization      : <operator name + explicit authorization reference>
Promotion decision : PROM_PH<n> := AUTHORIZED   (only when everything above holds)
Date               : <YYYY-MM-DD>
```

## Rollback event record

```
Trigger            : <failed verification / regression / operator decision>
Step rolled back   : <exact change>
Rollback command   : <exact command from doc 07>
Restored state     : <verified end state, e.g. sqlite 3.50.4 / gate FAIL>
Date / operator    : <YYYY-MM-DD> / <name>
```
