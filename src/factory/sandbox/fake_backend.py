"""Deterministic fake WSL2+Docker sandbox backend (preinstallation stand-in for Task 5.2).

Fully offline. It enforces the real isolation policy (non-root default, no writable host-project
mount, no privileged/host-namespace/host-socket, no Windows-native, hard resource limits) and models
runtime-unavailable and boundary-failure handling — without touching a real container runtime, which
is LIVE_SANDBOX_PENDING (Docker/WSL2 execution is NOT_AUTHORIZED at preinstallation).
"""

from __future__ import annotations

from factory.sandbox.errors import SandboxError
from factory.sandbox.models import (
    BoundaryFailureReport,
    SandboxHandle,
    SandboxIdentity,
    SandboxSpec,
    SandboxStatus,
)
from factory.sandbox.policy import evaluate_spec


class FakeWslDockerBackend:
    """Configurable deterministic isolation backend for tests and the preinstallation core."""

    __slots__ = ("_available", "_seq", "_status")

    def __init__(self, available: bool = True) -> None:
        self._available = available
        self._status: dict[str, SandboxStatus] = {}
        self._seq = 0

    def set_available(self, available: bool) -> None:
        self._available = available

    def provision(self, spec: SandboxSpec) -> SandboxHandle:
        if not self._available:
            return SandboxHandle(
                sandbox_id="",
                task_id=spec.task_id,
                workstream_id=spec.workstream_id,
                image=spec.image,
                image_version=spec.image_version,
                status=SandboxStatus.RUNTIME_UNAVAILABLE,
                reason="sandbox backend unavailable",
            )
        violations = evaluate_spec(spec)
        if violations:
            codes = sorted(v.code for v in violations)
            raise SandboxError(
                "SANDBOX_POLICY_DENIED", f"isolation policy denied spec: {codes}", security=True
            )
        self._seq += 1
        sandbox_id = f"sbx-{self._seq}"
        identity = SandboxIdentity(
            uid=spec.uid,
            gid=spec.gid,
            capabilities=(),  # no added capabilities
            mounts=spec.mounts,
            network=spec.network,
            resources=spec.resources,
            read_only_rootfs=spec.read_only_rootfs,
            cap_drop_all=spec.cap_drop_all,
            no_new_privileges=spec.no_new_privileges,
            network_name=spec.network_name,
            dual_homed=spec.dual_homed,
        )
        self._status[sandbox_id] = SandboxStatus.PROVISIONED
        return SandboxHandle(
            sandbox_id=sandbox_id,
            task_id=spec.task_id,
            workstream_id=spec.workstream_id,
            image=spec.image,
            image_version=spec.image_version,
            status=SandboxStatus.PROVISIONED,
            identity=identity,
            reason="provisioned",
        )

    def destroy(self, sandbox_id: str) -> bool:
        if self._status.get(sandbox_id) in (None, SandboxStatus.DESTROYED):
            return False
        self._status[sandbox_id] = SandboxStatus.DESTROYED
        return True

    def status(self, sandbox_id: str) -> SandboxStatus:
        return self._status.get(sandbox_id, SandboxStatus.DESTROYED)

    def reconcile(self, live_sandbox_ids: frozenset[str]) -> tuple[str, ...]:
        """Restart reconciliation: destroy any provisioned sandbox absent from the live set.

        After a restart, sandboxes the durable record does not vouch for are orphans and are
        disposed (they can never be silently resumed). Returns the destroyed orphan ids."""
        orphans = tuple(
            sorted(
                sid
                for sid, status in self._status.items()
                if status is SandboxStatus.PROVISIONED and sid not in live_sandbox_ids
            )
        )
        for sid in orphans:
            self._status[sid] = SandboxStatus.DESTROYED
        return orphans

    def boundary_failure(self, sandbox_id: str, reason: str) -> BoundaryFailureReport:
        """On an isolation boundary failure, destroy the sandbox and require security clearance."""
        destroyed = self.destroy(sandbox_id)
        self._status[sandbox_id] = SandboxStatus.FAILED
        return BoundaryFailureReport(
            sandbox_id=sandbox_id,
            destroyed=destroyed,
            security_clearance_required=True,
            reason=reason,
        )
