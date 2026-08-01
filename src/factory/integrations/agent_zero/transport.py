"""Agent Zero transport seam (brokered) + deterministic fake.

The adapter never imports ``requests``/``httpx``/``subprocess``/``docker`` directly. It speaks to an
:class:`AgentZeroTransport`, and the only concrete transport wired in this repository is
:class:`~factory.integrations.agent_zero.fake_transport.FakeAgentZeroTransport` (deterministic,
offline, no process/container spawned). A real transport (built later) MUST route every call
through the :class:`~factory.network.broker.NetworkBroker` under a task-scoped approval; it is not
implemented here so no live call — and no install of Agent Zero — is possible from this package.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from factory.integrations.agent_zero.models import AgentZeroEvent, WorkOrder


class TransportTimeout(Exception):
    """The transport timed out — the adapter maps this to TIMED_OUT (never a silent success)."""


class TransportFailure(Exception):
    """A transport failure (unreachable, crashed, malformed handshake) — maps to UNAVAILABLE."""


@runtime_checkable
class AgentZeroTransport(Protocol):
    """Submit one already-authorized work order and poll its append-only event stream.

    A real implementation must send only through the NetworkBroker with a task-scoped approval, must
    never hold a Docker socket or provider/secret handle, and must treat every returned event as
    untrusted until :mod:`factory.integrations.agent_zero.event_validation` accepts it.
    """

    def submit(self, work_order: WorkOrder) -> str:
        """Submit a work order; return a worker-assigned run id (opaque, not a task/branch
        grant)."""
        ...

    def poll_events(self, run_id: str, *, after_sequence: int) -> tuple[AgentZeroEvent, ...]:
        """Return events with ``sequence > after_sequence`` known to the transport so far."""
        ...

    def cancel(self, run_id: str) -> bool:
        """Request cancellation; return True if a run was found and asked to cancel."""
        ...
