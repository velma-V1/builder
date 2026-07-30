"""PH-4 unit — model-neutral value objects (fingerprint digest, usage, health, descriptors)."""

from __future__ import annotations

from factory.routing import (
    HealthRecord,
    HealthState,
    ModelDescriptor,
    ModelFingerprint,
    ModelRole,
    Provider,
    ResourceClass,
    UsageCounters,
)


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


def test_descriptor_route_key() -> None:
    d = ModelDescriptor(
        Provider.OLLAMA, "qwen3:8b", ModelRole.DISPATCHER, ResourceClass.GPU_LIGHT, True
    )
    assert d.route_key == "OLLAMA:qwen3:8b"


def test_fingerprint_digest_is_deterministic_and_order_independent() -> None:
    a = _fp(sampling=(("temperature", "0.0"), ("top_p", "1.0")))
    b = _fp(sampling=(("top_p", "1.0"), ("temperature", "0.0")))
    assert a.digest() == b.digest()  # sorted internally
    assert len(a.digest()) == 64


def test_fingerprint_digest_changes_with_material_field() -> None:
    assert _fp(quantization="Q4_K_M").digest() != _fp(quantization="Q8_0").digest()
    assert _fp(context_window=8192).digest() != _fp(context_window=16384).digest()


def test_usage_counters_plus_is_pure() -> None:
    base = UsageCounters()
    added = base.plus(requests=1, tokens=10, wall_time=2)
    assert (added.requests, added.tokens, added.wall_time) == (1, 10, 2)
    assert base == UsageCounters()  # unchanged


def test_health_record_validity_window() -> None:
    healthy = HealthRecord(
        "OLLAMA:qwen3:8b", HealthState.HEALTHY, checked_at=0, expires_at=10, reason="ok"
    )
    assert healthy.is_valid_at(5) is True
    assert healthy.is_valid_at(10) is False  # boundary is exclusive
    unhealthy = HealthRecord("OLLAMA:qwen3:8b", HealthState.UNHEALTHY, 0, 10, "bad")
    assert unhealthy.is_valid_at(5) is False
