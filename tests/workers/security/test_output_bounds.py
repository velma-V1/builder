"""Task 3.2 security — SEC-PH3-03: worker output is bounded (threat T-03).

A hostile/broken task emitting unbounded output must not exhaust orchestrator memory: the stream
truncates at the total cap and the task fails with output_overflow. The orchestrator survives.
"""

from __future__ import annotations

import pytest

from factory.workers import streaming
from factory.workers.execution import RawWorkerEvent, TaskExecutor
from factory.workers.models import ExecutionEventType
from factory.workers.streaming import CHUNK_BYTE_LIMIT

pytestmark = pytest.mark.security


def test_sec_ph3_03_unbounded_output_is_capped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(streaming, "TOTAL_BYTE_LIMIT", 256 * 1024)

    def flood() -> object:
        # would be ~10 MiB if unbounded; each chunk is itself clipped to the per-chunk cap.
        for _ in range(160):
            yield RawWorkerEvent(ExecutionEventType.STDOUT, data=b"x" * (CHUNK_BYTE_LIMIT * 2))
        yield RawWorkerEvent(ExecutionEventType.END, exit_code=0)

    result = TaskExecutor().execute("TASK-flood", flood())

    assert result.truncated is True
    assert result.failure_cause == "output_overflow"
    stream = TaskExecutor().stream_for("TASK-flood")  # separate executor: no leak across instances
    assert stream is None


def test_sec_ph3_03_single_giant_chunk_clipped() -> None:
    giant = RawWorkerEvent(ExecutionEventType.STDOUT, data=b"y" * (CHUNK_BYTE_LIMIT * 100))
    result = TaskExecutor().execute(
        "TASK-giant", [giant, RawWorkerEvent(ExecutionEventType.END, exit_code=0)]
    )
    # a single oversized chunk is clipped to the per-chunk cap, not stored whole.
    executor = TaskExecutor()
    executor.execute("TASK-giant", [giant, RawWorkerEvent(ExecutionEventType.END, exit_code=0)])
    stream = executor.stream_for("TASK-giant")
    assert stream is not None
    assert len(stream.events[1].payload.encode()) <= CHUNK_BYTE_LIMIT
    assert result.exit_code == 0  # clip alone (within total cap) is not a failure
