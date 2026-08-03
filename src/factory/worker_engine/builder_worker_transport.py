"""``BuilderWorkerTransport`` -- Builder's own in-process worker loop, driven by a local Ollama
model. It is NOT the real Agent Zero project.

**Naming note (read before using or extending this module):** this class implements the
``factory.integrations.agent_zero.transport.AgentZeroTransport`` *protocol* (submit/poll_events/
cancel) so it can be plugged into the existing ``AgentZeroAdapter`` exactly like
``FakeAgentZeroTransport`` already is -- Agent Zero is modeled throughout this codebase as a
pluggable transport behind that protocol, and satisfying the protocol's shape does not, by
itself, mean this class talks to the real Agent Zero project. It doesn't. No upstream Agent Zero
source is vendored anywhere in this repository (a structural invariant
``scripts/verify_agent_zero_structure.py`` checks), and this module does not change that. A real
transport that actually spawns or communicates with the upstream Agent Zero process through its
own documented protocol would be a genuinely different class (a plausible future name:
``AgentZeroProcessClient``) and does not exist here. Do not describe this class, in code or in
reports, as "the Agent Zero integration" -- it is Builder's own managed worker, calling a real
local Ollama+Devstral model directly through ``ModelRouterPort``.

**The sandbox/workspace is optional, not mandatory (Phase 3B execution-policy correction):**
``workspace_path`` is ``None`` for a ``DIRECT_READ_ONLY`` run -- no file is ever read from or
written to, and the worker performs pure analysis/planning via one model call. When
``workspace_path`` is set (``STAGED_WRITE`` or ``SANDBOXED_EXECUTION``, decided by
``factory.worker_engine.execution_policy`` before this class is ever constructed for a given
run), the worker may propose exactly one full-file replacement inside that path, which the
caller is responsible for treating as neither authoritative nor live-repository content until it
clears verification, approval, and promotion.

**Scope simplification (documented limitation, not hidden):** when writing is permitted, this
transport proposes exactly one full-file replacement per work order, not true multi-file
unified-diff patches. The target file is selected via an explicit ``target: <relative/path>``
line in ``work_order.instructions`` (case-insensitive); if none is present, it defaults to a
per-task scratch file (``task-output/<task_id>.md``), which is always within a sensible allowed
scope. This keeps a first real model-integration honest and testable without requiring the model
to produce a correctly-formatted unified diff across multiple files, which is unreliable to
prompt for reliably. A real diff (via ``difflib``) is still computed server-side from the
before/after content, so evidence carries a genuine, inspectable diff either way.
"""

from __future__ import annotations

import difflib
import re
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from factory.contracts.errors import ContractError
from factory.contracts.validation.paths import PathAuthority
from factory.integrations.agent_zero.models import (
    AgentZeroEvent,
    AgentZeroEventType,
    WorkOrder,
    content_digest,
)
from factory.integrations.agent_zero.policy import AgentZeroCapabilityRequest, ModelRouterPort
from factory.routing.models import Privacy

_TARGET_LINE_RE = re.compile(r"(?im)^\s*target\s*:\s*(\S+)\s*$")


def _default_target_path(task_id: str) -> str:
    return f"task-output/{task_id}.md"


def select_target_path(instructions: str, task_id: str) -> str:
    """Extract an explicit ``target: <path>`` line from ``instructions``, else a safe default."""
    match = _TARGET_LINE_RE.search(instructions)
    if match:
        return match.group(1)
    return _default_target_path(task_id)


def _build_write_prompt(*, instructions: str, target_path: str, current_content: str) -> str:
    return (
        "You are a careful software engineer modifying exactly one file in a small repository.\n\n"
        f"Task:\n{instructions}\n\n"
        f"Target file: {target_path}\n\n"
        "Current content of the target file (empty if it does not exist yet):\n"
        "---BEGIN CURRENT CONTENT---\n"
        f"{current_content}\n"
        "---END CURRENT CONTENT---\n\n"
        "Reply with the COMPLETE new content of the target file after your change, and NOTHING "
        "else -- no explanation, no markdown code fences -- between the exact markers below:\n"
        "---BEGIN NEW CONTENT---\n"
        "<new content here>\n"
        "---END NEW CONTENT---\n"
    )


def _build_read_only_prompt(*, instructions: str) -> str:
    return (
        "You are a careful software engineer performing read-only analysis. You must not "
        "propose any file changes -- only research, inspection, or planning.\n\n"
        f"Task:\n{instructions}\n\n"
        "Reply with your analysis/findings as plain text."
    )


_NEW_CONTENT_RE = re.compile(
    r"---BEGIN NEW CONTENT---\r?\n(.*?)\r?\n---END NEW CONTENT---", re.DOTALL
)


def parse_model_output(raw_output: str) -> str | None:
    """Extract the new file content from between the response markers, or ``None`` if malformed."""
    match = _NEW_CONTENT_RE.search(raw_output)
    if match is None:
        return None
    return match.group(1)


@dataclass(slots=True)
class BuilderWorkerTransport:
    """One-shot, synchronous, in-process transport for a single work order.

    A fresh instance is constructed per run. ``submit`` performs the real work synchronously and
    materializes the full event stream immediately; ``poll_events``/``cancel`` then operate over
    that already-known, in-memory stream -- there is no separate background process to poll.
    """

    model_router: ModelRouterPort
    allowed_path_globs: tuple[str, ...]
    #: ``None`` for DIRECT_READ_ONLY -- no workspace/sandbox/staging path is ever created or
    #: touched for a read-only run. Set only for STAGED_WRITE (a staging temp dir) or
    #: SANDBOXED_EXECUTION (a real git worktree) -- the caller (execution policy) decides which.
    workspace_path: Path | None = None
    clock: Callable[[], int] = field(default=lambda: int(time.time()))
    _events: list[AgentZeroEvent] = field(default_factory=list, init=False)
    _cancelled: bool = field(default=False, init=False)

    def submit(self, work_order: WorkOrder) -> str:
        run_id = f"worker-run-{uuid.uuid4().hex}"
        self._events = list(self._execute(work_order))
        return run_id

    def poll_events(self, run_id: str, *, after_sequence: int) -> tuple[AgentZeroEvent, ...]:
        return tuple(e for e in self._events if e.sequence > after_sequence)

    def cancel(self, run_id: str) -> bool:
        self._cancelled = True
        return True

    def _is_cancelled(self) -> bool:
        """A method call (not a bare attribute read) so type checkers don't narrow this to a
        static ``False`` between checks -- ``cancel()`` may set it from another thread/caller
        between the cooperative checkpoints in ``_execute`` below."""
        return self._cancelled

    def _emit(
        self, work_order_id: str, sequence: int, event_type: AgentZeroEventType, **payload: str
    ) -> AgentZeroEvent:
        return AgentZeroEvent(
            work_order_id=work_order_id,
            sequence=sequence,
            event_type=event_type,
            occurred_at=self.clock(),
            payload=payload,
        )

    def _execute(self, work_order: WorkOrder) -> list[AgentZeroEvent]:
        seq = 0
        events: list[AgentZeroEvent] = [
            self._emit(work_order.work_order_id, seq, AgentZeroEventType.STARTED)
        ]

        if self._is_cancelled():
            seq += 1
            events.append(self._emit(work_order.work_order_id, seq, AgentZeroEventType.CANCELLED))
            return events

        if self.workspace_path is None:
            return self._execute_read_only(work_order, events, seq)
        return self._execute_write(work_order, events, seq, self.workspace_path)

    def _execute_read_only(
        self, work_order: WorkOrder, events: list[AgentZeroEvent], seq: int
    ) -> list[AgentZeroEvent]:
        """DIRECT_READ_ONLY: exactly one model consultation, no file ever read or written."""
        seq += 1
        events.append(self._emit(work_order.work_order_id, seq, AgentZeroEventType.PROGRESS))

        model_result = self.model_router.request(
            AgentZeroCapabilityRequest(
                task_id=work_order.task_id,
                capability="analysis",
                prompt=_build_read_only_prompt(instructions=work_order.instructions),
                privacy=Privacy.LOCAL_ONLY,
            )
        )
        if not model_result.ok:
            seq += 1
            events.append(
                self._emit(
                    work_order.work_order_id,
                    seq,
                    AgentZeroEventType.FAILED,
                    reason=f"model call failed: {model_result.reason}",
                )
            )
            return events

        # A read-only run's work-product is its analysis text -- recorded as a genuine artifact
        # (never a repo patch: DIRECT_READ_ONLY never proposes a file change) so the existing,
        # unmodified AgentZeroResult completeness rule ("a SUCCESS with neither patches nor
        # artifacts is incomplete") is satisfied honestly, not worked around.
        analysis_digest = content_digest(model_result.output)
        seq += 1
        events.append(
            self._emit(
                work_order.work_order_id,
                seq,
                AgentZeroEventType.ARTIFACT_PRODUCED,
                artifact_path=f"analysis/{work_order.task_id}.txt",
                content_digest=analysis_digest,
                media_type="text/plain",
            )
        )
        seq += 1
        events.append(
            self._emit(
                work_order.work_order_id,
                seq,
                AgentZeroEventType.EVIDENCE_ATTACHED,
                kind="analysis",
                detail=model_result.output,
                content_digest=analysis_digest,
            )
        )
        seq += 1
        events.append(self._emit(work_order.work_order_id, seq, AgentZeroEventType.COMPLETED))
        return events

    def _execute_write(
        self,
        work_order: WorkOrder,
        events: list[AgentZeroEvent],
        seq: int,
        workspace_path: Path,
    ) -> list[AgentZeroEvent]:
        """STAGED_WRITE or SANDBOXED_EXECUTION: one full-file replacement inside ``workspace_path``
        (a staging temp dir or a real git worktree -- never the live repository either way)."""
        target_path = select_target_path(work_order.instructions, work_order.task_id)
        authority = PathAuthority(workspace_path)
        authorization = authority.evaluate(
            target_path,
            operation="write",
            allowed=list(work_order.allowed_path_globs),
            forbidden=(),
            read_only=(),
            active_exclusive_paths=(),
        )
        if not authorization.allowed:
            seq += 1
            events.append(
                self._emit(
                    work_order.work_order_id,
                    seq,
                    AgentZeroEventType.FAILED,
                    reason=f"target path denied: {authorization.reason}",
                )
            )
            return events

        absolute_target = workspace_path / authorization.normalized_relative
        current_content = ""
        if absolute_target.is_file():
            current_content = absolute_target.read_text(encoding="utf-8", errors="replace")

        seq += 1
        events.append(self._emit(work_order.work_order_id, seq, AgentZeroEventType.PROGRESS))

        if self._is_cancelled():
            seq += 1
            events.append(self._emit(work_order.work_order_id, seq, AgentZeroEventType.CANCELLED))
            return events

        prompt = _build_write_prompt(
            instructions=work_order.instructions,
            target_path=target_path,
            current_content=current_content,
        )
        model_result = self.model_router.request(
            AgentZeroCapabilityRequest(
                task_id=work_order.task_id,
                capability="code_generation",
                prompt=prompt,
                privacy=Privacy.LOCAL_ONLY,
            )
        )
        if not model_result.ok:
            seq += 1
            events.append(
                self._emit(
                    work_order.work_order_id,
                    seq,
                    AgentZeroEventType.FAILED,
                    reason=f"model call failed: {model_result.reason}",
                )
            )
            return events

        new_content = parse_model_output(model_result.output)
        if new_content is None:
            seq += 1
            events.append(
                self._emit(
                    work_order.work_order_id,
                    seq,
                    AgentZeroEventType.FAILED,
                    reason="model output did not contain the expected content markers",
                )
            )
            return events

        if self._is_cancelled():
            seq += 1
            events.append(self._emit(work_order.work_order_id, seq, AgentZeroEventType.CANCELLED))
            return events

        try:
            authority.revalidate_before_use(authorization)
        except ContractError as exc:
            seq += 1
            events.append(
                self._emit(
                    work_order.work_order_id,
                    seq,
                    AgentZeroEventType.FAILED,
                    reason=f"target path changed after authorization: {exc}",
                )
            )
            return events

        absolute_target.parent.mkdir(parents=True, exist_ok=True)
        absolute_target.write_text(new_content, encoding="utf-8")

        diff_text = "".join(
            difflib.unified_diff(
                current_content.splitlines(keepends=True),
                new_content.splitlines(keepends=True) if new_content else [],
                fromfile=f"a/{target_path}",
                tofile=f"b/{target_path}",
            )
        )
        digest = content_digest(new_content)
        seq += 1
        events.append(
            self._emit(
                work_order.work_order_id,
                seq,
                AgentZeroEventType.PATCH_PROPOSED,
                target_path=target_path,
                diff_text=diff_text,
                content_digest=digest,
            )
        )
        seq += 1
        events.append(
            self._emit(
                work_order.work_order_id,
                seq,
                AgentZeroEventType.EVIDENCE_ATTACHED,
                kind="model_route",
                detail=model_result.provider_route,
                content_digest=model_result.model_fingerprint,
            )
        )
        seq += 1
        events.append(self._emit(work_order.work_order_id, seq, AgentZeroEventType.COMPLETED))
        return events
