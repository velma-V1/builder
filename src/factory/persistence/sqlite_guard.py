"""SQLite engine hardening (Stage-1 static hardening).

Durable stores (the live execution/quota stores prepared for the live phase) must run on a SQLite
engine that is known-good under concurrency and crash recovery. This module enforces that
requirement without weakening it:

* **Engine floor** — :func:`assert_sqlite_supported` requires ``>= 3.51.3`` *or* an explicitly
  approved fixed backport version. It does not silently accept an older engine.
* **Hardened connections** — :func:`connect` opens WAL, foreign keys, and an explicit
  ``busy_timeout`` so concurrent writers wait rather than fail immediately.
* **Classified contention** — :func:`run_with_busy_retry` retries a bounded number of times on a
  classified ``SQLITE_BUSY`` / "database is locked" error, then fails closed with a typed error.

The current environment's engine is validated by the caller at store-open time. It is deliberately
NOT invoked at import so this module can be unit-tested against parametrized versions on any host.
"""

from __future__ import annotations

import sqlite3
import time
from collections.abc import Callable
from pathlib import Path

from factory.persistence.errors import PersistenceError

#: Minimum SQLite engine version required for the durable stores.
MIN_SQLITE_VERSION: tuple[int, int, int] = (3, 51, 3)


def running_sqlite_version() -> tuple[int, int, int]:
    parts = sqlite3.sqlite_version.split(".")
    major, minor, patch = (int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)
    return (major, minor, patch)


def assert_sqlite_supported(
    *,
    version: tuple[int, int, int] | None = None,
    minimum: tuple[int, int, int] = MIN_SQLITE_VERSION,
    approved_backports: frozenset[tuple[int, int, int]] = frozenset(),
) -> tuple[int, int, int]:
    """Return the engine version if supported, else raise ``SQLITE_ENGINE_UNSUPPORTED``.

    Support means ``version >= minimum`` OR ``version in approved_backports`` (an explicitly
    approved, fixed backport). An older, non-approved engine is rejected — never silently accepted.
    """
    actual = version if version is not None else running_sqlite_version()
    if actual >= minimum or actual in approved_backports:
        return actual
    want = ".".join(str(p) for p in minimum)
    have = ".".join(str(p) for p in actual)
    raise PersistenceError(
        "SQLITE_ENGINE_UNSUPPORTED",
        f"SQLite {have} is below the required {want} and is not an approved backport",
    )


def connect(
    database_path: Path,
    *,
    busy_timeout_ms: int = 5000,
    wal: bool = True,
) -> sqlite3.Connection:
    """Open a hardened connection: explicit busy timeout, foreign keys, and (by default) WAL."""
    if busy_timeout_ms <= 0:
        raise PersistenceError("BUSY_TIMEOUT_INVALID", "busy_timeout_ms must be positive")
    connection = sqlite3.connect(str(database_path), isolation_level=None)
    connection.execute(f"PRAGMA busy_timeout = {busy_timeout_ms}")
    connection.execute("PRAGMA foreign_keys = ON")
    if wal:
        connection.execute("PRAGMA journal_mode = WAL")
    return connection


def classify_operational_error(exc: sqlite3.OperationalError) -> str:
    """Classify a SQLite operational error. ``SQLITE_BUSY`` for lock contention, else ``OTHER``."""
    message = str(exc).lower()
    if "database is locked" in message or "database table is locked" in message:
        return "SQLITE_BUSY"
    return "OTHER"


def run_with_busy_retry[T](
    operation: Callable[[], T],
    *,
    retries: int = 5,
    base_backoff_ms: int = 10,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Run ``operation``, retrying a bounded number of times on classified ``SQLITE_BUSY``.

    A non-busy ``OperationalError`` is re-raised immediately (not retried). Exhausting the retry
    budget fails closed with ``SQLITE_BUSY_EXHAUSTED`` — contention is never swallowed silently.
    """
    if retries < 0:
        raise PersistenceError("RETRIES_INVALID", "retries must be non-negative")
    attempt = 0
    while True:
        try:
            return operation()
        except sqlite3.OperationalError as exc:
            if classify_operational_error(exc) != "SQLITE_BUSY":
                raise
            if attempt >= retries:
                raise PersistenceError(
                    "SQLITE_BUSY_EXHAUSTED",
                    f"database remained locked after {retries} retries",
                ) from exc
            sleep((base_backoff_ms * (2**attempt)) / 1000)
            attempt += 1
