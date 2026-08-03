"""Authenticated control-plane service for Builder's two managed integrations."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Protocol

from factory.audit.models import AuditEvent, RecordKind
from factory.integrations.runtime import (
    IntegrationName,
    IntegrationOperation,
    IntegrationRecord,
    IntegrationRuntime,
    IntegrationState,
    ManagedServiceSpec,
    OperationState,
)
from factory.integrations.worldmonitor.models import IntelligenceRecord
from factory.orchestrator.models import TaskState


class IntegrationControlError(RuntimeError):
    pass


class AuditPort(Protocol):
    def append(self, event: AuditEvent) -> object: ...


class WorldClientPort(Protocol):
    def refresh_earthquakes(
        self, *, start_ms: int, end_ms: int, limit: int, now_ms: int
    ) -> tuple[IntelligenceRecord, ...]: ...


@dataclass(slots=True)
class IntegrationControlService:
    runtime: IntegrationRuntime
    specs: Mapping[IntegrationName, ManagedServiceSpec]
    world_client: WorldClientPort
    audit: AuditPort
    clock: Callable[[], int]

    def status(self, name: IntegrationName) -> IntegrationRecord:
        if not self.specs[name].enabled:
            return IntegrationRecord(
                0,
                name,
                IntegrationState.DISABLED,
                f"{name.value} is disabled in Builder configuration",
                self.clock(),
            )
        return self.runtime.store.latest(name)

    def latest_operation(self, name: IntegrationName) -> IntegrationOperation | None:
        return self.runtime.store.latest_operation(name)

    def is_enabled(self, name: IntegrationName) -> bool:
        return self.specs[name].enabled

    def _mutate(
        self,
        name: IntegrationName,
        action: str,
        actor: str,
        operation_id: str,
        operation: Callable[[], IntegrationRecord],
    ) -> IntegrationRecord:
        op_key = f"integration:{name.value}:{action}:{operation_id}"
        payload_hash = hashlib.sha256(f"{name.value}:{action}".encode()).hexdigest()
        self.audit.append(
            AuditEvent(
                op_key,
                RecordKind.INTENT,
                3,
                actor,
                f"integration.{action}",
                payload_hash,
                str(self.clock()),
                name.value,
            )
        )
        try:
            return operation()
        finally:
            current = self.runtime.store.latest(name)
            completion_hash = hashlib.sha256(
                f"{payload_hash}:{current.state.value}:{current.detail}".encode()
            ).hexdigest()
            self.audit.append(
                AuditEvent(
                    op_key,
                    RecordKind.COMPLETION,
                    3,
                    actor,
                    f"integration.{action}",
                    completion_hash,
                    str(self.clock()),
                    name.value,
                )
            )

    def install(self, name: IntegrationName, *, actor: str, operation_id: str) -> IntegrationRecord:
        return self._mutate(
            name,
            "install",
            actor,
            operation_id,
            lambda: self.runtime.install(self.specs[name], actor=actor),
        )

    def start(self, name: IntegrationName, *, actor: str, operation_id: str) -> IntegrationRecord:
        return self._mutate(
            name,
            "start",
            actor,
            operation_id,
            lambda: self.runtime.start(self.specs[name], actor=actor),
        )

    def stop(self, name: IntegrationName, *, actor: str, operation_id: str) -> IntegrationRecord:
        return self._mutate(
            name,
            "stop",
            actor,
            operation_id,
            lambda: self.runtime.stop(self.specs[name], actor=actor),
        )

    def disable(self, name: IntegrationName, *, actor: str, operation_id: str) -> IntegrationRecord:
        return self._mutate(
            name,
            "disable",
            actor,
            operation_id,
            lambda: self.runtime.disable(self.specs[name], actor=actor),
        )

    def remove(self, name: IntegrationName, *, actor: str, operation_id: str) -> IntegrationRecord:
        return self._mutate(
            name,
            "remove",
            actor,
            operation_id,
            lambda: self.runtime.remove(self.specs[name], actor=actor),
        )

    def logs(self, name: IntegrationName, *, tail: int = 200) -> tuple[str, ...]:
        self._require_enabled(name)
        return self.runtime.logs(self.specs[name], tail=tail)

    def _require_enabled(self, name: IntegrationName) -> None:
        if not self.specs[name].enabled:
            raise IntegrationControlError(f"{name.value} is disabled in Builder configuration")

    def _require_ready(self, name: IntegrationName) -> None:
        self._require_enabled(name)
        if self.status(name).state is not IntegrationState.READY:
            raise IntegrationControlError(f"{name.value} is not ready")

    def dispatch_agent_task(
        self,
        operation_id: str,
        request_json: str,
        *,
        actor: str,
        submit: Callable[[], str],
    ) -> IntegrationOperation:
        """Persist dispatch intent before creating the authoritative Builder task."""
        existing = self.runtime.store.operation(operation_id)
        if existing is not None:
            return existing
        self._require_ready(IntegrationName.AGENT_ZERO)
        op_key = f"integration:agent-zero:dispatch:{operation_id}"
        payload_hash = hashlib.sha256(request_json.encode()).hexdigest()
        self.audit.append(
            AuditEvent(
                op_key,
                RecordKind.INTENT,
                3,
                actor,
                "integration.agent-task",
                payload_hash,
                str(self.clock()),
                IntegrationName.AGENT_ZERO.value,
            )
        )
        self.runtime.store.begin_operation(
            operation_id,
            IntegrationName.AGENT_ZERO,
            "agent-task",
            request_json,
            actor,
            self.clock(),
        )
        try:
            task_id = submit()
        except Exception as exc:
            operation = self.runtime.store.update_operation(
                operation_id,
                OperationState.FAILED,
                self.clock(),
                reason=_bounded_reason(exc),
            )
        else:
            operation = self.runtime.store.update_operation(
                operation_id,
                OperationState.RUNNING,
                self.clock(),
                context_id=task_id,
            )
        completion_hash = hashlib.sha256(
            f"{payload_hash}:{operation.state.value}:{operation.context_id or ''}".encode()
        ).hexdigest()
        self.audit.append(
            AuditEvent(
                op_key,
                RecordKind.COMPLETION,
                3,
                actor,
                "integration.agent-task",
                completion_hash,
                str(self.clock()),
                IntegrationName.AGENT_ZERO.value,
            )
        )
        return operation

    def reconcile_agent_task(
        self, operation_id: str, state_for_task: Callable[[str], TaskState | None]
    ) -> IntegrationOperation:
        operation = self.runtime.store.operation(operation_id)
        if operation is None or operation.name is not IntegrationName.AGENT_ZERO:
            raise IntegrationControlError("Agent Zero operation was not found")
        if operation.state is not OperationState.RUNNING:
            return operation
        if operation.context_id is None:
            return self.runtime.store.update_operation(
                operation_id,
                OperationState.INTERRUPTED,
                self.clock(),
                reason="dispatch has no authoritative Builder task",
            )
        state = state_for_task(operation.context_id)
        if state is None:
            return self.runtime.store.update_operation(
                operation_id,
                OperationState.INTERRUPTED,
                self.clock(),
                reason="authoritative Builder task is missing",
            )
        if state is TaskState.COMPLETE:
            result_json = json.dumps(
                {"task_id": operation.context_id}, sort_keys=True, separators=(",", ":")
            )
            return self.runtime.store.update_operation(
                operation_id,
                OperationState.SUCCEEDED,
                self.clock(),
                result_json=result_json,
            )
        if state is TaskState.CANCELLED:
            return self.runtime.store.update_operation(
                operation_id,
                OperationState.CANCELLED,
                self.clock(),
                reason="Builder task cancelled",
            )
        if state in {
            TaskState.BLOCKED,
            TaskState.PAUSED,
            TaskState.QUARANTINED,
            TaskState.ROLLED_BACK,
        }:
            return self.runtime.store.update_operation(
                operation_id,
                OperationState.INTERRUPTED,
                self.clock(),
                reason=f"Builder task reconciled to {state.value}",
            )
        if state in {TaskState.FAILED, TaskState.REJECTED}:
            return self.runtime.store.update_operation(
                operation_id,
                OperationState.FAILED,
                self.clock(),
                reason=f"Builder task ended in {state.value}",
            )
        return operation

    def cancel_agent_task(
        self, operation_id: str, cancel_task: Callable[[str], object]
    ) -> IntegrationOperation:
        operation = self.runtime.store.operation(operation_id)
        if operation is None or operation.name is not IntegrationName.AGENT_ZERO:
            raise IntegrationControlError("Agent Zero operation was not found")
        if operation.state in {
            OperationState.CANCELLED,
            OperationState.SUCCEEDED,
            OperationState.FAILED,
            OperationState.INTERRUPTED,
        }:
            return operation
        if operation.context_id is None:
            return self.runtime.store.update_operation(
                operation_id,
                OperationState.CANCELLED,
                self.clock(),
                reason="cancelled before Builder task creation",
            )
        try:
            cancel_task(operation.context_id)
        except Exception as exc:
            return self.runtime.store.update_operation(
                operation_id,
                OperationState.FAILED,
                self.clock(),
                reason=f"cancellation failed: {_bounded_reason(exc)}",
            )
        return self.runtime.store.update_operation(
            operation_id,
            OperationState.CANCELLED,
            self.clock(),
            reason="cancelled by operator",
        )

    def refresh_worldmonitor(
        self,
        operation_id: str,
        *,
        start_ms: int,
        end_ms: int,
        limit: int,
        actor: str,
    ) -> IntegrationOperation:
        existing = self.runtime.store.operation(operation_id)
        if existing is not None:
            return existing
        self._require_ready(IntegrationName.WORLDMONITOR)
        request_json = json.dumps(
            {"start_ms": start_ms, "end_ms": end_ms, "limit": limit},
            sort_keys=True,
            separators=(",", ":"),
        )
        self.runtime.store.begin_operation(
            operation_id, IntegrationName.WORLDMONITOR, "refresh", request_json, actor, self.clock()
        )
        self.runtime.store.update_operation(operation_id, OperationState.RUNNING, self.clock())
        try:
            records = self.world_client.refresh_earthquakes(
                start_ms=start_ms, end_ms=end_ms, limit=limit, now_ms=self.clock()
            )
        except Exception as exc:
            reason = _bounded_reason(exc)
            self.runtime.store.append(
                IntegrationName.WORLDMONITOR, IntegrationState.DEGRADED, reason, self.clock()
            )
            return self.runtime.store.update_operation(
                operation_id, OperationState.FAILED, self.clock(), reason=reason
            )
        payload = json.dumps(
            {"records": [_world_record(record) for record in records]},
            sort_keys=True,
            separators=(",", ":"),
        )
        return self.runtime.store.update_operation(
            operation_id, OperationState.SUCCEEDED, self.clock(), result_json=payload
        )

    def reconcile_operations(
        self, state_for_task: Callable[[str], TaskState | None] | None = None
    ) -> tuple[IntegrationOperation, ...]:
        reconciled: list[IntegrationOperation] = []
        for operation in self.runtime.store.unfinished_operations():
            if (
                operation.name is IntegrationName.AGENT_ZERO
                and operation.context_id is not None
                and state_for_task is not None
            ):
                reconciled.append(self.reconcile_agent_task(operation.operation_id, state_for_task))
                continue
            reconciled.append(
                self.runtime.store.update_operation(
                    operation.operation_id,
                    OperationState.INTERRUPTED,
                    self.clock(),
                    reason="operation interrupted by Builder restart",
                )
            )
        return tuple(reconciled)


def _bounded_reason(exc: Exception) -> str:
    return (str(exc).strip() or type(exc).__name__)[:500]


def _world_record(record: IntelligenceRecord) -> dict[str, object]:
    return {
        "id": record.record_id,
        "category": record.category.value,
        "summary": record.normalized_summary,
        "geography": record.geography,
        "freshness": record.freshness.freshness.value,
        "source": {
            "name": record.source.source_name,
            "url": record.source.source_url,
            "record_id": record.source.upstream_record_id,
        },
        "digest": record.content_digest,
        "raw_reference": record.raw_reference,
    }


__all__ = ["IntegrationControlError", "IntegrationControlService"]
