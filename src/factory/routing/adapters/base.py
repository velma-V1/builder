"""Provider-adapter interface + call vocabulary (Tasks 4.1/4.2).

Every runtime (Ollama) and coding worker (Aider) is reached through a :class:`ProviderAdapter`. The
interface makes runtime outages **explicit results**, never exceptions or silent fallbacks: a probe
returns a :class:`CapabilityReport` with a :class:`RuntimeStatus`, and a call returns a
:class:`CallResult` whose ``status`` may be ``RUNTIME_UNAVAILABLE``. Adapters never certify work and
never widen their own authority; they report capability and produce bounded, attributable output.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from factory.routing.models import (
    CapabilityReport,
    ExecutionStatus,
    ModelFingerprint,
)


@dataclass(frozen=True, slots=True)
class CallRequest:
    task_id: str
    stage_id: str
    route_key: str
    prompt: str
    max_tokens: int
    timeout: int


@dataclass(frozen=True, slots=True)
class CallResult:
    """Outcome of a single adapter call. ``status`` distinguishes an outage from a failure."""

    status: ExecutionStatus
    output: str
    tokens: int
    fingerprint: ModelFingerprint | None
    reason: str
    error_code: str | None = None
    tool_calls: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return self.status is ExecutionStatus.SUCCEEDED


@runtime_checkable
class ProviderAdapter(Protocol):
    """Uniform surface over a model runtime or coding worker.

    * ``provider_name`` — the provider identity string.
    * ``probe()`` — availability + exact-model + version + capability probe (``03 §8``).
    * ``supports(model_id)`` — True only if the *exact* model id can be served right now.
    * ``call(request)`` — run one bounded call; returns ``RUNTIME_UNAVAILABLE`` rather than raising
      on outage (``01J §1``).
    * ``cancel(task_id)`` — cancel an in-flight call; True if something was cancelled.
    """

    @property
    def provider_name(self) -> str: ...
    def probe(self) -> CapabilityReport: ...
    def supports(self, model_id: str) -> bool: ...
    def call(self, request: CallRequest) -> CallResult: ...
    def cancel(self, task_id: str) -> bool: ...
