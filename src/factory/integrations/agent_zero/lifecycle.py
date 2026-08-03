"""Dry-run lifecycle plan for Agent Zero (no mutation implemented) + update/rollback preparation.

Reuses the dry-run-by-default installer framework (:mod:`factory.preinstall.installer`): every
mutating phase is planned with a declared rollback but performs **no** action now. Update/rollback
*preparation* is a pure decision function (:func:`plan_update`) that Builder — never Agent Zero —
would invoke; Agent Zero holds no self-update authority (``SELF_UPDATE_DENIED``).
"""

from __future__ import annotations

from dataclasses import dataclass

from factory.integrations.agent_zero.compatibility import check_compatibility
from factory.integrations.agent_zero.errors import AgentZeroError, AgentZeroErrorCode
from factory.integrations.agent_zero.models import ModuleHealthState
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
    """Declared isolation posture for a future Agent Zero worker service (not applied)."""

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
        InstallStep("inspect", "inspect current Agent Zero state (read-only)", mutating=False),
        InstallStep("prepare", "prepare config + pinned manifest (read-only)", mutating=False),
        InstallStep(
            "install_later",
            "install the pinned Agent Zero worker image",
            mutating=True,
            rollback="remove the installed image + config",
        ),
        InstallStep(
            "start_later",
            "start the isolated Agent Zero worker service",
            mutating=True,
            rollback="stop the service and remove its containers/networks",
        ),
        InstallStep("health", "check worker health (read-only)", mutating=False),
        InstallStep(
            "stop_later",
            "stop the worker service",
            mutating=True,
            rollback="restart the service from the last good state",
        ),
        InstallStep(
            "update_later",
            "update to a newer pinned revision",
            mutating=True,
            rollback="roll back to the last-known-good pinned revision",
        ),
        InstallStep(
            "rollback_later",
            "roll back to the last-known-good revision",
            mutating=True,
            rollback="re-apply the prior revision snapshot",
        ),
        InstallStep(
            "remove_later",
            "remove the worker service + volumes",
            mutating=True,
            rollback="reinstall from the pinned manifest",
        ),
    )
    return Installer("agent_zero", steps)


@dataclass(frozen=True, slots=True)
class UpdateDecision:
    applied: bool
    rolled_back: bool
    active_version: str
    reason: str


def plan_update(
    *,
    current_version: str,
    candidate_version: str,
    builder_contract_version: str,
    post_update_health: ModuleHealthState,
) -> UpdateDecision:
    """Decide whether an update would be applied or rolled back to last-known-good.

    Pure and dry-run: this function performs no host action. It is Builder-side preparation logic —
    Agent Zero itself is never given the authority to decide or perform its own update
    (``SELF_UPDATE_DENIED`` if it ever attempts to).
    """
    compat = check_compatibility(
        builder_contract_version=builder_contract_version, worker_reported_version=candidate_version
    )
    if not compat.compatible:
        return UpdateDecision(
            applied=False,
            rolled_back=False,
            active_version=current_version,
            reason=f"update refused: {compat.reason}",
        )
    if post_update_health is ModuleHealthState.UNAVAILABLE:
        return UpdateDecision(
            applied=False,
            rolled_back=True,
            active_version=current_version,
            reason="candidate failed its post-update health check; rolled back to last-known-good",
        )
    return UpdateDecision(
        applied=True,
        rolled_back=False,
        active_version=candidate_version,
        reason="update plan accepted (dry-run preparation only; no host mutation performed)",
    )


def deny_self_update(actor: str) -> None:
    """Raise ``SELF_UPDATE_DENIED`` if anything other than Builder attempts to trigger an update."""
    if actor != "builder":
        raise AgentZeroError(
            AgentZeroErrorCode.SELF_UPDATE_DENIED,
            f"actor {actor!r} may not trigger an Agent Zero update; only Builder may",
        )
