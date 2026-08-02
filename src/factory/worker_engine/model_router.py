"""``ModelRouterPort`` implementations for Phase 3B: Agent Zero's only way to obtain AI.

``factory.integrations.agent_zero.policy.ModelRouterPort`` is the sole capability-request seam
Agent Zero (here, Builder's own in-process worker loop -- see ``BuilderWorkerTransport`` in
``builder_worker_transport.py``, NOT the real Agent Zero project) may use for AI; it never selects
a provider or calls one directly. This module provides:

- ``LiveOllamaModelRouter``: routes every request to a real local Ollama + Devstral call.
- ``FakeModelRouter``: a deterministic, scripted double for tests -- never calls out to anything.

Neither implementation wires into ``factory.routing``'s full multi-provider
``ModelRouter``/``ApprovedRoster``/``ResourceScheduler`` system (designed for fallback across many
hosted/local providers); Phase 3B integrates exactly one local model directly, a deliberate scope
decision documented here and in the Phase 3B final report. That broader system remains available,
unchanged, for a future phase that wants multi-provider fallback.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from factory.integrations.agent_zero.policy import AgentZeroCapabilityRequest, AgentZeroModelResult
from factory.models.ollama_adapter.live_ollama import (
    OllamaClient,
    OllamaError,
)


def _fingerprint(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class LiveOllamaModelRouter:
    """Routes every capability request to one real, configured local Ollama model."""

    client: OllamaClient
    model: str

    def request(self, capability: AgentZeroCapabilityRequest) -> AgentZeroModelResult:
        try:
            result = self.client.generate(model=self.model, prompt=capability.prompt)
        except OllamaError as exc:
            return AgentZeroModelResult(
                ok=False,
                output="",
                model_fingerprint=_fingerprint("ollama", self.model),
                provider_route="ollama:local",
                reason=str(exc),
            )
        if not result.done:
            return AgentZeroModelResult(
                ok=False,
                output=result.response_text,
                model_fingerprint=_fingerprint("ollama", self.model),
                provider_route="ollama:local",
                reason="generation did not complete",
            )
        return AgentZeroModelResult(
            ok=True,
            output=result.response_text,
            model_fingerprint=_fingerprint("ollama", self.model),
            provider_route="ollama:local",
        )


@dataclass(frozen=True, slots=True)
class FakeModelRouter:
    """Deterministic, scripted ``ModelRouterPort`` double for tests -- no live call, ever.

    ``script`` maps a capability's ``prompt`` (matched via ``prompt_matcher``, default exact
    equality) to a canned :class:`AgentZeroModelResult`. ``default`` is used for any prompt the
    script doesn't recognize, and a ``calls`` log records every request received for assertions.
    """

    script: dict[str, AgentZeroModelResult] = field(default_factory=dict)
    default: AgentZeroModelResult = field(
        default_factory=lambda: AgentZeroModelResult(
            ok=False, output="", model_fingerprint="fake", provider_route="fake",
            reason="no scripted response for this prompt",
        )
    )
    calls: list[AgentZeroCapabilityRequest] = field(default_factory=list)
    prompt_matcher: Callable[[str, Sequence[str]], str | None] = field(
        default=lambda prompt, keys: prompt if prompt in keys else None
    )

    def request(self, capability: AgentZeroCapabilityRequest) -> AgentZeroModelResult:
        self.calls.append(capability)
        matched = self.prompt_matcher(capability.prompt, tuple(self.script.keys()))
        if matched is not None and matched in self.script:
            return self.script[matched]
        return self.default
