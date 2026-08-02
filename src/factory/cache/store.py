"""Content-addressed, scoped, immutable cache (Task 5.4, ``01E §3.5``).

Guarantees, all deterministic and offline:

* **content-addressed** — an entry's identity is the SHA-256 of its bytes; a re-``put`` of identical
  bytes is idempotent and returns the same hash;
* **immutable to consumers** — a hash cannot be rewritten with different bytes in place;
* **scoped** — ``SANDBOX`` entries are private to one sandbox; a second sandbox putting the same
  bytes gets its own entry and cannot replace another's (contamination prevention);
* **credential-free** — a ``put`` whose bytes contain a forbidden secret value is rejected;
* **invalidation** — only through the trusted management API (``invalidate``), never by a consumer
  mutating an entry.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable

from factory.cache.errors import CacheError
from factory.cache.models import CacheEntry, CacheKey, CacheScope


def content_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


class ContentAddressedCache:
    """A scoped immutable cache keyed by (scope, scope_id, content-hash)."""

    __slots__ = ("_blobs", "_entries")

    def __init__(self) -> None:
        self._entries: dict[tuple[CacheScope, str, str], CacheEntry] = {}
        self._blobs: dict[str, bytes] = {}

    def put(
        self,
        scope: CacheScope,
        scope_id: str,
        content: bytes,
        forbidden_values: Iterable[str] = (),
    ) -> CacheKey:
        digest = content_hash(content)
        text = content.decode("utf-8", errors="ignore")
        for secret in forbidden_values:
            if secret and secret in text:
                raise CacheError("CACHE_CREDENTIAL", "credential material may not enter the cache")
        map_key = (scope, scope_id, digest)
        existing_blob = self._blobs.get(digest)
        # A differing blob under an identical hash is a SHA-256 collision (practically impossible).
        if existing_blob is not None and existing_blob != content:  # pragma: no cover
            raise CacheError("CACHE_HASH_COLLISION", "content hash collision detected")
        self._blobs[digest] = content
        key = CacheKey(scope, scope_id, digest)
        self._entries.setdefault(map_key, CacheEntry(key, len(content), digest))
        return key

    def get(self, key: CacheKey) -> bytes:
        if (key.scope, key.scope_id, key.content_hash) not in self._entries:
            raise CacheError("CACHE_MISS", f"no entry for {key.content_hash} in {key.scope_id}")
        return self._blobs[key.content_hash]

    def contains(self, key: CacheKey) -> bool:
        return (key.scope, key.scope_id, key.content_hash) in self._entries

    def visible_to(self, scope: CacheScope, scope_id: str) -> tuple[CacheEntry, ...]:
        return tuple(
            entry for (s, sid, _), entry in self._entries.items() if s is scope and sid == scope_id
        )

    def invalidate(self, key: CacheKey) -> bool:
        """Trusted-management invalidation of a single scoped entry (not a consumer mutation)."""
        removed = self._entries.pop((key.scope, key.scope_id, key.content_hash), None)
        return removed is not None

    def invalidate_scope(self, scope: CacheScope, scope_id: str) -> int:
        keys = [k for k in self._entries if k[0] is scope and k[1] == scope_id]
        for k in keys:
            self._entries.pop(k)
        return len(keys)
