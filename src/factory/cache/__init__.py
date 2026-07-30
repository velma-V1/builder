"""PH-5 (Task 5.4) — cache isolation (preinstallation).

Content-addressed, immutable, scoped cache: project vs sandbox scoping, contamination prevention,
credential-free enforcement, and trusted-management invalidation (``01E §3.5``).
"""

from __future__ import annotations

from factory.cache.errors import CacheError
from factory.cache.models import CacheEntry, CacheKey, CacheScope
from factory.cache.store import ContentAddressedCache, content_hash

__all__ = [
    "CacheEntry",
    "CacheError",
    "CacheKey",
    "CacheScope",
    "ContentAddressedCache",
    "content_hash",
]
