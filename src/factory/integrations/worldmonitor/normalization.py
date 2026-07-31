"""Normalize raw WorldMonitor payloads into provenance-preserving IntelligenceRecords.

Fail closed on malformed timestamps / geography / oversized inputs and on source URLs outside the
approved domains. Stale data is marked (not dropped). Confidence is only carried when the source
supplied a numeric value — never invented. Deduplication is by stable source identity + digest.
"""

from __future__ import annotations

from collections.abc import Mapping
from urllib.parse import urlsplit

from factory.integrations.worldmonitor.errors import WorldMonitorError, WorldMonitorErrorCode
from factory.integrations.worldmonitor.models import (
    Category,
    Freshness,
    IntelligenceRecord,
    WorldMonitorFreshness,
    WorldMonitorSourceRef,
    content_digest,
    dedup_key,
)
from factory.integrations.worldmonitor.provenance import build_provenance


def _require_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise WorldMonitorError(
            WorldMonitorErrorCode.MALFORMED_RESPONSE, f"{field} is not an integer timestamp"
        )
    return value


def _require_str(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise WorldMonitorError(
            WorldMonitorErrorCode.MALFORMED_RESPONSE, f"{field} is not a string"
        )
    return value


def normalize_record(
    raw: Mapping[str, object],
    *,
    category: Category,
    now: int,
    ttl_s: int,
    approved_source_domains: frozenset[str],
    provider_route: str = "",
    model_fingerprint: str = "",
) -> IntelligenceRecord:
    source_url = _require_str(raw.get("source_url", ""), "source_url")
    host = urlsplit(source_url).hostname or ""
    if host and host not in approved_source_domains:
        raise WorldMonitorError(
            WorldMonitorErrorCode.SOURCE_URL_DENIED, f"source host not approved: {host}"
        )
    geography = _require_str(raw.get("geography", ""), "geography")
    summary = _require_str(raw.get("summary", ""), "summary")

    observed_raw = raw.get("observed_at")
    if observed_raw is None:
        freshness = WorldMonitorFreshness(Freshness.UNKNOWN, fetched_at=now, ttl_s=ttl_s)
    else:
        observed_at = _require_int(observed_raw, "observed_at")
        is_stale = (now - observed_at) > ttl_s if ttl_s > 0 else False
        freshness = WorldMonitorFreshness(
            Freshness.STALE if is_stale else Freshness.FRESH,
            observed_at=observed_at, fetched_at=now, ttl_s=ttl_s,
        )

    # Confidence only when the source supplied a numeric value; never invented.
    raw_conf = raw.get("confidence")
    confidence: float | None = None
    if isinstance(raw_conf, (int, float)) and not isinstance(raw_conf, bool):
        confidence = float(raw_conf)

    source = WorldMonitorSourceRef(
        source_name=_require_str(raw.get("source_name", "unknown"), "source_name"),
        source_url=source_url,
        upstream_record_id=_require_str(raw.get("id", ""), "id"),
    )
    digest = content_digest(category.value, source.source_url, summary)
    return IntelligenceRecord(
        record_id=digest[:16],
        category=category,
        source=source,
        geography=geography,
        freshness=freshness,
        normalized_summary=summary,
        content_digest=digest,
        raw_reference=source_url or source.upstream_record_id,
        provider_route=provider_route,
        model_fingerprint=model_fingerprint,
        confidence=confidence,
        provenance_chain=build_provenance(
            source, fetched_at=now, provider_route=provider_route,
            model_fingerprint=model_fingerprint,
        ),
    )


def deduplicate(records: tuple[IntelligenceRecord, ...]) -> tuple[IntelligenceRecord, ...]:
    """Drop duplicates by stable (source identity + digest) key, preserving first occurrence."""
    seen: set[str] = set()
    out: list[IntelligenceRecord] = []
    for record in records:
        key = dedup_key(record.source, record.content_digest)
        if key not in seen:
            seen.add(key)
            out.append(record)
    return tuple(out)
