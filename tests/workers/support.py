"""Reusable worker test doubles, intentionally separate from pytest's conftest module."""

from __future__ import annotations

from dataclasses import dataclass, field

from factory.workers.process import ProcessHandle


@dataclass(slots=True)
class FakeHandle:
    """Deterministic ProcessHandle. ``exit_code`` None means still running."""

    pid: int
    exit_code: int | None = None
    terminated: bool = False
    killed: bool = False

    def poll(self) -> int | None:
        return self.exit_code

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True

    def crash(self, exit_code: int = 137) -> None:
        self.exit_code = exit_code


@dataclass(slots=True)
class FakeSpawner:
    """Records spawned handles so tests can drive and inspect them."""

    handles: list[FakeHandle] = field(default_factory=list)
    _next_pid: int = 1000

    def spawn(self, worker_id: str) -> ProcessHandle:
        self._next_pid += 1
        handle = FakeHandle(pid=self._next_pid)
        self.handles.append(handle)
        return handle
