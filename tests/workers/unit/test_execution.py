"""Task 3.2 — TaskExecutor event collection + result classification (CMP-WORKER)."""

from __future__ import annotations

import hashlib

from factory.workers.execution import CancelToken, RawWorkerEvent, TaskExecutor
from factory.workers.models import ExecutionEventType


def _out(data: bytes) -> RawWorkerEvent:
    return RawWorkerEvent(kind=ExecutionEventType.STDOUT, data=data)


def _end(exit_code: int) -> RawWorkerEvent:
    return RawWorkerEvent(kind=ExecutionEventType.END, exit_code=exit_code)


def test_clean_run_exit_zero_has_no_failure_cause() -> None:
    result = TaskExecutor().execute("TASK-001", [_out(b"ok"), _end(0)])
    assert result.exit_code == 0
    assert result.failure_cause is None
    assert result.truncated is False


def test_nonzero_exit_classified() -> None:
    result = TaskExecutor().execute("TASK-001", [_out(b"boom"), _end(1)])
    assert result.exit_code == 1
    assert result.failure_cause == "nonzero_exit"


def test_missing_end_is_heartbeat_loss() -> None:
    result = TaskExecutor().execute("TASK-001", [_out(b"partial")])
    assert result.exit_code is None
    assert result.failure_cause == "heartbeat_loss"


def test_cancellation_mid_stream_classified() -> None:
    token = CancelToken()

    def source() -> object:
        yield _out(b"chunk-1")
        token.cancel()
        yield _out(b"chunk-2")
        yield _end(0)

    result = TaskExecutor().execute("TASK-001", source(), cancel_token=token)
    assert result.failure_cause == "cancelled"
    assert result.exit_code is None


def test_events_captured_counts_start_body_end() -> None:
    result = TaskExecutor().execute("TASK-001", [_out(b"a"), _out(b"b"), _end(0)])
    # START + 2 STDOUT + END
    assert result.events_captured == 4


def test_output_hash_is_deterministic() -> None:
    r1 = TaskExecutor().execute("TASK-001", [_out(b"same"), _end(0)])
    r2 = TaskExecutor().execute("TASK-002", [_out(b"same"), _end(0)])
    assert r1.output_hash == r2.output_hash == hashlib.sha256(b"same").hexdigest()


def test_stream_for_returns_captured_stream() -> None:
    executor = TaskExecutor()
    executor.execute("TASK-001", [_out(b"x"), _end(0)])
    stream = executor.stream_for("TASK-001")
    assert stream is not None
    assert stream.events[0].event_type is ExecutionEventType.START
    assert executor.stream_for("TASK-404") is None
