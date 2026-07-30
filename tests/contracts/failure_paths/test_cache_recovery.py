from dataclasses import dataclass
from pathlib import Path

import pytest

from factory.contracts.activation.store import (
    SQLiteActivationReader,
    _SQLiteActivationWriter,
    apply_migrations,
)
from factory.contracts.cache.runtime_cache import RuntimeContractCache
from factory.contracts.errors import ContractError
from factory.contracts.models import ActivationRecord, CacheEntry, ErrorCode

pytestmark = pytest.mark.failure_path

MIGRATIONS_ROOT = Path("migrations/contracts")


@dataclass
class _StaleReader:
    """Reports a different content_hash than what the cache currently holds."""

    real_reader: SQLiteActivationReader
    lie_about_hash: str

    def get_active(self, project_id: str, contract_id: str) -> ActivationRecord | None:
        record = self.real_reader.get_active(project_id, contract_id)
        if record is None:
            return None
        return ActivationRecord(
            project_id=record.project_id,
            contract_id=record.contract_id,
            contract_version=record.contract_version,
            schema_version=record.schema_version,
            generation=record.generation,
            content_hash=self.lie_about_hash,
            runtime_status=record.runtime_status,
        )

    def get_generation(self, project_id: str) -> int:
        return self.real_reader.get_generation(project_id)


def test_cache_quarantines_on_mismatch_and_recovers_after_republish(tmp_path: Path) -> None:
    db_path = tmp_path / "activation.sqlite3"
    apply_migrations(db_path, MIGRATIONS_ROOT)
    writer = _SQLiteActivationWriter(db_path)
    reader = SQLiteActivationReader(db_path)
    cache = RuntimeContractCache()

    record = writer.activate_transactionally(
        project_id="PROJ-001",
        contract_id="TASK-001",
        contract_version=1,
        schema_version="1.0",
        content_hash="a" * 64,
        canonical_json=b"{}",
        validation_report_json="{}",
        impact_report_json="{}",
        policy_decision_json="{}",
        evidence_json="{}",
        expected_generation=0,
        rollback_contract_version=None,
    )
    entry = CacheEntry(record=record, canonical_bytes=b"{}", document={})
    cache.publish(entry)

    # Simulate a corrupted/rebuilt cache entry that no longer matches the committed SQLite state.
    lying_reader = _StaleReader(real_reader=reader, lie_about_hash="b" * 64)
    with pytest.raises(ContractError) as raised:
        cache.get("PROJ-001", "TASK-001", lying_reader)
    assert raised.value.code is ErrorCode.CACHE_QUARANTINED

    # The quarantined entry must not silently resurrect itself against the real reader either,
    # since publish() was never called again yet.
    with pytest.raises(ContractError):
        cache.get("PROJ-001", "TASK-001", reader)

    # Recovery: rebuild the cache entry from the still-committed canonical bytes (no new
    # generation is required — the underlying activation never changed) and republish.
    cache.publish(CacheEntry(record=record, canonical_bytes=b"{}", document={}))
    recovered = cache.get("PROJ-001", "TASK-001", reader)
    assert recovered.record.content_hash == "a" * 64


def test_quarantine_then_get_on_a_never_republished_entry_stays_rejected(tmp_path: Path) -> None:
    db_path = tmp_path / "activation.sqlite3"
    apply_migrations(db_path, MIGRATIONS_ROOT)
    writer = _SQLiteActivationWriter(db_path)
    reader = SQLiteActivationReader(db_path)
    cache = RuntimeContractCache()

    record = writer.activate_transactionally(
        project_id="PROJ-001",
        contract_id="TASK-001",
        contract_version=1,
        schema_version="1.0",
        content_hash="a" * 64,
        canonical_json=b"{}",
        validation_report_json="{}",
        impact_report_json="{}",
        policy_decision_json="{}",
        evidence_json="{}",
        expected_generation=0,
        rollback_contract_version=None,
    )
    cache.publish(CacheEntry(record=record, canonical_bytes=b"{}", document={}))
    cache.quarantine("PROJ-001", "TASK-001", reason="manual test quarantine")

    with pytest.raises(ContractError) as raised:
        cache.get("PROJ-001", "TASK-001", reader)
    assert raised.value.code is ErrorCode.CACHE_QUARANTINED
