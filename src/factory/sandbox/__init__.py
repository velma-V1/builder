"""PH-5 (Task 5.2) — non-root WSL2+Docker sandbox lifecycle (preinstallation).

Backend interface + deterministic fake backend + isolation policy: per-workstream disposable
sandboxes, non-root identity, prohibited-privilege denial, no writable host-project mount, hard
resource limits, Windows-native exclusion (Decision C), runtime-unavailable results, and
boundary-failure destroy + security clearance. Live WSL2/Docker execution is LIVE_SANDBOX_PENDING.
"""

from __future__ import annotations

from factory.sandbox.backend import SandboxBackend
from factory.sandbox.errors import SandboxError
from factory.sandbox.fake_backend import FakeWslDockerBackend
from factory.sandbox.models import (
    BoundaryFailureReport,
    MountMode,
    MountSpec,
    NetworkPolicy,
    PolicyViolation,
    ResourceLimits,
    SandboxHandle,
    SandboxIdentity,
    SandboxSpec,
    SandboxStatus,
)
from factory.sandbox.policy import evaluate_spec

__all__ = [
    "BoundaryFailureReport",
    "FakeWslDockerBackend",
    "MountMode",
    "MountSpec",
    "NetworkPolicy",
    "PolicyViolation",
    "ResourceLimits",
    "SandboxBackend",
    "SandboxError",
    "SandboxHandle",
    "SandboxIdentity",
    "SandboxSpec",
    "SandboxStatus",
    "evaluate_spec",
]
