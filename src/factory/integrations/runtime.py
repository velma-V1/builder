"""Builder-owned lifecycle for the pinned Agent Zero and WorldMonitor services."""

from __future__ import annotations

import sqlite3
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol


class IntegrationName(StrEnum):
    AGENT_ZERO = "agent-zero"
    WORLDMONITOR = "worldmonitor"


class IntegrationState(StrEnum):
    NOT_INSTALLED = "NOT_INSTALLED"
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    READY = "READY"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    DISABLED = "DISABLED"


class OperationState(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    INTERRUPTED = "INTERRUPTED"


class RuntimeFailure(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


class CommandRunner(Protocol):
    def run(self, command: tuple[str, ...], *, timeout_s: int) -> CommandResult: ...


@dataclass(frozen=True, slots=True)
class SubprocessCommandRunner:
    def run(self, command: tuple[str, ...], *, timeout_s: int) -> CommandResult:
        try:
            result = subprocess.run(  # noqa: S603
                command,
                capture_output=True,
                check=False,
                text=True,
                timeout=timeout_s,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            raise RuntimeFailure(f"command unavailable or timed out: {command[0]}: {exc}") from exc
        return CommandResult(result.returncode, result.stdout, result.stderr)


@dataclass(frozen=True, slots=True)
class ManagedServiceSpec:
    name: IntegrationName
    release: str
    commit: str
    compose_file: Path
    port: int
    readiness_url: str
    timeout_s: int
    enabled: bool = True
    build_from_source: bool = False
    verify_revision: bool = False

    def compose(self, *args: str) -> tuple[str, ...]:
        profile = ("--profile", "builder-enabled") if self.enabled else ()
        return ("docker", "compose", "-f", str(self.compose_file), *profile, *args)


@dataclass(frozen=True, slots=True)
class IntegrationRecord:
    sequence: int
    name: IntegrationName
    state: IntegrationState
    detail: str
    occurred_at: int


@dataclass(frozen=True, slots=True)
class IntegrationResultRecord:
    result_id: int
    name: IntegrationName
    operation_id: str
    status: str
    payload_json: str
    occurred_at: int


@dataclass(frozen=True, slots=True)
class IntegrationOperation:
    operation_id: str
    name: IntegrationName
    kind: str
    state: OperationState
    context_id: str | None
    request_json: str
    result_json: str | None
    reason: str | None
    actor: str
    created_at: int
    updated_at: int


@dataclass(frozen=True, slots=True)
class IntegrationStore:
    database_path: Path

    def __post_init__(self) -> None:
        with sqlite3.connect(self.database_path) as connection:
            tables = {
                str(row[0])
                for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
        required = {"integration_events", "integration_operations", "schema_migrations"}
        if not required.issubset(tables):
            raise RuntimeFailure("integration database schema is not current; run setup")

    def append(
        self, name: IntegrationName, state: IntegrationState, detail: str, occurred_at: int
    ) -> IntegrationRecord:
        with sqlite3.connect(self.database_path) as connection:
            cursor = connection.execute(
                "INSERT INTO integration_events (name, state, detail, occurred_at) "
                "VALUES (?, ?, ?, ?)",
                (name.value, state.value, detail, occurred_at),
            )
            sequence = int(cursor.lastrowid or 0)
        return IntegrationRecord(sequence, name, state, detail, occurred_at)

    def latest(self, name: IntegrationName) -> IntegrationRecord:
        with sqlite3.connect(self.database_path) as connection:
            row = connection.execute(
                "SELECT sequence, name, state, detail, occurred_at FROM integration_events "
                "WHERE name = ? ORDER BY sequence DESC LIMIT 1",
                (name.value,),
            ).fetchone()
        if row is None:
            return IntegrationRecord(0, name, IntegrationState.NOT_INSTALLED, "not installed", 0)
        return IntegrationRecord(
            sequence=int(row[0]),
            name=IntegrationName(row[1]),
            state=IntegrationState(row[2]),
            detail=str(row[3]),
            occurred_at=int(row[4]),
        )

    def save_result(
        self,
        name: IntegrationName,
        operation_id: str,
        status: str,
        payload_json: str,
        occurred_at: int,
    ) -> IntegrationResultRecord:
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                "INSERT INTO integration_operations "
                "(operation_id, name, kind, state, request_json, result_json, actor, "
                "created_at, updated_at) VALUES (?, ?, 'legacy', ?, '{}', ?, 'system', ?, ?)",
                (operation_id, name.value, status, payload_json, occurred_at, occurred_at),
            )
            result_id = int(
                connection.execute(
                    "SELECT rowid FROM integration_operations WHERE operation_id = ?",
                    (operation_id,),
                ).fetchone()[0]
            )
        return IntegrationResultRecord(
            result_id, name, operation_id, status, payload_json, occurred_at
        )

    def latest_result(self, name: IntegrationName) -> IntegrationResultRecord | None:
        with sqlite3.connect(self.database_path) as connection:
            row = connection.execute(
                "SELECT rowid, name, operation_id, state, result_json, updated_at "
                "FROM integration_operations WHERE name = ? AND result_json IS NOT NULL "
                "ORDER BY rowid DESC LIMIT 1",
                (name.value,),
            ).fetchone()
        if row is None:
            return None
        return IntegrationResultRecord(
            int(row[0]), IntegrationName(row[1]), str(row[2]), str(row[3]), str(row[4]), int(row[5])
        )

    def get_result(self, operation_id: str) -> IntegrationResultRecord | None:
        with sqlite3.connect(self.database_path) as connection:
            row = connection.execute(
                "SELECT rowid, name, operation_id, state, result_json, updated_at "
                "FROM integration_operations WHERE operation_id = ? AND result_json IS NOT NULL",
                (operation_id,),
            ).fetchone()
        if row is None:
            return None
        return IntegrationResultRecord(
            int(row[0]), IntegrationName(row[1]), str(row[2]), str(row[3]), str(row[4]), int(row[5])
        )

    def begin_operation(
        self,
        operation_id: str,
        name: IntegrationName,
        kind: str,
        request_json: str,
        actor: str,
        occurred_at: int,
        *,
        context_id: str | None = None,
    ) -> IntegrationOperation:
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                "INSERT INTO integration_operations "
                "(operation_id, name, kind, state, context_id, request_json, actor, "
                "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    operation_id,
                    name.value,
                    kind,
                    OperationState.PENDING.value,
                    context_id,
                    request_json,
                    actor,
                    occurred_at,
                    occurred_at,
                ),
            )
        operation = self.operation(operation_id)
        assert operation is not None
        return operation

    def update_operation(
        self,
        operation_id: str,
        state: OperationState,
        occurred_at: int,
        *,
        context_id: str | None = None,
        result_json: str | None = None,
        reason: str | None = None,
    ) -> IntegrationOperation:
        with sqlite3.connect(self.database_path) as connection:
            cursor = connection.execute(
                "UPDATE integration_operations SET state = ?, "
                "context_id = COALESCE(?, context_id), "
                "result_json = COALESCE(?, result_json), reason = ?, updated_at = ? "
                "WHERE operation_id = ?",
                (state.value, context_id, result_json, reason, occurred_at, operation_id),
            )
            if cursor.rowcount != 1:
                raise RuntimeFailure(f"unknown integration operation: {operation_id}")
        operation = self.operation(operation_id)
        assert operation is not None
        return operation

    def operation(self, operation_id: str) -> IntegrationOperation | None:
        with sqlite3.connect(self.database_path) as connection:
            row = connection.execute(
                "SELECT operation_id, name, kind, state, context_id, request_json, result_json, "
                "reason, actor, created_at, updated_at FROM integration_operations "
                "WHERE operation_id = ?",
                (operation_id,),
            ).fetchone()
        if row is None:
            return None
        return IntegrationOperation(
            str(row[0]),
            IntegrationName(row[1]),
            str(row[2]),
            OperationState(row[3]),
            None if row[4] is None else str(row[4]),
            str(row[5]),
            None if row[6] is None else str(row[6]),
            None if row[7] is None else str(row[7]),
            str(row[8]),
            int(row[9]),
            int(row[10]),
        )

    def unfinished_operations(self) -> tuple[IntegrationOperation, ...]:
        with sqlite3.connect(self.database_path) as connection:
            ids = [
                str(row[0])
                for row in connection.execute(
                    "SELECT operation_id FROM integration_operations WHERE state IN (?, ?)",
                    (OperationState.PENDING.value, OperationState.RUNNING.value),
                )
            ]
        return tuple(operation for item in ids if (operation := self.operation(item)) is not None)

    def latest_operation(self, name: IntegrationName) -> IntegrationOperation | None:
        with sqlite3.connect(self.database_path) as connection:
            row = connection.execute(
                "SELECT operation_id FROM integration_operations WHERE name = ? "
                "ORDER BY updated_at DESC, rowid DESC LIMIT 1",
                (name.value,),
            ).fetchone()
        return None if row is None else self.operation(str(row[0]))


@dataclass(slots=True)
class IntegrationRuntime:
    store: IntegrationStore
    runner: CommandRunner
    clock: Callable[[], int]

    def _record(
        self, spec: ManagedServiceSpec, state: IntegrationState, detail: str
    ) -> IntegrationRecord:
        return self.store.append(spec.name, state, detail, self.clock())

    def _checked(self, spec: ManagedServiceSpec, command: tuple[str, ...]) -> CommandResult:
        result = self.runner.run(command, timeout_s=spec.timeout_s)
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or "command failed"
            self._record(spec, IntegrationState.FAILED, detail)
            raise RuntimeFailure(detail)
        return result

    def _require_enabled(self, spec: ManagedServiceSpec) -> None:
        if not spec.enabled:
            detail = f"{spec.name.value} is disabled in Builder configuration"
            self._record(spec, IntegrationState.DISABLED, detail)
            raise RuntimeFailure(detail)

    def _verify_revision(self, spec: ManagedServiceSpec) -> str:
        if not spec.verify_revision:
            return "revision verification disabled"
        image = self._checked(
            spec, spec.compose("images", "--quiet", spec.name.value)
        ).stdout.strip()
        if not image:
            detail = f"{spec.name.value} image identity is missing"
            self._record(spec, IntegrationState.FAILED, detail)
            raise RuntimeFailure(detail)
        result = self._checked(
            spec,
            (
                "docker",
                "image",
                "inspect",
                "--format",
                '{{ index .Config.Labels "org.opencontainers.image.revision" }}',
                image,
            ),
        )
        actual = result.stdout.strip()
        if actual != spec.commit:
            detail = f"image revision mismatch: expected {spec.commit}, got {actual or 'missing'}"
            self._record(spec, IntegrationState.FAILED, detail)
            raise RuntimeFailure(detail)
        return f"image {image} revision {actual}"

    def install(self, spec: ManagedServiceSpec, *, actor: str) -> IntegrationRecord:
        self._require_enabled(spec)
        command = (
            spec.compose("build", "--pull") if spec.build_from_source else spec.compose("pull")
        )
        self._checked(spec, command)
        provenance = self._verify_revision(spec)
        return self._record(
            spec,
            IntegrationState.STOPPED,
            f"installed {spec.release} by {actor}; {provenance}",
        )

    def start(self, spec: ManagedServiceSpec, *, actor: str) -> IntegrationRecord:
        self._require_enabled(spec)
        provenance = self._verify_revision(spec)
        self._record(spec, IntegrationState.STARTING, f"start requested by {actor}")
        command = spec.compose("up", "-d", "--wait", "--wait-timeout", str(spec.timeout_s))
        try:
            self._checked(spec, command)
        except RuntimeFailure as original:
            try:
                cleanup = self.runner.run(
                    spec.compose("down", "--remove-orphans"), timeout_s=spec.timeout_s
                )
            except Exception as cleanup_error:
                detail = f"{original}; cleanup failed: {cleanup_error}"
                self._record(spec, IntegrationState.FAILED, detail)
                raise RuntimeFailure(detail) from original
            if cleanup.returncode != 0:
                cleanup_detail = (
                    cleanup.stderr.strip() or cleanup.stdout.strip() or "command failed"
                )
                detail = f"{original}; cleanup failed: {cleanup_detail}"
                self._record(spec, IntegrationState.FAILED, detail)
                raise RuntimeFailure(detail) from original
            detail = f"{original}; partial containers cleaned"
            self._record(spec, IntegrationState.FAILED, detail)
            raise RuntimeFailure(detail) from original
        return self._record(
            spec, IntegrationState.READY, f"ready at {spec.readiness_url}; {provenance}"
        )

    def stop(self, spec: ManagedServiceSpec, *, actor: str) -> IntegrationRecord:
        self._require_enabled(spec)
        self._checked(spec, spec.compose("stop"))
        return self._record(spec, IntegrationState.STOPPED, f"stopped by {actor}")

    def disable(self, spec: ManagedServiceSpec, *, actor: str) -> IntegrationRecord:
        self._require_enabled(spec)
        self._checked(spec, spec.compose("stop"))
        return self._record(spec, IntegrationState.DISABLED, f"disabled by {actor}; data preserved")

    def remove(self, spec: ManagedServiceSpec, *, actor: str) -> IntegrationRecord:
        self._require_enabled(spec)
        self._checked(spec, spec.compose("down", "--remove-orphans"))
        return self._record(
            spec, IntegrationState.NOT_INSTALLED, f"removed by {actor}; data preserved"
        )

    def logs(self, spec: ManagedServiceSpec, *, tail: int = 200) -> tuple[str, ...]:
        self._require_enabled(spec)
        if tail <= 0 or tail > 1000:
            raise ValueError("tail must be between 1 and 1000")
        result = self._checked(spec, spec.compose("logs", "--no-color", "--tail", str(tail)))
        return tuple(result.stdout.splitlines()[-tail:])

    def reconcile(self, specs: Sequence[ManagedServiceSpec]) -> tuple[IntegrationRecord, ...]:
        reconciled: list[IntegrationRecord] = []
        for spec in specs:
            current = self.store.latest(spec.name)
            if current.state not in {IntegrationState.READY, IntegrationState.STARTING}:
                reconciled.append(current)
                continue
            result = self.runner.run(
                spec.compose("ps", "--status", "running", "--quiet"), timeout_s=spec.timeout_s
            )
            if result.returncode == 0 and result.stdout.strip():
                reconciled.append(self._record(spec, IntegrationState.READY, "reconciled ready"))
            else:
                detail = result.stderr.strip() or "container missing during startup reconciliation"
                reconciled.append(self._record(spec, IntegrationState.FAILED, detail))
        return tuple(reconciled)


__all__ = [
    "CommandResult",
    "IntegrationName",
    "IntegrationOperation",
    "IntegrationRecord",
    "IntegrationResultRecord",
    "IntegrationRuntime",
    "IntegrationState",
    "IntegrationStore",
    "ManagedServiceSpec",
    "OperationState",
    "RuntimeFailure",
    "SubprocessCommandRunner",
]
