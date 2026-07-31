"""Prerequisite manifest + fail-closed evaluation (preinstall preparation).

Declares the host prerequisites the live phase needs and evaluates a *detected* version against a
required floor. Detection itself happens read-only on the host (readiness runner); this module is
the pure decision layer so it is deterministic and unit-tested. An **unknown** prerequisite name
fails closed (it is never silently treated as satisfied).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from factory.livegate.models import CheckStatus


@dataclass(frozen=True, slots=True)
class Prerequisite:
    name: str
    minimum: tuple[int, ...]
    mandatory: bool
    rationale: str


#: The authoritative prerequisite manifest. Versions mirror the readiness floors so the two cannot
#: drift apart in intent (the readiness runner is the on-host detector; this is the declared floor).
PREREQUISITES: tuple[Prerequisite, ...] = (
    Prerequisite("wsl2", (2,), True, "Decision C: WSL2 is the only supported Linux substrate"),
    Prerequisite("docker", (24, 0, 0), True, "Compose v2 + cgroup-v2 resource limits"),
    Prerequisite("nvidia_cuda", (12, 0), True, "GPU-heavy roles (qwen3:14b, aider) need CUDA >=12"),
    Prerequisite("ollama", (0, 1, 0), True, "local model runtime for approved local models"),
    Prerequisite("python", (3, 12), True, "factory targets CPython 3.12"),
    Prerequisite("uv", (0, 4, 0), True, "reproducible, locked dependency management"),
    Prerequisite("sqlite", (3, 51, 3), True, "durable-store engine floor (fail-closed gate)"),
    Prerequisite("git", (2, 30, 0), True, "controlled repository operations"),
)

_BY_NAME: dict[str, Prerequisite] = {p.name: p for p in PREREQUISITES}


def get_prerequisite(name: str) -> Prerequisite:
    """Return the declared prerequisite, or raise ``KeyError`` for an unknown name (fail closed)."""
    return _BY_NAME[name]


def evaluate_prerequisite(name: str, detected: tuple[int, ...] | None) -> CheckStatus:
    """Evaluate a detected version against the declared floor.

    * unknown name → ``ERROR`` (fail closed; never silently satisfied);
    * not detected (``None``) → ``UNAVAILABLE``;
    * detected < floor → ``FAIL``;
    * detected >= floor → ``PASS``.
    """
    prereq = _BY_NAME.get(name)
    if prereq is None:
        return CheckStatus.ERROR
    if detected is None:
        return CheckStatus.UNAVAILABLE
    return CheckStatus.PASS if detected >= prereq.minimum else CheckStatus.FAIL


def unmet_mandatory(detected: Mapping[str, tuple[int, ...] | None]) -> tuple[str, ...]:
    """Return the names of mandatory prerequisites that are not ``PASS`` given a detection map.

    Any mandatory prerequisite absent from ``detected`` is treated as ``UNAVAILABLE`` (unmet) — an
    omission cannot pass. Names not in the manifest are reported as unmet (fail closed).
    """
    unmet: list[str] = []
    for prereq in PREREQUISITES:
        if not prereq.mandatory:
            continue
        if evaluate_prerequisite(prereq.name, detected.get(prereq.name)) is not CheckStatus.PASS:
            unmet.append(prereq.name)
    for name in detected:
        if name not in _BY_NAME:
            unmet.append(f"unknown:{name}")
    return tuple(unmet)
