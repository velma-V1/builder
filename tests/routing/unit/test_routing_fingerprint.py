"""PH-4 unit — fingerprint sufficiency (CTR-MODEL-FINGERPRINT, ``01J §3.1``)."""

from __future__ import annotations

import pytest

from factory.routing import ModelFingerprint, require_full_fingerprint
from factory.routing.errors import RoutingError


def _fp(**overrides: object) -> ModelFingerprint:
    base = dict(
        family="qwen3",
        declared_name="qwen3:8b",
        artifact_digest="sha256-abc",
        quantization="Q4_K_M",
        fmt="gguf",
        ollama_version="0.1",
        runtime_version="cpu",
        context_window=8192,
        context_allocation=4096,
        sampling=(("temperature", "0.0"),),
        system_prompt_version="sys",
        tool_schema_version="tools",
        adapter_version="ad",
        routing_policy_version="rp",
        gpu_config="none",
    )
    base.update(overrides)
    return ModelFingerprint(**base)  # type: ignore[arg-type]


def test_complete_fingerprint_passes() -> None:
    fp = _fp()
    assert require_full_fingerprint(fp) is fp


@pytest.mark.security
def test_bare_declared_name_is_insufficient() -> None:
    with pytest.raises(RoutingError) as exc:
        require_full_fingerprint(_fp(artifact_digest="  "))
    assert exc.value.code == "FINGERPRINT_INSUFFICIENT"
    assert "artifact_digest" in str(exc.value)


def test_zero_context_window_is_insufficient() -> None:
    with pytest.raises(RoutingError):
        require_full_fingerprint(_fp(context_window=0))


def test_empty_sampling_is_insufficient() -> None:
    with pytest.raises(RoutingError):
        require_full_fingerprint(_fp(sampling=()))
