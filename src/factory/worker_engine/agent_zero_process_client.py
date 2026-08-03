"""Pinned Agent Zero v2.7 async transport for Builder's untrusted worker boundary."""

from __future__ import annotations

import contextlib
import difflib
import hashlib
import json
import os
import shutil
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from factory.contracts.validation.paths import PathAuthority, PathAuthorityResult
from factory.integrations.agent_zero.models import (
    AgentZeroEvent,
    AgentZeroEventType,
    WorkOrder,
)
from factory.integrations.agent_zero.official_client import AgentZeroPoll
from factory.integrations.agent_zero.transport import TransportFailure, TransportTimeout
from factory.worker_engine.builder_worker_transport import select_target_path


class AgentZeroDeploymentUnavailable(RuntimeError):
    """The pinned Agent Zero runtime is not ready for work."""


_WRITE_TOOL_GRANTS = frozenset({"edit_file", "write_file", "write_patch"})
_MAX_RESULT_FILES = 100
_MAX_RESULT_FILE_BYTES = 2_000_000
_MAX_RESULT_RESPONSE_BYTES = 8_000_000


@dataclass(frozen=True, slots=True)
class _ValidatedFile:
    target: str
    content: str
    decision: PathAuthorityResult
    destination: Path
    before: bytes | None


class OfficialAgentZeroPort(Protocol):
    def probe(self) -> None: ...
    def start_async(self, work_order_json: str) -> str: ...
    def poll(self, context_id: str) -> AgentZeroPoll: ...
    def cancel(self, context_id: str) -> bool: ...


class AgentZeroTransportFactory(Protocol):
    def create(
        self, workspace_path: Path | None, allowed_path_globs: tuple[str, ...]
    ) -> AgentZeroProcessClient: ...


@dataclass(frozen=True, slots=True)
class OfficialAgentZeroTransportFactory:
    official_factory: Callable[[], OfficialAgentZeroPort]
    cancel_requested: Callable[[str], bool] = lambda _task_id: False

    def create(
        self, workspace_path: Path | None, allowed_path_globs: tuple[str, ...]
    ) -> AgentZeroProcessClient:
        return AgentZeroProcessClient(
            self.official_factory(),
            workspace_path,
            allowed_path_globs,
            cancel_requested=self.cancel_requested,
        )


def _work_order_payload(
    work_order: WorkOrder,
    workspace_path: Path | None,
    allowed_path_globs: tuple[str, ...],
) -> str:
    workspace_files: list[dict[str, str]] = []
    if workspace_path is not None:
        target = select_target_path(work_order.instructions, work_order.task_id)
        authority = PathAuthority(workspace_path)
        decision = authority.evaluate(
            target,
            operation="read",
            allowed=list(allowed_path_globs),
            forbidden=(),
            read_only=(),
            active_exclusive_paths=(),
        )
        if not decision.allowed:
            raise TransportFailure(f"Agent Zero input path denied: {decision.reason}")
        source = workspace_path / decision.normalized_relative
        if source.is_file():
            if source.stat().st_size > min(work_order.resources.disk_mb * 1024 * 1024, 2_000_000):
                raise TransportFailure("Agent Zero input file exceeds the bounded context ceiling")
            workspace_files.append(
                {
                    "path": decision.normalized_relative,
                    "content": source.read_text(encoding="utf-8", errors="strict"),
                }
            )
    payload = {
        "contract": "builder.agent-zero.work-order.v1",
        "work_order": {
            "work_order_id": work_order.work_order_id,
            "task_id": work_order.task_id,
            "workstream_id": work_order.workstream_id,
            "branch_ref": work_order.branch_ref,
            "instructions": work_order.instructions,
            "granted_tools": sorted(work_order.granted_tools),
            "allowed_path_globs": list(work_order.allowed_path_globs),
            "timeout_s": work_order.timeout_s,
            "resources": {
                "cpu_millis": work_order.resources.cpu_millis,
                "memory_mb": work_order.resources.memory_mb,
                "disk_mb": work_order.resources.disk_mb,
                "wall_clock_s": work_order.resources.wall_clock_s,
            },
        },
        "response_contract": {
            "response": "plain-text summary",
            "files": [{"path": "authorized relative path", "content": "complete file content"}],
        },
        "workspace_files": workspace_files,
        "authority": (
            "You are an untrusted worker. Return only the response contract as JSON. "
            "You cannot verify, approve, promote, merge, or access Builder authority."
        ),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


@dataclass(slots=True)
class AgentZeroProcessClient:
    """Adapt the pinned upstream async API to Builder's validated event transport."""

    official: OfficialAgentZeroPort
    workspace_path: Path | None
    allowed_path_globs: tuple[str, ...]
    clock: Callable[[], int] = field(default=lambda: int(time.monotonic()))
    sleep: Callable[[float], None] = field(default=time.sleep)
    poll_interval_s: float = 0.25
    cancel_requested: Callable[[str], bool] = lambda _task_id: False
    max_file_count: int = _MAX_RESULT_FILES
    max_file_bytes: int = _MAX_RESULT_FILE_BYTES
    max_response_bytes: int = _MAX_RESULT_RESPONSE_BYTES
    replace: Callable[[Path, Path], None] = os.replace
    _orders: dict[str, WorkOrder] = field(default_factory=dict, init=False)
    _events: dict[str, tuple[AgentZeroEvent, ...]] = field(default_factory=dict, init=False)

    def probe(self) -> None:
        try:
            self.official.probe()
        except Exception as exc:
            raise AgentZeroDeploymentUnavailable(str(exc)) from exc

    def submit(self, work_order: WorkOrder) -> str:
        try:
            context_id = self.official.start_async(
                _work_order_payload(work_order, self.workspace_path, self.allowed_path_globs)
            )
        except Exception as exc:
            raise TransportFailure(f"Agent Zero async submission failed: {exc}") from exc
        if not context_id or context_id in self._orders:
            raise TransportFailure("Agent Zero returned a missing or duplicate context")
        self._orders[context_id] = work_order
        return context_id

    def poll_events(self, run_id: str, *, after_sequence: int) -> tuple[AgentZeroEvent, ...]:
        cached = self._events.get(run_id)
        if cached is None:
            order = self._orders.get(run_id)
            if order is None:
                raise TransportFailure("Agent Zero context is missing")
            cached = self._collect(run_id, order)
            self._events[run_id] = cached
        return tuple(event for event in cached if event.sequence > after_sequence)

    def _collect(self, context_id: str, order: WorkOrder) -> tuple[AgentZeroEvent, ...]:
        started = self.clock()
        while True:
            if self.cancel_requested(order.task_id):
                if not self.cancel(context_id):
                    raise TransportFailure("Agent Zero cancellation was not confirmed")
                now = self.clock()
                return (
                    AgentZeroEvent(order.work_order_id, 0, AgentZeroEventType.STARTED, now),
                    AgentZeroEvent(
                        order.work_order_id,
                        1,
                        AgentZeroEventType.CANCELLED,
                        now,
                        {"reason": "cancelled by Builder"},
                    ),
                )
            if self.clock() - started >= order.timeout_s:
                cleanup = self.cancel(context_id)
                detail = "cancelled" if cleanup else "cancellation was not confirmed"
                raise TransportTimeout(f"Agent Zero context timed out; {detail}")
            try:
                poll = self.official.poll(context_id)
            except Exception as exc:
                raise TransportFailure(f"Agent Zero polling failed: {exc}") from exc
            if poll.context_id != context_id:
                raise TransportFailure("Agent Zero poll returned a different context")
            if poll.running:
                self.sleep(self.poll_interval_s)
                continue
            if poll.response is None:
                raise TransportFailure("Agent Zero completed without a response")
            return self._intake_response(order, poll.response)

    def _intake_response(self, order: WorkOrder, response: str) -> tuple[AgentZeroEvent, ...]:
        if len(response.encode("utf-8")) > self.max_response_bytes:
            raise TransportFailure("Agent Zero result exceeds the response byte ceiling")
        try:
            payload = json.loads(response)
        except ValueError as exc:
            raise TransportFailure("malformed Agent Zero result JSON") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("response"), str):
            raise TransportFailure("malformed Agent Zero result contract")
        files = payload.get("files")
        if not isinstance(files, list):
            raise TransportFailure("malformed Agent Zero files result")
        if len(files) > self.max_file_count:
            raise TransportFailure("Agent Zero result exceeds the file count ceiling")
        events: list[AgentZeroEvent] = [
            AgentZeroEvent(order.work_order_id, 0, AgentZeroEventType.STARTED, self.clock())
        ]
        sequence = 0
        if files and not order.granted_tools.intersection(_WRITE_TOOL_GRANTS):
            raise TransportFailure("Agent Zero file result has no authorized write/edit tool grant")
        if self.workspace_path is None and files:
            raise TransportFailure("read-only Agent Zero work returned file changes")
        authority = PathAuthority(self.workspace_path) if self.workspace_path is not None else None
        validated: list[_ValidatedFile] = []
        targets: set[str] = set()
        for item in files:
            if not isinstance(item, dict):
                raise TransportFailure("malformed Agent Zero file item")
            target, content = item.get("path"), item.get("content")
            if not isinstance(target, str) or not isinstance(content, str) or authority is None:
                raise TransportFailure("malformed or unauthorized Agent Zero file item")
            if len(content.encode("utf-8")) > self.max_file_bytes:
                raise TransportFailure("Agent Zero result exceeds the per-file byte ceiling")
            assert self.workspace_path is not None
            decision = authority.evaluate(
                target,
                operation="write",
                allowed=list(self.allowed_path_globs),
                forbidden=(),
                read_only=(),
                active_exclusive_paths=(),
            )
            if not decision.allowed:
                raise TransportFailure(f"Agent Zero output path denied: {decision.reason}")
            if decision.normalized_relative in targets:
                raise TransportFailure("Agent Zero result contains a duplicate output path")
            targets.add(decision.normalized_relative)
            destination = self.workspace_path / decision.normalized_relative
            original_bytes = destination.read_bytes() if destination.is_file() else None
            validated.append(_ValidatedFile(target, content, decision, destination, original_bytes))
        self._apply_validated_files(authority, validated)
        for item in validated:
            target, content, before_bytes = item.target, item.content, item.before
            before_text = (
                "" if before_bytes is None else before_bytes.decode("utf-8", errors="replace")
            )
            digest = hashlib.sha256(content.encode()).hexdigest()
            diff_text = "".join(
                difflib.unified_diff(
                    before_text.splitlines(keepends=True),
                    content.splitlines(keepends=True),
                    fromfile=f"a/{target}",
                    tofile=f"b/{target}",
                )
            )
            sequence += 1
            events.append(
                AgentZeroEvent(
                    order.work_order_id,
                    sequence,
                    AgentZeroEventType.PATCH_PROPOSED,
                    self.clock(),
                    {"target_path": target, "content_digest": digest, "diff_text": diff_text},
                )
            )
        summary = str(payload["response"])
        digest = hashlib.sha256(summary.encode()).hexdigest()
        if not files:
            sequence += 1
            events.append(
                AgentZeroEvent(
                    order.work_order_id,
                    sequence,
                    AgentZeroEventType.ARTIFACT_PRODUCED,
                    self.clock(),
                    {
                        "artifact_path": f"analysis/{order.task_id}.txt",
                        "content_digest": digest,
                        "media_type": "text/plain",
                    },
                )
            )
        sequence += 1
        events.append(
            AgentZeroEvent(
                order.work_order_id,
                sequence,
                AgentZeroEventType.EVIDENCE_ATTACHED,
                self.clock(),
                {"kind": "worker-response", "detail": summary, "content_digest": digest},
            )
        )
        sequence += 1
        events.append(
            AgentZeroEvent(
                order.work_order_id, sequence, AgentZeroEventType.COMPLETED, self.clock()
            )
        )
        return tuple(events)

    def _apply_validated_files(
        self, authority: PathAuthority | None, files: list[_ValidatedFile]
    ) -> None:
        if not files:
            return
        assert self.workspace_path is not None and authority is not None
        stage = Path(tempfile.mkdtemp(prefix=".builder-agent-zero-stage-", dir=self.workspace_path))
        staged: list[tuple[_ValidatedFile, Path, Path | None]] = []
        applied: list[tuple[_ValidatedFile, Path | None]] = []
        created_directories: list[Path] = []
        try:
            for index, item in enumerate(files):
                staged_path = stage / f"result-{index}"
                staged_path.write_bytes(item.content.encode("utf-8"))
                backup_path = None
                if item.before is not None:
                    backup_path = stage / f"backup-{index}"
                    backup_path.write_bytes(item.before)
                staged.append((item, staged_path, backup_path))
            for item, staged_path, backup_path in staged:
                try:
                    authority.revalidate_before_use(item.decision)
                except Exception as exc:
                    raise TransportFailure(
                        f"Agent Zero output path changed before staged write: {exc}"
                    ) from exc
                missing: list[Path] = []
                parent = item.destination.parent
                while parent != self.workspace_path and not parent.exists():
                    missing.append(parent)
                    parent = parent.parent
                item.destination.parent.mkdir(parents=True, exist_ok=True)
                created_directories.extend(reversed(missing))
                self.replace(staged_path, item.destination)
                applied.append((item, backup_path))
        except Exception as exc:
            rollback_errors: list[str] = []
            for item, backup_path in reversed(applied):
                try:
                    if backup_path is None:
                        item.destination.unlink(missing_ok=True)
                    else:
                        self.replace(backup_path, item.destination)
                except Exception as rollback_exc:
                    rollback_errors.append(str(rollback_exc))
            for directory in reversed(created_directories):
                with contextlib.suppress(OSError):
                    directory.rmdir()
            if rollback_errors:
                detail = "; ".join(rollback_errors)
                raise TransportFailure(
                    f"Agent Zero staged application failed; rollback failed: {detail}"
                ) from exc
            raise TransportFailure(
                "Agent Zero staged application failed and was rolled back"
            ) from exc
        finally:
            shutil.rmtree(stage, ignore_errors=True)

    def cancel(self, run_id: str) -> bool:
        try:
            return self.official.cancel(run_id)
        except Exception as exc:
            raise TransportFailure(f"Agent Zero cancellation failed: {exc}") from exc


__all__ = [
    "AgentZeroDeploymentUnavailable",
    "AgentZeroProcessClient",
    "AgentZeroTransportFactory",
    "OfficialAgentZeroTransportFactory",
]
