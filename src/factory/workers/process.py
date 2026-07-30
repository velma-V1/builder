"""Worker process abstraction + spawner protocol (PH-3, CMP-WORKER, Task 3.1).

The pool never calls ``subprocess`` directly: it depends on the ``ProcessSpawner`` /
``ProcessHandle`` protocols so process management is testable without forking real OS processes
and so PH-5 can substitute a sandbox-backed spawner without touching pool logic (loose coupling).
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from factory.workers.models import WorkerState


@runtime_checkable
class ProcessHandle(Protocol):
    """A live OS-process handle. Implementations wrap a real or fake process."""

    @property
    def pid(self) -> int: ...

    def poll(self) -> int | None:
        """Return the exit code if the process has exited, else None (still running)."""
        ...

    def terminate(self) -> None:
        """Request graceful termination (SIGTERM semantics)."""
        ...

    def kill(self) -> None:
        """Force termination (SIGKILL semantics)."""
        ...


@runtime_checkable
class ProcessSpawner(Protocol):
    """Factory for worker OS processes. Injected into WorkerPool for isolation."""

    def spawn(self, worker_id: str) -> ProcessHandle:
        """Start a new idle worker process and return its handle."""
        ...


@dataclass(slots=True)
class SubprocessHandle:
    """Real ProcessHandle backed by ``subprocess.Popen``."""

    _proc: subprocess.Popen[bytes]

    @property
    def pid(self) -> int:
        return self._proc.pid

    def poll(self) -> int | None:
        return self._proc.poll()

    def terminate(self) -> None:
        self._proc.terminate()

    def kill(self) -> None:
        self._proc.kill()


@dataclass(slots=True)
class SubprocessSpawner:
    """Default ProcessSpawner. Starts an idle worker stub that waits for a task contract.

    The concrete worker entrypoint/command is supplied by the caller; PH-3 owns only the pooling
    and lifecycle around it. Sandbox isolation of this command is a PH-5 concern (Dec C).
    """

    command: tuple[str, ...]

    def spawn(self, worker_id: str) -> ProcessHandle:
        proc = subprocess.Popen(  # noqa: S603 - command is caller-supplied, not shell-parsed
            list(self.command),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return SubprocessHandle(proc)


@dataclass(slots=True)
class WorkerProcess:
    """A single pool slot binding a worker identity to its OS-process handle.

    Mutable by design: the pool advances ``state`` and (un)binds ``task_id`` across the slot
    lifecycle. Never a source of authoritative task state.
    """

    worker_id: str
    handle: ProcessHandle
    process_epoch: str
    state: WorkerState = WorkerState.IDLE
    task_id: str | None = field(default=None)

    @property
    def pid(self) -> int:
        return self.handle.pid
