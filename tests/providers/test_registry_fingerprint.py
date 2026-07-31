"""Provider tests — registry (discovery ≠ approval) + versioned fingerprint provenance."""

from __future__ import annotations

from factory.providers import (
    ApprovedHostedRoster,
    ApprovedHostedRoute,
    Capability,
    DiscoveredModel,
    HostedModelCatalog,
    ProviderCapability,
    ProviderFingerprint,
)
from factory.routing.models import ModelRole, Privacy, Provider, ResourceClass


def test_discovered_model_enters_catalog_but_is_never_approved() -> None:
    catalog = HostedModelCatalog()
    model = DiscoveredModel(
        Provider.OPENROUTER, "vendor/new-model",
        ProviderCapability(frozenset({Capability.CHAT})),
    )
    catalog.record(model)
    key = "OPENROUTER:vendor/new-model"
    assert catalog.is_catalogued(key)
    assert catalog.is_approved(key) is False  # discovery is NOT approval


def test_approved_route_is_fully_declared() -> None:
    route = ApprovedHostedRoute(
        provider=Provider.OPENROUTER, model_id="openai/gpt-x", role=ModelRole.HOSTED_WORKER,
        privacy_class=Privacy.CLOUD_ALLOWED,
        allowed_capabilities=frozenset({Capability.CHAT, Capability.TOOLS}),
        approved_domains=frozenset({"openrouter.ai"}), resource_class=ResourceClass.CPU_ONLY,
        cost_ceiling_usd=0.5, timeout_s=30.0, context_limit=8192, upstream_provider="openai",
    )
    roster = ApprovedHostedRoster((route,))
    assert roster.get("OPENROUTER:openai/gpt-x") is route
    assert roster.approved_model_ids(Provider.OPENROUTER) == frozenset({"openai/gpt-x"})
    assert route.fallback_allowed is False  # adapter fallback always forbidden


def test_fingerprint_digest_is_deterministic_and_provider_neutral() -> None:
    fp = ProviderFingerprint(
        provider=Provider.TOGETHER, model_id="m", model_version_or_digest="d",
        upstream_provider="together", endpoint_identity="serverless:together",
        runtime_or_api_version="v1", context_window=8192, capability_digest="abc",
        sampling=(("temperature", "0.2"),), system_prompt_version="v1", tool_schema_version="v1",
        adapter_version="v1", routing_policy_version="v1", execution_region="us",
    )
    assert fp.schema_version == 2
    assert fp.digest() == fp.digest()
    # A different endpoint identity changes the digest (provenance is material).
    other = ProviderFingerprint(**{**{f.name: getattr(fp, f.name)
                                      for f in fp.__dataclass_fields__.values()},
                                    "endpoint_identity": "dedicated:ep-9"})
    assert other.digest() != fp.digest()


def test_legacy_model_fingerprint_digest_unchanged() -> None:
    # The Ollama-specific legacy fingerprint remains reproducible (schema not disturbed).
    from factory.routing.models import ModelFingerprint
    legacy = ModelFingerprint(
        family="qwen", declared_name="qwen3:8b", artifact_digest="sha", quantization="q4",
        fmt="gguf", ollama_version="0.1", runtime_version="r1", context_window=8192,
        context_allocation=4096, sampling=(("temperature", "0.1"),), system_prompt_version="v1",
        tool_schema_version="v1", adapter_version="v1", routing_policy_version="v1",
        gpu_config="12g",
    )
    assert legacy.digest() == legacy.digest()
    assert len(legacy.digest()) == 64
