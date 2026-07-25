"""Task 3.2 failure-paths — output overflow, incomplete stream, cancel race (CMP-WORKER)."""

from __future__ import annotations

import pytest

from factory.workers import streaming
from factory.workers.execution import CancelToken, RawWorkerEvent, TaskExecutor
from factory.workers.models import ExecutionEventType

pytestmark = pytest.mark.failure_path


def _out(data: bytes) -> RawWorkerEvent:
    return RawWorkerEvent(kind=ExecutionEventType.STDOUT, data=data)


def test_output_overflow_truncates_and_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(streaming, "TOTAL_BYTE_LIMIT", 8)
    events = [
        _out(b"1234"),
        _out(b"5678xxxx"),
        _out(b"never"),
        RawWorkerEvent(ExecutionEventType.END, exit_code=0),
    ]
    result = TaskExecutor().execute("TASK-001", events)
    assert result.truncated is True
    assert result.failure_cause == "output_overflow"
    # stream stops at the overflow; the trailing END is never consumed
    assert result.exit_code is None


def test_incomplete_stream_reports_heartbeat_loss() -> None:
    # Worker emits some output then its process vanishes (no END) — a crash signature.
    result = TaskExecutor().execute("TASK-001", [_out(b"work..."), _out(b"more...")])
    assert result.failure_cause == "heartbeat_loss"


def test_cancel_before_any_event() -> None:
    token = CancelToken()
    token.cancel()
    result = TaskExecutor().execute(
        "TASK-001", [_out(b"should-not-run")], cancel_token=token
    )
    assert result.failure_cause == "cancelled"
    assert result.events_captured == 1  # only START recorded
