"""Pure parsers + compatibility decisions for host readiness probes.

Subprocess/HTTP I/O lives in the script layer (``scripts/live_gate``). This module only *parses*
already-captured tool output and decides compatibility, so every decision is deterministic and unit
tested without a live host. All floors are conservative and documented alongside each evaluator.
"""

from __future__ import annotations

import re

from factory.livegate.models import CheckStatus, ReadinessCheck
from factory.routing.roster import EXCLUDED_MODEL_IDS, QWEN_8B, QWEN_14B

#: Documented minimum floors (target host — Decision C: WSL2 + Docker Linux).
MIN_DOCKER_VERSION: tuple[int, int, int] = (24, 0, 0)
MIN_CUDA_VERSION: tuple[int, int] = (12, 0)
REQUIRED_WSL_DEFAULT_VERSION = 2
#: Approved *local* model tags that must be present in Ollama for PH-4 live routing.
APPROVED_LOCAL_MODELS: frozenset[str] = frozenset({QWEN_8B, QWEN_14B})

_DOCKER_RE = re.compile(r"Docker version (\d+)\.(\d+)\.(\d+)")
_CUDA_RE = re.compile(r"CUDA Version:\s*(\d+)\.(\d+)")
_DRIVER_RE = re.compile(r"Driver Version:\s*([\d.]+)")


#: U+FEFF (ZERO WIDTH NO-BREAK SPACE / BOM), built via chr() to avoid any ambiguity from escape
#: sequences in string literals.
_BOM = chr(0xFEFF)


def _clean_probe_text(text: str) -> str:
    """Remove a leading Unicode BOM and embedded NUL characters."""
    return text.removeprefix(_BOM).replace("\x00", "")


def parse_docker_version(stdout: str) -> tuple[int, int, int] | None:
    match = _DOCKER_RE.search(stdout)
    if match is None:
        return None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def evaluate_docker(
    stdout: str, *, minimum: tuple[int, int, int] = MIN_DOCKER_VERSION
) -> ReadinessCheck:
    version = parse_docker_version(stdout)
    if version is None:
        return ReadinessCheck(
            "docker-engine", "Docker Engine present and current", CheckStatus.UNAVAILABLE,
            "docker not found / no parseable version; install Docker Engine on the WSL2 host",
            mandatory=True,
        )
    ok = version >= minimum
    ver = ".".join(str(p) for p in version)
    floor = ".".join(str(p) for p in minimum)
    return ReadinessCheck(
        "docker-engine", "Docker Engine present and current",
        CheckStatus.PASS if ok else CheckStatus.FAIL,
        f"Docker {ver} ({'meets' if ok else 'below'} {floor} floor)",
        mandatory=True, facts=(("docker_version", ver), ("floor", floor)),
    )


def evaluate_wsl(stdout: str, *, required: int = REQUIRED_WSL_DEFAULT_VERSION) -> ReadinessCheck:
    """Confirm the WSL default version is 2. ``stdout`` is ``wsl --status`` / ``wsl -l -v`` text.

    ``wsl.exe`` writes its console output as UTF-16LE; a caller that decodes it with a mismatched
    codec leaves the text interleaved with NUL characters (and sometimes a leading BOM), so the
    literal marker ``"Default Version:"`` never appears contiguously and the regex below would
    otherwise never match. ``stdout`` is cleaned defensively here so this parser is correct
    regardless of how the caller captured/decoded the raw bytes.
    """
    cleaned = _clean_probe_text(stdout)
    if not cleaned.strip():
        return ReadinessCheck(
            "wsl2-default", "WSL2 is the default distro version", CheckStatus.UNAVAILABLE,
            "wsl not found; this is expected off the Windows target host",
            mandatory=True,
        )
    match = re.search(r"Default Version:\s*(\d+)", cleaned)
    version = int(match.group(1)) if match else None
    ok = version == required
    return ReadinessCheck(
        "wsl2-default", "WSL2 is the default distro version",
        CheckStatus.PASS if ok else CheckStatus.FAIL,
        f"default WSL version = {version} (require {required})",
        mandatory=True, facts=(("default_version", str(version)),),
    )


def parse_nvidia_smi(stdout: str) -> tuple[tuple[int, int] | None, str | None]:
    """Return ``(cuda_version, driver_version)`` parsed from ``nvidia-smi`` header text.

    ``cuda_version`` is ``None`` both when no NVIDIA hardware/driver is present at all *and* when a
    driver-only install reports ``CUDA Version: N/A`` (no CUDA runtime component). Callers must
    consult ``driver_version`` to tell these two cases apart — see :func:`evaluate_nvidia`.
    """
    cleaned = _clean_probe_text(stdout)
    cuda_match = _CUDA_RE.search(cleaned)
    driver_match = _DRIVER_RE.search(cleaned)
    cuda = (int(cuda_match.group(1)), int(cuda_match.group(2))) if cuda_match else None
    driver = driver_match.group(1) if driver_match else None
    return (cuda, driver)


def evaluate_nvidia(
    stdout: str, *, minimum_cuda: tuple[int, int] = MIN_CUDA_VERSION
) -> ReadinessCheck:
    cuda, driver = parse_nvidia_smi(stdout)
    floor = ".".join(str(p) for p in minimum_cuda)
    if cuda is None and driver is None:
        return ReadinessCheck(
            "nvidia-cuda", "NVIDIA driver + CUDA support GPU-heavy roles", CheckStatus.UNAVAILABLE,
            "nvidia-smi not found / unparseable; install the NVIDIA driver + CUDA on the host",
            mandatory=True,
        )
    if cuda is None:
        # Driver detected but the CUDA runtime component is absent/unparseable — e.g. a driver-only
        # install reporting "CUDA Version: N/A". GPU hardware IS present, so the floor is a FAILURE
        # (not an absence): collapsing this into UNAVAILABLE would lose the driver-version fact and
        # misreport a real, non-compliant host identically to "no NVIDIA hardware at all".
        return ReadinessCheck(
            "nvidia-cuda", "NVIDIA driver + CUDA support GPU-heavy roles", CheckStatus.FAIL,
            f"NVIDIA driver {driver} detected but CUDA Version is unavailable (e.g. driver-only "
            f"install, no CUDA toolkit); floor {floor} requires the CUDA runtime component",
            mandatory=True,
            facts=(("driver_version", driver or "unknown"), ("cuda_version", "unavailable"),
                   ("floor", floor)),
        )
    ok = cuda >= minimum_cuda
    cuda_s = ".".join(str(p) for p in cuda)
    return ReadinessCheck(
        "nvidia-cuda", "NVIDIA driver + CUDA support GPU-heavy roles",
        CheckStatus.PASS if ok else CheckStatus.FAIL,
        f"CUDA {cuda_s} (driver {driver or 'unknown'}); {'meets' if ok else 'below'} {floor}",
        mandatory=True,
        facts=(("cuda_version", cuda_s), ("driver_version", driver or "unknown"), ("floor", floor)),
    )


def parse_ollama_list(stdout: str) -> tuple[str, ...]:
    """Parse ``ollama list`` output into the set of installed model tags (first column)."""
    tags: list[str] = []
    for line in stdout.splitlines():
        stripped = line.strip()
        if not stripped or stripped.lower().startswith("name"):
            continue
        tags.append(stripped.split()[0])
    return tuple(tags)


def evaluate_ollama_models(
    installed: tuple[str, ...],
    *,
    approved: frozenset[str] = APPROVED_LOCAL_MODELS,
    excluded: frozenset[str] = EXCLUDED_MODEL_IDS,
) -> ReadinessCheck:
    """PASS when every approved local model is present and no excluded model is installed."""
    installed_set = {t.lower() for t in installed}
    missing = sorted(m for m in approved if m.lower() not in installed_set)
    leaked = sorted(m for m in installed if m.lower() in {e.lower() for e in excluded})
    if not installed:
        return ReadinessCheck(
            "ollama-models", "Approved local models available; excluded absent",
            CheckStatus.UNAVAILABLE,
            "ollama not running / no models; pull approved models on the host before live PH-4",
            mandatory=True, facts=(("approved_required", ",".join(sorted(approved))),),
        )
    if leaked:
        return ReadinessCheck(
            "ollama-models", "Approved local models available; excluded absent", CheckStatus.FAIL,
            f"excluded model(s) present and must be removed: {leaked}",
            mandatory=True, facts=(("excluded_present", ",".join(leaked)),),
        )
    status = CheckStatus.PASS if not missing else CheckStatus.FAIL
    detail = "all approved local models present" if not missing else f"missing: {missing}"
    return ReadinessCheck(
        "ollama-models", "Approved local models available; excluded absent", status, detail,
        mandatory=True,
        facts=(
            ("installed", ",".join(sorted(installed))),
            ("missing", ",".join(missing) or "none"),
        ),
    )
