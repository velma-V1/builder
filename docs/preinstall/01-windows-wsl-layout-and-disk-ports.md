# Preinstall 01 — Windows/WSL Layout, Disk & Port Inventory

Planning reference for the target host. Nothing here is applied; the operator confirms these on the
Windows 11 + WSL2 machine.

## Windows / WSL2 layout

- **Windows 11** host with WSL2 enabled; the factory runs **inside a WSL2 Linux distro** (Decision
  C). The Windows side runs no factory services directly.
- One dedicated factory distro (`wsl -l -v` shows `VERSION 2`). Docker Desktop with the WSL2 backend,
  or Docker Engine inside the distro, exposes the Docker socket **only inside the distro** — never
  bind-mounted into a container (enforced by the sandbox policy and compose validator).
- GPU passthrough: `/dev/dxg` present in the distro; `nvidia-smi` works **inside** WSL2.

## Disk inventory (plan)

| Area | Purpose | Notes |
|---|---|---|
| repo clone (`~/builder`) | source + venv | keep on the ext4 WSL2 filesystem, not `/mnt/c` |
| model store (Ollama) | local model blobs | large; ensure free space for `qwen3:8b` + `qwen3:14b` |
| durable store dir | SQLite journal (later) | git-ignored runtime path; inert until SQLite gate PASS |
| `.livegate-out/` | readiness output | git-ignored, redacted |

Confirm sufficient free space on the WSL2 ext4 volume before pulling models (models are multi-GB).

## Port inventory (local-only)

The topology publishes **no host ports** (enforced: compose `PUBLISHED_PORTS_DENIED`). Internal
service ports stay on the internal Docker network. Ollama's default local API (`11434`) is bound on
loopback inside the distro and is **not** published to the LAN. Any hosted egress is off by default
(see Preinstall 06). There are no inbound host ports to open in the Windows firewall for the factory.
