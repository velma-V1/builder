"""Network broker interface (Task 5.3, ``01E §3.3``)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from factory.network.models import NetworkApproval, NetworkDecision, NetworkRequest


@runtime_checkable
class NetworkBroker(Protocol):
    """Default-deny network mediation under a task-scoped approval contract.

    * ``evaluate(approval, request, now)`` — allow only when a matching approval covers the request.
    * ``evaluate_redirect(approval, target, now)`` — a redirect target must stay in the allowlist.
    * ``charge(approval, nbytes)`` — track transfer against the contract's total-byte limit.
    """

    def evaluate(
        self, approval: NetworkApproval | None, request: NetworkRequest, now: int
    ) -> NetworkDecision: ...
    def evaluate_redirect(
        self, approval: NetworkApproval, target: str, now: int
    ) -> NetworkDecision: ...
    def charge(self, approval: NetworkApproval, nbytes: int) -> NetworkDecision: ...
