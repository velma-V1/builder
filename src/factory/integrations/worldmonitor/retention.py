"""Retention policy — minimal by default; no indefinite raw-feed or secret retention."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RetentionPolicy:
    raw_cache_ttl_s: int = 3600  # raw upstream payloads: short-lived cache
    normalized_ttl_s: int = 86_400  # normalized records: bounded
    alert_retention_s: int = 604_800  # alerts: one week
    provenance_retention_s: int = 2_592_000  # provenance: 30 days (audit)
    retain_model_io: bool = False  # prompts/outputs are NOT retained unless policy allows
    store_secrets_in_cache: bool = False  # never

    def is_expired(self, age_s: int, *, kind: str, user_pinned: bool = False) -> bool:
        if user_pinned:
            return False  # user-pinned records are exempt from TTL expiry
        ttl = {
            "raw": self.raw_cache_ttl_s,
            "normalized": self.normalized_ttl_s,
            "alert": self.alert_retention_s,
            "provenance": self.provenance_retention_s,
        }.get(kind, 0)
        return ttl > 0 and age_s > ttl


DEFAULT_RETENTION = RetentionPolicy()
