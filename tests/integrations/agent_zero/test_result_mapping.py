"""Result mapping: malformed payloads and incomplete terminal streams are flagged, never hidden."""

from __future__ import annotations

from factory.integrations.agent_zero.event_validation import validate_event_stream
from factory.integrations.agent_zero.fake_transport import event
from factory.integrations.agent_zero.models import AgentZeroEventType, WorkerOutcome
from factory.integrations.agent_zero.result_mapping import map_events_to_result


def test_completed_with_no_patches_or_artifacts_is_incomplete() -> None:
    events = (
        event("wo-1", 0, AgentZeroEventType.STARTED),
        event("wo-1", 1, AgentZeroEventType.COMPLETED),
    )
    result = map_events_to_result("wo-1", events)
    assert result.worker_claimed_outcome is WorkerOutcome.SUCCESS
    assert result.incomplete
    assert "no patches or artifacts" in result.reason


def test_completed_with_patch_but_no_evidence_is_incomplete() -> None:
    events = (
        event("wo-1", 0, AgentZeroEventType.STARTED),
        event(
            "wo-1",
            1,
            AgentZeroEventType.PATCH_PROPOSED,
            target_path="src/x.py",
            content_digest="c" * 64,
        ),
        event("wo-1", 2, AgentZeroEventType.COMPLETED),
    )
    result = map_events_to_result("wo-1", events)
    assert result.incomplete
    assert "no evidence" in result.reason


def test_stream_with_no_terminal_event_is_incomplete() -> None:
    events = (
        event("wo-1", 0, AgentZeroEventType.STARTED),
        event("wo-1", 1, AgentZeroEventType.PROGRESS),
    )
    result = map_events_to_result("wo-1", events)
    assert result.incomplete
    assert result.worker_claimed_outcome is WorkerOutcome.FAILURE
    assert "without a terminal event" in result.reason


def test_patch_event_missing_content_digest_is_malformed() -> None:
    events = (
        event("wo-1", 0, AgentZeroEventType.PATCH_PROPOSED, target_path="src/x.py"),
        event("wo-1", 1, AgentZeroEventType.COMPLETED),
    )
    result = map_events_to_result("wo-1", events)
    assert result.malformed
    assert result.patches == ()


def test_patch_event_with_non_hex_digest_is_malformed() -> None:
    events = (
        event(
            "wo-1",
            0,
            AgentZeroEventType.PATCH_PROPOSED,
            target_path="src/x.py",
            content_digest="not-a-real-digest",
        ),
        event("wo-1", 1, AgentZeroEventType.COMPLETED),
    )
    result = map_events_to_result("wo-1", events)
    assert result.malformed


def test_artifact_event_missing_path_is_malformed() -> None:
    events = (
        event("wo-1", 0, AgentZeroEventType.ARTIFACT_PRODUCED, content_digest="d" * 64),
        event("wo-1", 1, AgentZeroEventType.COMPLETED),
    )
    result = map_events_to_result("wo-1", events)
    assert result.malformed
    assert result.artifacts == ()


def test_evidence_event_missing_kind_is_malformed() -> None:
    events = (
        event("wo-1", 0, AgentZeroEventType.EVIDENCE_ATTACHED, detail="no kind given"),
        event("wo-1", 1, AgentZeroEventType.COMPLETED),
    )
    result = map_events_to_result("wo-1", events)
    assert result.malformed


def test_well_formed_complete_stream_is_neither_malformed_nor_incomplete() -> None:
    events = (
        event("wo-1", 0, AgentZeroEventType.STARTED),
        event(
            "wo-1",
            1,
            AgentZeroEventType.PATCH_PROPOSED,
            target_path="src/x.py",
            content_digest="e" * 64,
        ),
        event("wo-1", 2, AgentZeroEventType.EVIDENCE_ATTACHED, kind="test_run", detail="ok"),
        event("wo-1", 3, AgentZeroEventType.COMPLETED),
    )
    result = map_events_to_result("wo-1", events)
    assert not result.malformed
    assert not result.incomplete
    assert result.worker_claimed_outcome is WorkerOutcome.SUCCESS


def test_validated_stream_feeds_result_mapping_directly() -> None:
    events = (
        event("wo-1", 0, AgentZeroEventType.STARTED),
        event("wo-1", 1, AgentZeroEventType.FAILED, reason="disk full"),
    )
    validated = validate_event_stream(events)
    result = map_events_to_result("wo-1", validated.accepted)
    assert result.worker_claimed_outcome is WorkerOutcome.FAILURE
    assert result.reason == "disk full"
