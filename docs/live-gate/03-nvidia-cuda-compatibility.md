# 03 — NVIDIA / CUDA Compatibility

GPU-heavy roles (`qwen3:14b` supervisor, the Aider coding worker) require a working NVIDIA driver +
CUDA runtime in WSL2. This is a read-only compatibility check; installing the driver/CUDA/container
toolkit is an operator action (document 08).

## Gate `nvidia-cuda` (mandatory)

| Item | Value |
|---|---|
| Probe | `nvidia-smi` (read-only) |
| Parsed | `Driver Version`, `CUDA Version` (`factory.livegate.version_probe.parse_nvidia_smi`) |
| CUDA floor | **12.0** (`MIN_CUDA_VERSION`) |
| PASS when | reported CUDA ≥ 12.0 |
| UNAVAILABLE when | `nvidia-smi` not found (install the NVIDIA driver + CUDA on the host) |

Rationale: current Ollama GPU builds target CUDA 12.x; a ≥ 12.0 runtime with a matching recent
driver covers the rostered local GPU models. The exact driver→CUDA mapping is reported by
`nvidia-smi` itself and captured verbatim in the readiness facts.

## Additional operator confirmations (manual, at live time)

- WSL2 GPU passthrough is enabled (`/dev/dxg` present) and `nvidia-smi` works **inside** the WSL2
  distro, not only on the Windows host.
- The NVIDIA Container Toolkit is installed so Docker can expose the GPU
  (`docker run --gpus all ... nvidia-smi` succeeds) — perform under authorization, not during prep.
- VRAM is sufficient for the concurrently-resident GPU-heavy model(s) given the single-active
  GPU-heavy reservation policy (only one heavy reservation at a time — see PH-4).

## Note on the single-active GPU-heavy policy

PH-4 enforces a single active GPU-heavy reservation. Live acceptance criterion **AC4.2** confirms
this serializes concurrent `qwen3:14b`/Aider requests on the real GPU; the deterministic parity test
already proves the policy against the fakes.
