"""Bounded execution-output streaming (PH-3, CMP-WORKER, Task 3.2).

Worker output is UNTRUSTED (trust Zone 3). It is size-bounded to prevent resource exhaustion
(threat T-03): a per-chunk cap and a per-task total cap. On breach the stream is truncated and the
task is failed with ``output_overflow`` — the orchestrator must survive a hostile/broken task that
emits unbounded output. Output is never executed; it is only accumulated and hashed (deterministic
dedup key). Events are append-only (never mutated), mirroring the PH-2 journal discipline.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime

from factory.workers.models import ExecutionEvent, ExecutionEventType

# Zone-3 output bounds. 64 KiB/chunk, 512 MiB/task (spec §Execution Event Stream / §Threats T-03).
CHUNK_BYTE_LIMIT = 64 * 1024
TOTAL_BYTE_LIMIT = 512 * 1024 * 1024


def _utcnow() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(slots=True)
class OutputAccumulator:
    """Incrementally hashes and size-caps captured output bytes.

    Truncation is sticky: once the total cap is breached, further bytes are rejected and
    ``truncated`` stays True. Per-chunk oversize bytes are clipped (not silently dropped whole) so
    the running hash reflects exactly what was retained.
    """

    _hasher: hashlib._Hash = field(default_factory=hashlib.sha256)
    total_bytes: int = 0
    truncated: bool = False

    def add(self, data: bytes) -> bool:
        """Accept output bytes. Returns False if this call caused/continued truncation."""
        if self.truncated:
            return False
        chunk = data[:CHUNK_BYTE_LIMIT]  # clip an oversized single chunk
        remaining = TOTAL_BYTE_LIMIT - self.total_bytes
        if len(chunk) > remaining:
            chunk = chunk[:remaining]
            self.truncated = True
        self._hasher.update(chunk)
        self.total_bytes += len(chunk)
        return not self.truncated

    @property
    def output_hash(self) -> str:
        return self._hasher.hexdigest()


@dataclass(slots=True)
class ExecutionStream:
    """Append-only collector of ExecutionEvents for a single task execution.

    Enforces sequence ordering and captures STDOUT/STDERR through a bounded accumulator. The stream
    holds NO authoritative task state — it produces the raw material StateIntegration (Task 3.3)
    routes to the PH-2 single writer.
    """

    task_id: str
    _events: list[ExecutionEvent] = field(default_factory=list)
    _accumulator: OutputAccumulator = field(default_factory=OutputAccumulator)
    _sequence: int = 0

    def record(self, event_type: ExecutionEventType, payload: bytes | str) -> ExecutionEvent:
        """Append one event. Output payloads are size-bounded; event stores the retained text."""
        raw = payload.encode() if isinstance(payload, str) else payload
        if event_type in (ExecutionEventType.STDOUT, ExecutionEventType.STDERR):
            self._accumulator.add(raw)
        event = ExecutionEvent(
            task_id=self.task_id,
            sequence=self._sequence,
            event_type=event_type,
            occurred_at=_utcnow(),
            payload=raw[:CHUNK_BYTE_LIMIT].decode(errors="replace"),
        )
        self._events.append(event)
        self._sequence += 1
        return event

    @property
    def events(self) -> tuple[ExecutionEvent, ...]:
        return tuple(self._events)

    @property
    def output_hash(self) -> str:
        return self._accumulator.output_hash

    @property
    def truncated(self) -> bool:
        return self._accumulator.truncated
