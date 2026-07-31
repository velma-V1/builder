"""Stage-3 unit — live adapter contract / fake parity."""

from __future__ import annotations

from factory.livegate.adapter_contracts import (
    LIVE_ADAPTER_OBLIGATIONS,
    structural_parity_violations,
)
from factory.models.ollama_adapter.fake_ollama import FakeOllamaAdapter
from factory.workers.aider_adapter.fake_aider import FakeAiderWorker


def test_fake_ollama_is_a_structural_drop_in() -> None:
    assert structural_parity_violations(FakeOllamaAdapter()) == ()


def test_fake_aider_is_a_structural_drop_in() -> None:
    assert structural_parity_violations(FakeAiderWorker()) == ()


def test_non_adapter_is_rejected() -> None:
    violations = structural_parity_violations(object())
    assert violations  # non-empty
    assert any("ProviderAdapter" in v for v in violations)


def test_obligations_are_declared_and_unique() -> None:
    ids = [o.obligation_id for o in LIVE_ADAPTER_OBLIGATIONS]
    assert len(ids) == len(set(ids))
    assert all(o.fake_parity for o in LIVE_ADAPTER_OBLIGATIONS)
