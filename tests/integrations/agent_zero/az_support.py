"""Shared builders for Agent Zero integration tests (deterministic fakes only)."""

from __future__ import annotations

from factory.integrations.agent_zero.fake_transport import sample_work_order
from factory.integrations.agent_zero.models import ResourceEnvelope, WorkOrder
from factory.integrations.agent_zero.policy import AgentZeroCapabilityRequest, AgentZeroModelResult
from factory.network.fake_backend import FakeNetworkBackend
from factory.network.models import NetworkApproval
from factory.secret.fake_backend import FakeSecretBackend

APPROVED_HOST = "agent-zero-worker.internal.example"


class StaticModelRouter:
    """A ModelRouterPort double that returns a fixed result and records every request it saw."""

    def __init__(self, result: AgentZeroModelResult) -> None:
        self._result = result
        self.requests: list[AgentZeroCapabilityRequest] = []

    def request(self, capability: AgentZeroCapabilityRequest) -> AgentZeroModelResult:
        self.requests.append(capability)
        return self._result


def model_router(
    *, ok: bool = True, output: str = "ok", fingerprint: str = "fp-1", route: str = "local:qwen"
) -> StaticModelRouter:
    return StaticModelRouter(AgentZeroModelResult(ok, output, fingerprint, route))


def network_backend() -> FakeNetworkBackend:
    return FakeNetworkBackend()


def approval(
    host: str = APPROVED_HOST, *, task_id: str = "T1", max_bytes: int = 1_000_000
) -> NetworkApproval:
    return NetworkApproval(
        approval_id="AZ-A1",
        task_id=task_id,
        destinations=frozenset({host}),
        protocols=frozenset({"https"}),
        methods=frozenset({"GET", "POST"}),
        expires_at=10_000,
        max_total_bytes=max_bytes,
        follow_redirects=True,
    )


def secret_backend(value: str = "unused-fake-secret") -> FakeSecretBackend:
    return FakeSecretBackend({"R1": value})


def work_order(**over: object) -> WorkOrder:
    return sample_work_order(**over)


def resources(**over: object) -> ResourceEnvelope:
    base: dict[str, object] = dict(cpu_millis=1000, memory_mb=512, disk_mb=256, wall_clock_s=300)
    base.update(over)
    return ResourceEnvelope(**base)  # type: ignore[arg-type]
