# Preinstall 04 — NVIDIA Runtime Plan

GPU-heavy roles (`qwen3:14b` supervisor, Aider coding worker) require a working NVIDIA driver + CUDA
in WSL2 and GPU exposure to Docker. Read-only readiness only; installation is an operator action.

## Requirements

- NVIDIA driver + **CUDA ≥ 12.0** reported by `nvidia-smi` (parsed by
  `factory.livegate.version_probe.parse_nvidia_smi`).
- WSL2 GPU passthrough (`/dev/dxg`); `nvidia-smi` works **inside** the distro.
- **NVIDIA Container Toolkit** so Docker can expose the GPU (`docker run --gpus all … nvidia-smi`).
  Install/verify under authorization — not during preinstall.

## Interaction with the single-active GPU-heavy policy

PH-4 enforces a single active GPU-heavy reservation. Live criterion **AC4.2** confirms concurrent
`qwen3:14b`/Aider requests serialize on the real GPU; the deterministic parity test already proves
the policy against the fakes. Confirm VRAM is sufficient for one resident GPU-heavy model at a time.

## Not done here

No driver, CUDA, or container-toolkit install; no `--gpus` container run; no GPU probe against a real
device from this preparation environment.
