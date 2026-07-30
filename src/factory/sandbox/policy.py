"""Sandbox isolation policy (``01E §3.1/§3.2``, ``01R`` Decision C).

Pure, deterministic evaluation of a :class:`SandboxSpec` against the prohibited-privilege surface.
Returns the full list of violations (empty ⇒ admissible). Enforced by default and not grantable
through an ordinary task approval.
"""

from __future__ import annotations

from factory.sandbox.models import MountMode, PolicyViolation, SandboxSpec

# Prohibited-privilege flags: (spec attribute, violation code, detail). Each set flag is a denial.
_PROHIBITED: tuple[tuple[str, str, str], ...] = (
    ("windows_native", "WINDOWS_NATIVE_DENIED", "Decision C: WSL2+Docker Linux only"),
    ("privileged", "PRIVILEGED_DENIED", "privileged containers are prohibited"),
    ("host_docker_socket", "HOST_SOCKET_DENIED", "host container-runtime socket denied"),
    ("host_pid_namespace", "HOST_PID_NS_DENIED", "host PID namespace denied"),
    ("host_ipc_namespace", "HOST_IPC_NS_DENIED", "host IPC namespace denied"),
    ("host_network", "HOST_NET_DENIED", "host network namespace control denied"),
)


def evaluate_spec(spec: SandboxSpec) -> tuple[PolicyViolation, ...]:
    violations: list[PolicyViolation] = [
        PolicyViolation(code, detail)
        for attr, code, detail in _PROHIBITED
        if getattr(spec, attr)
    ]
    if spec.run_as_root or spec.uid == 0:
        violations.append(
            PolicyViolation("ROOT_DENIED", "non-root execution is the default (01E §3.2)")
        )
    for mount in spec.mounts:
        if mount.is_host_project and mount.mode is MountMode.RW:
            violations.append(
                PolicyViolation(
                    "HOST_PROJECT_WRITE_DENIED",
                    f"writable host-project mount denied: {mount.container_path}",
                )
            )
    limits = spec.resources
    smallest = min(
        limits.cpu_millis, limits.memory_mb, limits.disk_mb, limits.pids, limits.wall_clock_s
    )
    if smallest <= 0:
        violations.append(
            PolicyViolation("RESOURCE_LIMITS_REQUIRED", "hard resource limits must all be positive")
        )
    return tuple(violations)
