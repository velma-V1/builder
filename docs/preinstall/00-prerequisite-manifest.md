# Preinstall 00 — Prerequisite Manifest

Authoritative floors for the live-phase host. Source of truth in code:
`factory.preinstall.prerequisites.PREREQUISITES` (fail-closed: an unknown prerequisite is never
treated as satisfied). Detection is read-only on the host via `scripts/live_gate/run_readiness.py`.

| Prerequisite | Minimum | Mandatory | Why |
|---|---|---|---|
| `wsl2` | 2 | yes | Decision C: WSL2 is the only supported Linux substrate |
| `docker` | 24.0.0 | yes | Compose v2 + cgroup-v2 resource limits |
| `nvidia_cuda` | 12.0 | yes | GPU-heavy roles (`qwen3:14b`, `aider`) need CUDA ≥ 12 |
| `ollama` | 0.1.0 | yes | local model runtime for approved local models |
| `python` | 3.12 | yes | factory targets CPython 3.12 |
| `uv` | 0.4.0 | yes | reproducible, locked dependency management |
| `sqlite` | 3.51.3 | yes | durable-store engine floor (fail-closed gate) |
| `git` | 2.30.0 | yes | controlled repository operations |

**Fail-closed rule:** any mandatory prerequisite that is missing, below floor, or unknown blocks the
live gate. `factory.preinstall.prerequisites.unmet_mandatory()` returns the offending names; an
unknown name is reported as `unknown:<name>` and never passes.
