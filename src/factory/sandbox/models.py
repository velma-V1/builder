"""Value objects for the PH-5 sandbox subsystem (``01E``).

Encodes the sandbox request/identity vocabulary and the prohibited-privilege surface. Decision C
(``01R``) is structural: a Windows-native spec is expressible only to be rejected — no
Windows-native execution path exists.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class SandboxStatus(StrEnum):
    PROVISIONED = "PROVISIONED"
    DESTROYED = "DESTROYED"
    FAILED = "FAILED"
    RUNTIME_UNAVAILABLE = "RUNTIME_UNAVAILABLE"


class MountMode(StrEnum):
    RO = "RO"
    RW = "RW"


class NetworkPolicy(StrEnum):
    DENY = "DENY"
    SCOPED = "SCOPED"


@dataclass(frozen=True, slots=True)
class MountSpec:
    host_path: str
    container_path: str
    mode: MountMode
    is_host_project: bool = False


@dataclass(frozen=True, slots=True)
class ResourceLimits:
    """Hard limits (``01E §2.11``). Every field must be positive or the spec fails closed."""

    cpu_millis: int
    memory_mb: int
    disk_mb: int
    pids: int
    wall_clock_s: int


@dataclass(frozen=True, slots=True)
class SandboxSpec:
    """A requested sandbox. Prohibited-privilege flags default off; setting one is a denial."""

    task_id: str
    workstream_id: str
    image: str
    image_version: str
    resources: ResourceLimits
    uid: int = 1000
    gid: int = 1000
    run_as_root: bool = False
    privileged: bool = False
    host_docker_socket: bool = False
    host_pid_namespace: bool = False
    host_ipc_namespace: bool = False
    host_network: bool = False
    windows_native: bool = False
    mounts: tuple[MountSpec, ...] = field(default_factory=tuple)
    network: NetworkPolicy = NetworkPolicy.DENY


@dataclass(frozen=True, slots=True)
class SandboxIdentity:
    """Recorded execution identity (``01E §3.2``)."""

    uid: int
    gid: int
    capabilities: tuple[str, ...]
    mounts: tuple[MountSpec, ...]
    network: NetworkPolicy
    resources: ResourceLimits


@dataclass(frozen=True, slots=True)
class SandboxHandle:
    sandbox_id: str
    task_id: str
    workstream_id: str
    image: str
    image_version: str
    status: SandboxStatus
    identity: SandboxIdentity | None = None
    reason: str = ""


@dataclass(frozen=True, slots=True)
class PolicyViolation:
    code: str
    detail: str


@dataclass(frozen=True, slots=True)
class BoundaryFailureReport:
    """Result of a sandbox boundary/isolation failure (``04 §7``): destroy + security clearance."""

    sandbox_id: str
    destroyed: bool
    security_clearance_required: bool
    reason: str
