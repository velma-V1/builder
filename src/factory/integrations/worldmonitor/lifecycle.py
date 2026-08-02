"""Dry-run lifecycle plan for the WorldMonitor module (no mutation implemented).

Reuses the dry-run-by-default installer framework (:mod:`factory.preinstall.installer`): every
mutating phase is planned with a declared rollback but performs **no** action now. Default is
inspect/dry-run; a future mutation requires an explicit apply flag. Future runtime isolation posture
is declared for review.
"""

from __future__ import annotations

from dataclasses import dataclass

from factory.preinstall.installer import Installer, InstallStep

LIFECYCLE_PHASES = (
    "inspect",
    "prepare",
    "install_later",
    "start_later",
    "health",
    "stop_later",
    "update_later",
    "rollback_later",
    "remove_later",
)


@dataclass(frozen=True, slots=True)
class FutureIsolation:
    """Declared isolation posture for a future WorldMonitor service (not applied)."""

    separate_service: bool = True
    read_only_rootfs: bool = True
    non_root: bool = True
    no_host_networking: bool = True
    no_docker_socket: bool = True
    bounded_cpu_ram: bool = True
    approved_volumes_only: bool = True
    dedicated_network: bool = True
    egress_via_broker_only: bool = True


FUTURE_ISOLATION = FutureIsolation()


def build_lifecycle() -> Installer:
    """Build the dry-run lifecycle installer. Mutating phases carry a rollback but no action."""
    steps = (
        InstallStep("inspect", "inspect current WorldMonitor state (read-only)", mutating=False),
        InstallStep("prepare", "prepare config + pinned manifest (read-only)", mutating=False),
        InstallStep(
            "install_later",
            "install the pinned WorldMonitor image",
            mutating=True,
            rollback="remove the installed image + config",
        ),
        InstallStep(
            "start_later",
            "start the isolated WorldMonitor service",
            mutating=True,
            rollback="stop the service and remove its containers/networks",
        ),
        InstallStep("health", "check service health (read-only)", mutating=False),
        InstallStep(
            "stop_later",
            "stop the service",
            mutating=True,
            rollback="restart the service from the last good state",
        ),
        InstallStep(
            "update_later",
            "update to a newer pinned revision",
            mutating=True,
            rollback="roll back to the previous pinned revision",
        ),
        InstallStep(
            "rollback_later",
            "roll back to the previous revision",
            mutating=True,
            rollback="re-apply the prior revision snapshot",
        ),
        InstallStep(
            "remove_later",
            "remove the service + volumes",
            mutating=True,
            rollback="reinstall from the pinned manifest",
        ),
    )
    return Installer("worldmonitor", steps)
