# PH-5 Pending Live-Gate Register

Work that is **out of scope for preinstallation** and remains gated behind installation and live
validation. Nothing below is claimed complete. Each item replaces a fake backend with a live one
under the *same* interface, or promotes Git's local enforcement into the live Promotion Service.

| Gate | Depends on | What remains | Blocked by |
|---|---|---|---|
| LG-5.1 Real WSL2 execution | installed WSL2 | run sandboxed commands under a real WSL2 distro | `NOT_AUTHORIZED`: WSL2_configuration |
| LG-5.2 Real Docker execution | installed Docker | provision/destroy real Linux containers via the live `SandboxBackend` | `NOT_AUTHORIZED`: Docker_execution |
| LG-5.3 Live container identity validation | live runtime | assert real non-root uid/gid, dropped capabilities, and namespaces at runtime | live sandbox |
| LG-5.4 Live mount validation | live runtime | prove no writable host-project mount and staging-only exit on a real container | live sandbox |
| LG-5.5 Live network-namespace enforcement | live runtime | enforce default-deny + allowlist at the OS network layer, not just contract logic | live sandbox |
| LG-5.6 Live secret injection | secret backend / broker | inject real short-lived credentials at execution time; verify redaction end-to-end | live sandbox |
| LG-5.7 Live resource enforcement | cgroups / job objects | apply and verify hard CPU/RAM/GPU/disk/pid limits and termination thresholds | live sandbox |
| LG-5.8 Live restart & recovery | durable sandbox records | reconcile real orphaned sandboxes and verified checkpoints after a restart | live sandbox |
| LG-5.9 Promotion Service (PH-7) | staging + evidence spine | advance protected refs only through the gated Promotion Service; local offline promotion parity | PH-7 |
| LG-5.10 Durable Git baseline sync | approved remote + network | remote synchronization before task-branch creation; multi-repo atomic promotion | network + PH-7 |

**Promotion posture:** PH-5 preinstallation is `COMPLETE`; `PROM-PH5` is `NOT_AUTHORIZED`. Promotion
requires the live gates above plus separate operator authorization, exactly as RPH-3 required.
