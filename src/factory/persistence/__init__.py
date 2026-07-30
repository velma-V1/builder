"""Persistence-hardening utilities for durable SQLite stores (Stage-1 static hardening).

Enforces a minimum SQLite engine (``>=3.51.3`` or an approved backport), opens hardened connections
(busy timeout + WAL + foreign keys), and provides bounded, classified ``SQLITE_BUSY`` retry. Used by
the durable execution/quota stores prepared for the live phase; not wired into any preinstallation
code path yet.
"""

from __future__ import annotations

from factory.persistence.errors import PersistenceError
from factory.persistence.sqlite_guard import (
    MIN_SQLITE_VERSION,
    assert_sqlite_supported,
    classify_operational_error,
    connect,
    run_with_busy_retry,
    running_sqlite_version,
)

__all__ = [
    "MIN_SQLITE_VERSION",
    "PersistenceError",
    "assert_sqlite_supported",
    "classify_operational_error",
    "connect",
    "run_with_busy_retry",
    "running_sqlite_version",
]
