from __future__ import annotations

import threading
from dataclasses import dataclass, field

from factory.contracts.activation.store import ActivationReader
from factory.contracts.errors import ContractError
from factory.contracts.models import CacheEntry, ErrorCode


@dataclass(slots=True)
class RuntimeContractCache:
    _entries: dict[tuple[str, str], CacheEntry] = field(default_factory=dict)
    _lock: threading.RLock = field(default_factory=threading.RLock)

    def publish(self, entry: CacheEntry) -> None:
        with self._lock:
            key = (entry.record.project_id, entry.record.contract_id)
            self._entries[key] = entry

    def get(self, project_id: str, contract_id: str, reader: ActivationReader) -> CacheEntry:
        key = (project_id, contract_id)
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                raise ContractError(
                    ErrorCode.CACHE_QUARANTINED, f"no cached entry for {project_id}/{contract_id}"
                )

            current = reader.get_active(project_id, contract_id)
            stale = (
                current is None
                or current.contract_version != entry.record.contract_version
                or current.schema_version != entry.record.schema_version
                or current.generation != entry.record.generation
                or current.content_hash != entry.record.content_hash
            )
            if stale:
                del self._entries[key]
                raise ContractError(
                    ErrorCode.CACHE_QUARANTINED,
                    f"cache entry is stale for {project_id}/{contract_id}",
                )

            return entry

    def quarantine(self, project_id: str, contract_id: str, reason: str) -> None:
        del reason  # recorded by the caller's audit trail; the cache itself only forgets
        with self._lock:
            self._entries.pop((project_id, contract_id), None)
