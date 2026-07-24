"""Memory store operations: propose, verify, supersede (PH-2, CMP-MEM)."""

from __future__ import annotations

import pytest

from factory.orchestrator.errors import OrchestratorError
from factory.orchestrator.models import MemoryRecord, MemoryRecordStatus


def test_propose_inserts_record_with_proposed_status(
    memory_store,
) -> None:
    record = MemoryRecord(
        record_id="MEM-001",
        project_id="PROJ-001",
        memory_class="PROJECT_AUTHORITY",
        status=MemoryRecordStatus.PROPOSED,
        source="human",
        scope="implementation",
        summary="test record",
        evidence_ref=None,
        supersedes=None,
        created_at="2026-07-24T00:00:00Z",
    )
    result = memory_store.propose(record)
    assert result.record_id == "MEM-001"
    assert result.status is MemoryRecordStatus.PROPOSED


def test_propose_with_non_proposed_status_raises(
    memory_store,
) -> None:
    record = MemoryRecord(
        record_id="MEM-002",
        project_id="PROJ-001",
        memory_class="PROJECT_AUTHORITY",
        status=MemoryRecordStatus.VERIFIED,  # invalid for propose
        source="human",
        scope="test",
        summary="should fail",
        evidence_ref=None,
        supersedes=None,
        created_at="2026-07-24T00:00:00Z",
    )
    try:
        memory_store.propose(record)
        pytest.fail("should have raised")
    except OrchestratorError as e:
        assert e.code == "MEMORY_INVALID_STATUS"


def test_verify_transitions_proposed_to_verified(
    memory_store,
) -> None:
    record = MemoryRecord(
        record_id="MEM-003",
        project_id="PROJ-001",
        memory_class="PROJECT_AUTHORITY",
        status=MemoryRecordStatus.PROPOSED,
        source="human",
        scope="test",
        summary="test record",
        evidence_ref=None,
        supersedes=None,
        created_at="2026-07-24T00:00:00Z",
    )
    memory_store.propose(record)
    result = memory_store.verify("MEM-003")
    assert result.record_id == "MEM-003"
    assert result.status is MemoryRecordStatus.VERIFIED


def test_verify_non_proposed_record_raises(
    memory_store,
) -> None:
    record = MemoryRecord(
        record_id="MEM-004",
        project_id="PROJ-001",
        memory_class="PROJECT_AUTHORITY",
        status=MemoryRecordStatus.PROPOSED,
        source="human",
        scope="test",
        summary="test",
        evidence_ref=None,
        supersedes=None,
        created_at="2026-07-24T00:00:00Z",
    )
    memory_store.propose(record)
    memory_store.verify("MEM-004")  # now VERIFIED
    try:
        memory_store.verify("MEM-004")  # try again
        pytest.fail("should have raised")
    except OrchestratorError as e:
        assert e.code == "MEMORY_INVALID_TRANSITION"


def test_verify_nonexistent_record_raises(
    memory_store,
) -> None:
    try:
        memory_store.verify("MEM-MISSING")
        pytest.fail("should have raised")
    except OrchestratorError as e:
        assert e.code == "MEMORY_NOT_FOUND"


def test_supersede_inserts_new_record_and_marks_prior_superseded(
    memory_store,
) -> None:
    prior = MemoryRecord(
        record_id="MEM-005",
        project_id="PROJ-001",
        memory_class="PROJECT_AUTHORITY",
        status=MemoryRecordStatus.PROPOSED,
        source="human",
        scope="test",
        summary="original",
        evidence_ref=None,
        supersedes=None,
        created_at="2026-07-24T00:00:00Z",
    )
    memory_store.propose(prior)

    new_record = MemoryRecord(
        record_id="MEM-005-V2",
        project_id="PROJ-001",
        memory_class="PROJECT_AUTHORITY",
        status=MemoryRecordStatus.PROPOSED,
        source="human",
        scope="test",
        summary="corrected",
        evidence_ref=None,
        supersedes="MEM-005",
        created_at="2026-07-24T00:00:01Z",
    )
    result = memory_store.supersede("MEM-005", new_record)
    assert result.record_id == "MEM-005-V2"
    assert result.supersedes == "MEM-005"

    prior_after = memory_store.get("MEM-005")
    assert prior_after is not None
    assert prior_after.status is MemoryRecordStatus.SUPERSEDED


def test_supersede_with_mismatched_supersedes_raises(
    memory_store,
) -> None:
    prior = MemoryRecord(
        record_id="MEM-006",
        project_id="PROJ-001",
        memory_class="PROJECT_AUTHORITY",
        status=MemoryRecordStatus.PROPOSED,
        source="human",
        scope="test",
        summary="original",
        evidence_ref=None,
        supersedes=None,
        created_at="2026-07-24T00:00:00Z",
    )
    memory_store.propose(prior)

    new_record = MemoryRecord(
        record_id="MEM-006-V2",
        project_id="PROJ-001",
        memory_class="PROJECT_AUTHORITY",
        status=MemoryRecordStatus.PROPOSED,
        source="human",
        scope="test",
        summary="corrected",
        evidence_ref=None,
        supersedes="MEM-WRONG",  # doesn't match record_id being superseded
        created_at="2026-07-24T00:00:01Z",
    )
    try:
        memory_store.supersede("MEM-006", new_record)
        pytest.fail("should have raised")
    except OrchestratorError as e:
        assert e.code == "MEMORY_INVALID_SUPERSESSION"


def test_supersede_nonexistent_record_raises(
    memory_store,
) -> None:
    new_record = MemoryRecord(
        record_id="MEM-NEW",
        project_id="PROJ-001",
        memory_class="PROJECT_AUTHORITY",
        status=MemoryRecordStatus.PROPOSED,
        source="human",
        scope="test",
        summary="new",
        evidence_ref=None,
        supersedes="MEM-MISSING",
        created_at="2026-07-24T00:00:00Z",
    )
    try:
        memory_store.supersede("MEM-MISSING", new_record)
        pytest.fail("should have raised")
    except OrchestratorError as e:
        assert e.code == "MEMORY_NOT_FOUND"


def test_get_retrieves_record_by_id(
    memory_store,
) -> None:
    record = MemoryRecord(
        record_id="MEM-007",
        project_id="PROJ-001",
        memory_class="PROJECT_AUTHORITY",
        status=MemoryRecordStatus.PROPOSED,
        source="human",
        scope="test",
        summary="test record",
        evidence_ref="evidence-123",
        supersedes=None,
        created_at="2026-07-24T00:00:00Z",
    )
    memory_store.propose(record)
    retrieved = memory_store.get("MEM-007")
    assert retrieved is not None
    assert retrieved.record_id == "MEM-007"
    assert retrieved.evidence_ref == "evidence-123"


def test_get_nonexistent_record_returns_none(
    memory_store,
) -> None:
    result = memory_store.get("MEM-NONEXISTENT")
    assert result is None
