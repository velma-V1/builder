"""Immutable provenance chain for normalized WorldMonitor records."""

from __future__ import annotations

from factory.integrations.worldmonitor.models import ProvenanceStep, WorldMonitorSourceRef


def build_provenance(
    source: WorldMonitorSourceRef,
    *,
    fetched_at: int,
    provider_route: str = "",
    model_fingerprint: str = "",
) -> tuple[ProvenanceStep, ...]:
    """Build the ordered, immutable provenance chain from source → fetch → normalize → (AI)."""
    steps = [
        ProvenanceStep("source", f"{source.source_name} :: {source.source_url}"),
        ProvenanceStep("fetch", f"fetched_at={fetched_at}"),
        ProvenanceStep("normalize", "normalized_summary is an external claim, not a verified fact"),
    ]
    if provider_route or model_fingerprint:
        steps.append(ProvenanceStep("ai", f"route={provider_route} fp={model_fingerprint}"))
    return tuple(steps)
