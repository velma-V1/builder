"""PH-5 — content-addressed scoped cache (immutability, scoping, contamination, invalidation)."""

from __future__ import annotations

import pytest

from factory.cache import (
    CacheError,
    CacheScope,
    ContentAddressedCache,
    content_hash,
)


def test_put_get_roundtrip() -> None:
    cache = ContentAddressedCache()
    key = cache.put(CacheScope.PROJECT, "P1", b"payload")
    assert cache.get(key) == b"payload"
    assert cache.contains(key)
    assert key.content_hash == content_hash(b"payload")


def test_put_is_idempotent() -> None:
    cache = ContentAddressedCache()
    k1 = cache.put(CacheScope.PROJECT, "P1", b"same")
    k2 = cache.put(CacheScope.PROJECT, "P1", b"same")
    assert k1 == k2
    assert len(cache.visible_to(CacheScope.PROJECT, "P1")) == 1


@pytest.mark.security
def test_credential_material_rejected() -> None:
    cache = ContentAddressedCache()
    with pytest.raises(CacheError) as exc:
        cache.put(CacheScope.SANDBOX, "sbx-1", b"token=s3cr3t", forbidden_values=["s3cr3t"])
    assert exc.value.code == "CACHE_CREDENTIAL"


def test_sandbox_scoping_is_isolated() -> None:
    cache = ContentAddressedCache()
    k1 = cache.put(CacheScope.SANDBOX, "sbx-1", b"shared-bytes")
    k2 = cache.put(CacheScope.SANDBOX, "sbx-2", b"shared-bytes")
    # Identical content, but each sandbox owns its own entry (contamination prevention).
    assert k1.content_hash == k2.content_hash
    assert k1 != k2
    assert cache.contains(k1) and cache.contains(k2)
    assert len(cache.visible_to(CacheScope.SANDBOX, "sbx-1")) == 1


def test_invalidate_one_scope_leaves_the_other() -> None:
    cache = ContentAddressedCache()
    k1 = cache.put(CacheScope.SANDBOX, "sbx-1", b"data")
    k2 = cache.put(CacheScope.SANDBOX, "sbx-2", b"data")
    assert cache.invalidate(k1) is True
    assert cache.invalidate(k1) is False  # already gone
    assert not cache.contains(k1)
    assert cache.contains(k2)  # other sandbox unaffected


def test_invalidate_scope_bulk() -> None:
    cache = ContentAddressedCache()
    cache.put(CacheScope.PROJECT, "P1", b"a")
    cache.put(CacheScope.PROJECT, "P1", b"b")
    assert cache.invalidate_scope(CacheScope.PROJECT, "P1") == 2


def test_get_miss_raises() -> None:
    cache = ContentAddressedCache()
    key = cache.put(CacheScope.PROJECT, "P1", b"x")
    cache.invalidate(key)
    with pytest.raises(CacheError) as exc:
        cache.get(key)
    assert exc.value.code == "CACHE_MISS"


def test_put_with_non_matching_forbidden_values_succeeds() -> None:
    cache = ContentAddressedCache()
    key = cache.put(CacheScope.PROJECT, "P1", b"clean bytes", forbidden_values=["absent", ""])
    assert cache.get(key) == b"clean bytes"


def test_cache_error_repr() -> None:
    err = CacheError("X", "y")
    assert "CacheError(code='X'" in repr(err)
    assert str(err) == "X: y"
