"""Sandbox backend interface (Task 5.2).

A backend provisions/destroys isolated execution environments. Runtime outages are explicit results
(``SandboxStatus.RUNTIME_UNAVAILABLE``), never silent. The preinstallation core ships a
deterministic fake WSL2+Docker backend; the live backend against real WSL2/Docker is
LIVE_SANDBOX_PENDING.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from factory.sandbox.models import SandboxHandle, SandboxSpec, SandboxStatus


@runtime_checkable
class SandboxBackend(Protocol):
    """Provision / destroy / status over an isolation backend.

    * ``provision(spec)`` — apply isolation policy and create a sandbox, or return a
      ``RUNTIME_UNAVAILABLE`` handle if the backend is down; raises on a policy denial.
    * ``destroy(sandbox_id)`` — dispose a sandbox; idempotent (False if already gone).
    * ``status(sandbox_id)`` — current status.
    """

    def provision(self, spec: SandboxSpec) -> SandboxHandle: ...
    def destroy(self, sandbox_id: str) -> bool: ...
    def status(self, sandbox_id: str) -> SandboxStatus: ...
