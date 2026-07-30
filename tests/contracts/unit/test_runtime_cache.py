from dataclasses import dataclass

import pytest

from factory.contracts.cache.runtime_cache import RuntimeContractCache
from factory.contracts.errors import ContractError
from factory.contracts.models import ActivationRecord, CacheEntry, ErrorCode


@dataclass
class _FakeReader:
    active: ActivationRecord | None

    def get_active(self, project_id: str, contract_id: str) -> ActivationRecord | None:
        return self.active

    def get_generation(self, project_id: str) -> int:
        return self.active.generation if self.active else 0


def _record(**overrides: object) -> ActivationRecord:
    defaults: dict[str, object] = {
        "project_id": "PROJ-001",
        "contract_id": "TASK-001",
        "contract_version": 1,
        "schema_version": "1.0",
        "generation": 1,
        "content_hash": "a" * 64,
        "runtime_status": "ACTIVE",
    }
    defaults.update(overrides)
    return ActivationRecord(**defaults)  # type: ignore[arg-type]


def test_get_with_no_published_entry_raises_cache_quarantined() -> None:
    cache = RuntimeContractCache()
    with pytest.raises(ContractError) as raised:
        cache.get("PROJ-001", "TASK-001", _FakeReader(active=None))
    assert raised.value.code is ErrorCode.CACHE_QUARANTINED


def test_publish_then_get_returns_matching_entry() -> None:
    cache = RuntimeContractCache()
    record = _record()
    entry = CacheEntry(record=record, canonical_bytes=b"{}", document={})
    cache.publish(entry)

    result = cache.get("PROJ-001", "TASK-001", _FakeReader(active=record))
    assert result is entry


def test_get_detects_content_hash_mismatch_and_quarantines() -> None:
    cache = RuntimeContractCache()
    record = _record()
    entry = CacheEntry(record=record, canonical_bytes=b"{}", document={})
    cache.publish(entry)

    stale_reader = _FakeReader(active=_record(content_hash="b" * 64))
    with pytest.raises(ContractError) as raised:
        cache.get("PROJ-001", "TASK-001", stale_reader)
    assert raised.value.code is ErrorCode.CACHE_QUARANTINED

    with pytest.raises(ContractError):
        cache.get("PROJ-001", "TASK-001", stale_reader)


def test_get_detects_generation_mismatch() -> None:
    cache = RuntimeContractCache()
    record = _record()
    cache.publish(CacheEntry(record=record, canonical_bytes=b"{}", document={}))

    stale_reader = _FakeReader(active=_record(generation=2))
    with pytest.raises(ContractError) as raised:
        cache.get("PROJ-001", "TASK-001", stale_reader)
    assert raised.value.code is ErrorCode.CACHE_QUARANTINED


def test_get_when_no_longer_active_in_sqlite_quarantines() -> None:
    cache = RuntimeContractCache()
    record = _record()
    cache.publish(CacheEntry(record=record, canonical_bytes=b"{}", document={}))

    with pytest.raises(ContractError) as raised:
        cache.get("PROJ-001", "TASK-001", _FakeReader(active=None))
    assert raised.value.code is ErrorCode.CACHE_QUARANTINED


def test_quarantine_removes_only_the_targeted_entry() -> None:
    cache = RuntimeContractCache()
    record_a = _record()
    record_b = _record(contract_id="TASK-002")
    cache.publish(CacheEntry(record=record_a, canonical_bytes=b"{}", document={}))
    cache.publish(CacheEntry(record=record_b, canonical_bytes=b"{}", document={}))

    cache.quarantine("PROJ-001", "TASK-001", reason="test")

    with pytest.raises(ContractError):
        cache.get("PROJ-001", "TASK-001", _FakeReader(active=record_a))

    result = cache.get("PROJ-001", "TASK-002", _FakeReader(active=record_b))
    assert result.record.contract_id == "TASK-002"


def test_cache_entries_are_frozen_and_not_mutable_by_consumers() -> None:
    cache = RuntimeContractCache()
    record = _record()
    document = {"a": 1}
    entry = CacheEntry(record=record, canonical_bytes=b"{}", document=document)
    cache.publish(entry)

    fetched = cache.get("PROJ-001", "TASK-001", _FakeReader(active=record))
    with pytest.raises(Exception):  # noqa: B017 -- frozen dataclass raises FrozenInstanceError
        fetched.record = _record(contract_id="TASK-999")  # type: ignore[misc]
