"""PH-4 (Task 4.1) — Ollama runtime adapter.

Ships the deterministic preinstallation fake (:class:`FakeOllamaAdapter`) implementing the
routing-owned ``ProviderAdapter`` surface: health/version, exact-model discovery, bounded calls, and
every failure mode. The live adapter against a real Ollama daemon is LIVE_RUNTIME_PENDING.
"""

from __future__ import annotations

from factory.models.ollama_adapter.fake_ollama import FakeOllamaAdapter

__all__ = ["FakeOllamaAdapter"]
