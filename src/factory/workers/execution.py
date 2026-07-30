"""Task execution + event collection (PH-3, CMP-WORKER, Task 3.2).

`TaskExecutor.execute` drives a single task's output stream into a bounded `ExecutionStream` and
returns an `ExecutionResult`. It performs NO authoritative task-state write — that is Task 3.3's job
via the PH-2 single writer. The worker's raw output is injected as a `RawOutputSource` (an iterable
of `RawWorkerEvent`), which is the seam a real subprocess reader (or a PH-5 sandbox) plugs into;
this keeps execution logic testable without forking processes.

Failure-cause precedence (most severe first): output_overflow → cancelled → heartbeat_loss (stream
ended with no END event) → nonzero_exit. A clean run (END, exit 0, not truncated) has cause None.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from factory.workers.models import ExecutionEventType, ExecutionResult
from factory.workers.streaming import ExecutionStream


@dataclass(slots=True)
class RawWorkerEvent:
    """One raw output event from a worker process (pre-bounding).

    ``exit_code`` is only meaningful on an END event. ``data`` carries STDOUT/STDERR bytes/text.
    """

    kind: ExecutionEventType
    data: bytes | str = b""
    exit_code: int | None = None


# The seam a subprocess/sandbox reader implements: yields raw events until the process finishes.
RawOutputSource = Iterable[RawWorkerEvent]


@dataclass(slots=True)
class CancelToken:
    """Cooperative cancellation flag checked between events (SIGTERM semantics upstream)."""

    cancelled: bool = False

    def cancel(self) -> None:
        self.cancelled = True


@dataclass(slots=True)
class TaskExecutor:
    """Executes one task by consuming its bounded output stream. Stateless across tasks."""

    _streams: dict[str, ExecutionStream] = field(default_factory=dict, init=False)

    def execute(
        self,
        task_id: str,
        output_source: RawOutputSource,
        cancel_token: CancelToken | None = None,
    ) -> ExecutionResult:
        stream = ExecutionStream(task_id)
        self._streams[task_id] = stream
        stream.record(ExecutionEventType.START, b"")

        exit_code: int | None = None
        saw_end = False
        cancelled = False

        for raw in output_source:
            if cancel_token is not None and cancel_token.cancelled:
                cancelled = True
                break
            if raw.kind is ExecutionEventType.END:
                saw_end = True
                exit_code = raw.exit_code
                stream.record(ExecutionEventType.END, raw.data)
                break
            stream.record(raw.kind, raw.data)
            if stream.truncated:
                break

        return ExecutionResult(
            task_id=task_id,
            exit_code=exit_code,
            output_hash=stream.output_hash,
            events_captured=len(stream.events),
            truncated=stream.truncated,
            failure_cause=_classify(
                truncated=stream.truncated,
                cancelled=cancelled,
                saw_end=saw_end,
                exit_code=exit_code,
            ),
        )

    def stream_for(self, task_id: str) -> ExecutionStream | None:
        """Return the captured stream for a task (dashboard/audit read), or None."""
        return self._streams.get(task_id)


def _classify(
    *, truncated: bool, cancelled: bool, saw_end: bool, exit_code: int | None
) -> str | None:
    if truncated:
        return "output_overflow"
    if cancelled:
        return "cancelled"
    if not saw_end:
        return "heartbeat_loss"
    if exit_code != 0:
        return "nonzero_exit"
    return None
