"""Task 3.2 — bounded execution-output streaming (CMP-WORKER)."""

from __future__ import annotations

import hashlib

import pytest

from factory.workers import streaming
from factory.workers.models import ExecutionEventType
from factory.workers.streaming import CHUNK_BYTE_LIMIT, ExecutionStream, OutputAccumulator


def test_accumulator_hashes_retained_bytes() -> None:
    acc = OutputAccumulator()
    acc.add(b"hello ")
    acc.add(b"world")
    assert acc.output_hash == hashlib.sha256(b"hello world").hexdigest()
    assert acc.total_bytes == 11
    assert acc.truncated is False


def test_accumulator_clips_oversized_single_chunk() -> None:
    acc = OutputAccumulator()
    oversized = b"x" * (CHUNK_BYTE_LIMIT + 5000)
    acc.add(oversized)
    assert acc.total_bytes == CHUNK_BYTE_LIMIT  # clipped to per-chunk cap


def test_accumulator_total_limit_is_sticky(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(streaming, "TOTAL_BYTE_LIMIT", 10)
    acc = OutputAccumulator()
    assert acc.add(b"12345") is True
    assert acc.add(b"678901234") is False  # crosses the 10-byte cap
    assert acc.truncated is True
    assert acc.add(b"more") is False  # sticky: stays truncated
    assert acc.total_bytes == 10


def test_stream_records_events_in_sequence() -> None:
    stream = ExecutionStream("TASK-001")
    stream.record(ExecutionEventType.START, b"")
    stream.record(ExecutionEventType.STDOUT, b"line-1")
    stream.record(ExecutionEventType.END, b"")
    seqs = [e.sequence for e in stream.events]
    assert seqs == [0, 1, 2]
    assert stream.events[0].event_type is ExecutionEventType.START


def test_stream_bounds_stdout_and_exposes_hash() -> None:
    stream = ExecutionStream("TASK-001")
    stream.record(ExecutionEventType.STDOUT, "abc")
    assert stream.output_hash == hashlib.sha256(b"abc").hexdigest()
    assert stream.truncated is False


def test_stream_truncation_flag_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(streaming, "TOTAL_BYTE_LIMIT", 4)
    stream = ExecutionStream("TASK-001")
    stream.record(ExecutionEventType.STDOUT, b"12345")
    assert stream.truncated is True
