"""AgentZeroAdapter — the Builder-side managed interface to the Agent Zero worker.

Builder remains the sole authority for task state, repositories, branches, models, tools, network,
secrets, permissions, approvals, verification, promotion, and scheduling. This adapter is the single
seam through which Agent Zero's work is submitted, its untrusted event stream is validated, its
result is mapped, and — before that result may cross into Builder's own evidence intake — its
self-report is checked for a self-certification or self-promotion attempt.

A single work order crashing (transport failure, timeout, malformed/incomplete stream) never
corrupts this adapter's ability to serve any other work order: all per-run state is local to the
call, and the adapter's only cumulative state (:meth:`health`'s failure counter) is an intentional
signal, not shared mutable state that a bad run could poison.
"""

from __future__ import annotations

from collections.abc import Callable

from factory.contracts.validation.paths import PathAuthority, PathAuthorityResult
from factory.integrations.agent_zero.capabilities import CapabilitySet, require_tool
from factory.integrations.agent_zero.errors import AgentZeroError, AgentZeroErrorCode
from factory.integrations.agent_zero.event_validation import validate_event_stream
from factory.integrations.agent_zero.health import check_health
from factory.integrations.agent_zero.models import (
    AgentZeroEvent,
    AgentZeroEventType,
    AgentZeroResult,
    ModuleHealth,
    WorkerOutcome,
    WorkOrder,
)
from factory.integrations.agent_zero.policy import (
    AgentZeroCapabilityRequest,
    AgentZeroModelResult,
    ModelRouterPort,
    assert_no_self_certification,
    assert_no_self_promotion,
    enforce_sandbox_boundary,
    evaluate_output_path,
)
from factory.integrations.agent_zero.result_mapping import map_events_to_result
from factory.integrations.agent_zero.transport import (
    AgentZeroTransport,
    TransportFailure,
    TransportTimeout,
)
from factory.routing.models import Privacy
from factory.sandbox.models import SandboxSpec

_TERMINAL_EVENT_TYPES = frozenset(
    {AgentZeroEventType.COMPLETED, AgentZeroEventType.FAILED, AgentZeroEventType.CANCELLED}
)
_RECOVERABLE_CODES = frozenset(
    {AgentZeroErrorCode.TIMED_OUT, AgentZeroErrorCode.UNAVAILABLE, AgentZeroErrorCode.CANCELLED}
)


class AgentZeroAdapter:
    __slots__ = ("_clock", "_consecutive_failures", "_last_success_at", "_router", "_transport")

    def __init__(
        self,
        *,
        transport: AgentZeroTransport,
        model_router: ModelRouterPort,
        clock: Callable[[], int],
    ) -> None:
        self._transport = transport
        self._router = model_router
        self._clock = clock
        self._consecutive_failures = 0
        self._last_success_at: int | None = None

    def _record_success(self) -> None:
        self._consecutive_failures = 0
        self._last_success_at = self._clock()

    def _record_failure(self) -> None:
        self._consecutive_failures += 1

    def submit(self, work_order: WorkOrder) -> str:
        try:
            run_id = self._transport.submit(work_order)
        except TransportTimeout as exc:
            self._record_failure()
            raise AgentZeroError(AgentZeroErrorCode.TIMED_OUT, str(exc)) from exc
        except TransportFailure as exc:
            self._record_failure()
            raise AgentZeroError(AgentZeroErrorCode.UNAVAILABLE, str(exc)) from exc
        self._record_success()
        return run_id

    def poll(self, run_id: str, *, after_sequence: int) -> tuple[AgentZeroEvent, ...]:
        try:
            events = self._transport.poll_events(run_id, after_sequence=after_sequence)
        except TransportTimeout as exc:
            self._record_failure()
            raise AgentZeroError(AgentZeroErrorCode.TIMED_OUT, str(exc)) from exc
        except TransportFailure as exc:
            self._record_failure()
            raise AgentZeroError(AgentZeroErrorCode.UNAVAILABLE, str(exc)) from exc
        self._record_success()
        return events

    def cancel(self, run_id: str) -> bool:
        return self._transport.cancel(run_id)

    def collect_result(self, run_id: str, work_order: WorkOrder) -> AgentZeroResult:
        """Poll to a terminal event (or a recoverable transport failure), then validate + map.

        A poll failure never propagates raw — it is folded into a typed, incomplete result so one
        bad run can never crash a caller iterating over many work orders.
        """
        collected: list[AgentZeroEvent] = []
        after = -1
        crash_detail = ""
        crashed = False
        while True:
            try:
                batch = self.poll(run_id, after_sequence=after)
            except AgentZeroError as exc:
                if exc.code in _RECOVERABLE_CODES:
                    crashed = True
                    crash_detail = exc.detail
                    break
                raise
            if not batch:
                break
            collected.extend(batch)
            after = max(e.sequence for e in collected)
            if any(e.event_type in _TERMINAL_EVENT_TYPES for e in batch):
                break

        try:
            validated = validate_event_stream(tuple(collected))
        except AgentZeroError as exc:
            # Module failure isolation: a stream-integrity violation from one worker never
            # propagates as an uncaught exception — it becomes a typed, non-authoritative result.
            return AgentZeroResult(
                work_order_id=work_order.work_order_id,
                worker_claimed_outcome=WorkerOutcome.FAILURE,
                reason=f"event stream failed integrity validation: {exc.detail}",
                malformed=True,
                incomplete=True,
            )

        has_terminal = any(e.event_type in _TERMINAL_EVENT_TYPES for e in validated.accepted)
        if crashed and not has_terminal:
            partial = map_events_to_result(work_order.work_order_id, validated.accepted)
            return AgentZeroResult(
                work_order_id=work_order.work_order_id,
                worker_claimed_outcome=WorkerOutcome.CRASHED,
                patches=partial.patches,
                artifacts=partial.artifacts,
                evidence=partial.evidence,
                reason=f"transport failure mid-stream: {crash_detail}",
                malformed=partial.malformed,
                incomplete=True,
            )
        return map_events_to_result(work_order.work_order_id, validated.accepted)

    def intake_result(self, result: AgentZeroResult) -> AgentZeroResult:
        """The single boundary through which a worker's result crosses into Builder's evidence
        intake. A self-certification or self-promotion claim is rejected here, not just documented.
        """
        assert_no_self_certification(result)
        assert_no_self_promotion(result)
        return result

    def authorize_tool_call(self, work_order: WorkOrder, tool_name: str) -> None:
        capabilities = CapabilitySet(work_order.work_order_id, work_order.granted_tools)
        require_tool(capabilities, tool_name)

    def authorize_output_path(
        self, authority: PathAuthority, work_order: WorkOrder, candidate: str
    ) -> PathAuthorityResult:
        return evaluate_output_path(authority, candidate, allowed=work_order.allowed_path_globs)

    def authorize_sandbox(self, spec: SandboxSpec) -> None:
        enforce_sandbox_boundary(spec)

    def health(self) -> ModuleHealth:
        return check_health(
            consecutive_failures=self._consecutive_failures,
            now=self._clock(),
            last_success_at=self._last_success_at,
        )

    def request_model(
        self, task_id: str, capability: str, prompt: str, *, privacy: Privacy = Privacy.LOCAL_ONLY,
    ) -> AgentZeroModelResult:
        """The ONLY way Agent Zero obtains AI: hand a capability request to the Builder router."""
        return self._router.request(
            AgentZeroCapabilityRequest(
                task_id=task_id, capability=capability, prompt=prompt, privacy=privacy,
            )
        )
