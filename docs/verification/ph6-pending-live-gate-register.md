# PH-6 Pending Live-Gate Register

Work that is **out of scope for the simulated core** and remains gated behind installation and live
validation. Nothing below is claimed complete. The simulated core proves the workstream engine's
logic against deterministic fakes; the live gates wire real backends and run real integration.

| Gate | Depends on | What remains | Blocked by |
|---|---|---|---|
| LG-6.1 Live isolated checkouts | PH-5 live Git worktrees | assign real Git worktrees per lane on a real repo | live sandbox / Git host |
| LG-6.2 Live sandbox assignment | PH-5 live WSL2/Docker | provision a real disposable sandbox per workstream | `NOT_AUTHORIZED`: Docker/WSL2 |
| LG-6.3 Live router assignment | PH-4 live Ollama/Aider | route real coding work to a live model/worker | live runtime |
| LG-6.4 Live cross-workstream integration (IP-3) | live backends + PH-7 | run real cross-workstream integration tests before promotion | PH-7 Promotion/Integration Service |
| LG-6.5 Live checkpoint contents | durable checkpoint store | populate the full `01D §3.6` verified-checkpoint contents from real workspace state | live sandbox |
| LG-6.6 Live priority interruption | live scheduler + sandboxes | enforce the 5/15/30-minute real-time deadlines and checkpointed pause on live lanes | live runtime |
| LG-6.7 Live quarantine actions | live orchestration | quarantine a real workstream and route it to operator review | live runtime + PH-7 |
| LG-6.8 Integration coordinator promotion | PH-7 Promotion Service | combine approved commits through the real Promotion/Integration Service | PH-7 |

**Promotion posture:** PH-6 simulated core is `COMPLETE`; `PROM-PH6` is `NOT_AUTHORIZED`. Promotion
requires the live gates above plus separate operator authorization, exactly as RPH-3 required.
