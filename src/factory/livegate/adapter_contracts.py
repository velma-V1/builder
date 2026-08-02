"""Live adapter contract + fake-parity check.

A *live* Ollama / Aider adapter must be a drop-in for the deterministic fake: same structural
surface (:class:`factory.routing.adapters.base.ProviderAdapter`) **and** the same behavioural
obligations. This module states those obligations as data and provides a structural parity check
used by the compat tests, so that when a live adapter is written it can be validated against the
identical contract the fakes already satisfy. No live adapter is created or called here.
"""

from __future__ import annotations

from dataclasses import dataclass

from factory.routing.adapters.base import ProviderAdapter

#: Callables the structural contract requires (the ``ProviderAdapter`` Protocol surface).
REQUIRED_CALLABLES: tuple[str, ...] = ("probe", "supports", "call", "cancel")
REQUIRED_PROPERTIES: tuple[str, ...] = ("provider_name",)


@dataclass(frozen=True, slots=True)
class LiveAdapterObligation:
    """A behavioural obligation a live adapter must honour (beyond the structural surface)."""

    obligation_id: str
    statement: str
    fake_parity: str


LIVE_ADAPTER_OBLIGATIONS: tuple[LiveAdapterObligation, ...] = (
    LiveAdapterObligation(
        "OB-1",
        "An outage is returned as CallResult(status=RUNTIME_UNAVAILABLE), never raised.",
        "FakeOllamaAdapter.set_status(UNAVAILABLE) → call() returns RUNTIME_UNAVAILABLE",
    ),
    LiveAdapterObligation(
        "OB-2",
        "probe() reports exact served model id + version + capability; no optimistic claims.",
        "FakeOllamaAdapter.probe() → CapabilityReport with exact fingerprint",
    ),
    LiveAdapterObligation(
        "OB-3",
        "supports(model_id) is True only for the exact model currently servable.",
        "Fake adapters gate supports() on the exact backing model id",
    ),
    LiveAdapterObligation(
        "OB-4",
        "call() output is bounded and attributable (fingerprint carried on success).",
        "Fake CallResult carries a ModelFingerprint and bounded output",
    ),
    LiveAdapterObligation(
        "OB-5",
        "The adapter never certifies work and never widens its own authority.",
        "Fakes return worker output only; verification remains external",
    ),
    LiveAdapterObligation(
        "OB-6",
        "cancel(task_id) is idempotent and returns whether something was cancelled.",
        "Fake cancel() returns a bool without side effects on unknown ids",
    ),
)


def structural_parity_violations(candidate: object) -> tuple[str, ...]:
    """Return violations if ``candidate`` does not satisfy the live adapter structural contract.

    Empty tuple ⇒ the object is a structural drop-in for a live adapter. Used against the fakes so
    the same assertion will validate a future live adapter.
    """
    violations: list[str] = []
    if not isinstance(candidate, ProviderAdapter):
        violations.append("does not satisfy the ProviderAdapter protocol")
    for name in REQUIRED_CALLABLES:
        if not callable(getattr(candidate, name, None)):
            violations.append(f"missing callable: {name}()")
    for name in REQUIRED_PROPERTIES:
        if not hasattr(candidate, name):
            violations.append(f"missing property: {name}")
    return tuple(violations)
