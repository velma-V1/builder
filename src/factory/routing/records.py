"""Append-only model-execution ledger — CTR-MODEL-EXEC-RECORD (``01J §3.1/§3.2``).

The ledger is the authoritative, model-neutral provenance store. It is **append-only**: a record id
is written exactly once and never mutated. State progress (e.g. a running attempt that fails, then a
fallback) is expressed as *new* records — the failed attempt is closed with a terminal status via a
fresh record id, and the substitute attempt supersedes it. This mirrors the security-spine audit
rule (``UNIQUE`` op ids, no update/delete) without requiring the durable SQLite store, which the
live runtime phase wires underneath the same :class:`RecordStore` port.
"""

from __future__ import annotations

import threading
from collections.abc import Iterable, Sequence
from typing import Protocol

from factory.routing.errors import RoutingError
from factory.routing.models import (
    ExecutionRecord,
    ExecutionStatus,
    FallbackRecord,
)


class RecordStore(Protocol):
    """Storage port for the execution ledger. The preinstallation core uses an in-memory list;
    the live phase supplies a durable append-only SQLite-backed implementation."""

    def append(self, record: ExecutionRecord) -> None: ...
    def all(self) -> Sequence[ExecutionRecord]: ...


class InMemoryRecordStore:
    """Deterministic, ordered, append-only, thread-safe record store with a duplicate-id guard."""

    __slots__ = ("_ids", "_lock", "_records")

    def __init__(self, seed: Iterable[ExecutionRecord] = ()) -> None:
        self._records: list[ExecutionRecord] = []
        self._ids: set[str] = set()
        self._lock = threading.Lock()
        for record in seed:
            self.append(record)

    def append(self, record: ExecutionRecord) -> None:
        with self._lock:
            if record.record_id in self._ids:
                raise RoutingError(
                    "RECORD_DUPLICATE", f"execution record {record.record_id} already exists"
                )
            self._ids.add(record.record_id)
            self._records.append(record)

    def all(self) -> Sequence[ExecutionRecord]:
        with self._lock:
            return tuple(self._records)


class ExecutionLedger:
    """Authoritative append-only provenance with derived, read-only queries."""

    __slots__ = ("_fallbacks", "_store")

    def __init__(self, store: RecordStore | None = None) -> None:
        self._store: RecordStore = store if store is not None else InMemoryRecordStore()
        self._fallbacks: list[FallbackRecord] = []

    def record(self, record: ExecutionRecord) -> ExecutionRecord:
        """Append a new record. A ``supersedes`` link must reference an existing record."""
        if record.supersedes is not None and self.get(record.supersedes) is None:
            raise RoutingError(
                "RECORD_SUPERSEDE_UNKNOWN",
                f"record {record.record_id} supersedes unknown {record.supersedes}",
            )
        self._store.append(record)
        return record

    def restore(self, records: Iterable[ExecutionRecord]) -> int:
        """Rebuild execution history from a durable snapshot after a restart.

        Records already present are skipped, so restore is idempotent and cannot raise
        ``RECORD_DUPLICATE`` when replayed. Returns the number of records newly restored."""
        restored = 0
        for record in records:
            if self.get(record.record_id) is None:
                self._store.append(record)
                restored += 1
        return restored

    def get(self, record_id: str) -> ExecutionRecord | None:
        for record in self._store.all():
            if record.record_id == record_id:
                return record
        return None

    def for_task(self, task_id: str) -> tuple[ExecutionRecord, ...]:
        return tuple(r for r in self._store.all() if r.task_id == task_id)

    def latest_for_stage(self, task_id: str, stage_id: str) -> ExecutionRecord | None:
        matches = [r for r in self._store.all() if r.task_id == task_id and r.stage_id == stage_id]
        return matches[-1] if matches else None

    def next_attempt(self, task_id: str, stage_id: str) -> int:
        latest = self.latest_for_stage(task_id, stage_id)
        return 1 if latest is None else latest.attempt + 1

    def register_fallback(self, fallback: FallbackRecord) -> FallbackRecord:
        """Record a disclosed substitution linking two existing records (``01J §3.2``)."""
        if self.get(fallback.from_record_id) is None:
            raise RoutingError(
                "FALLBACK_FROM_UNKNOWN", f"fallback from unknown record {fallback.from_record_id}"
            )
        if self.get(fallback.to_record_id) is None:
            raise RoutingError(
                "FALLBACK_TO_UNKNOWN", f"fallback to unknown record {fallback.to_record_id}"
            )
        self._fallbacks.append(fallback)
        return fallback

    def fallbacks(self) -> tuple[FallbackRecord, ...]:
        return tuple(self._fallbacks)

    def all_records(self) -> tuple[ExecutionRecord, ...]:
        return tuple(self._store.all())

    def in_flight(self) -> tuple[ExecutionRecord, ...]:
        """Records with a non-terminal status — the reconciliation surface after a restart."""
        return tuple(r for r in self._store.all() if r.status is ExecutionStatus.RUNNING)
