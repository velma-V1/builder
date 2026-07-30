"""Value objects for the PH-5 cache subsystem (``01E §3.5``).

A shared cache is immutable / content-addressed to consumers, credential-free, and scoped so one
sandbox cannot replace an entry beneath another.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CacheScope(StrEnum):
    """Isolation scope. PROJECT entries are shared read-only; SANDBOX entries are private."""

    PROJECT = "PROJECT"
    SANDBOX = "SANDBOX"


@dataclass(frozen=True, slots=True)
class CacheKey:
    scope: CacheScope
    scope_id: str
    content_hash: str


@dataclass(frozen=True, slots=True)
class CacheEntry:
    """An immutable, content-addressed cache entry."""

    key: CacheKey
    size: int
    content_hash: str
