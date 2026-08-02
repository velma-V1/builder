"""``AgentZeroProcessClient`` -- the real Agent Zero integration, separately identifiable from
``BuilderWorkerTransport`` (Builder's own deterministic/testable fallback worker).

This is a genuine network client: it makes real HTTP calls to a configured Agent Zero deployment
and never fabricates a response. It fails clearly and immediately
(``AgentZeroDeploymentUnavailable``) when nothing is listening at the configured address -- the
honest, expected outcome in any environment (including this repository's own development/CI
environment) that does not have a real Agent Zero runtime installed and running. This class never
silently falls back to
``BuilderWorkerTransport``; the fallback decision is made explicitly by whatever constructs a
transport for a run (see the Phase 3B final report for how that decision is recorded), and must
never be presented as "Agent Zero" succeeding when it did not.

**Documented interface contract.** No stable, versioned wire-protocol specification for the
upstream Agent Zero project's programmatic API was available to design against in this
environment (no live deployment to introspect, no network access to fetch its documentation).
Rather than guess at undocumented internals and risk silently talking past a real deployment,
this client defines its OWN small, explicit HTTP contract that Builder expects an Agent Zero
deployment to expose, and documents it here in full:

- ``GET  {base_url}/health``                        -> ``200`` iff the runtime is ready.
- ``POST {base_url}/work-orders``                    body: see :func:`_work_order_payload`.
                                                      returns ``{"run_id": "..."}``.
- ``GET  {base_url}/work-orders/{run_id}/events?after={sequence}``
                                                      returns ``{"events": [...]}`` (see
                                                      :func:`_parse_event`).
- ``POST {base_url}/work-orders/{run_id}/cancel``    returns ``{"cancelled": true|false}``.

A real Agent Zero deployment must expose a compatible shim for this contract to work end to end;
that shim is not part of Builder and is not built here (Builder does not vendor or reimplement
the Agent Zero project). If no deployment is configured/reachable, every call fails closed with a
typed error identifying exactly what was unavailable -- this is the expected, correctly-reported
outcome when Agent Zero is not installed.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from factory.integrations.agent_zero.models import AgentZeroEvent, AgentZeroEventType, WorkOrder
from factory.integrations.agent_zero.transport import TransportFailure, TransportTimeout

_DEFAULT_TIMEOUT_S = 30


class AgentZeroDeploymentUnavailable(Exception):
    """No real Agent Zero deployment is reachable at the configured address.

    This is the expected, correctly-reported outcome in an environment (such as this
    repository's own development environment) that has no real Agent Zero runtime installed.
    """


def _event_type_from_wire(value: str) -> AgentZeroEventType:
    try:
        return AgentZeroEventType(value)
    except ValueError:
        # An unrecognized event type from an external process is untrusted input, not a bug --
        # map it to LOG so it is preserved (not silently dropped) without inventing meaning.
        return AgentZeroEventType.LOG


def _parse_event(work_order_id: str, raw: object) -> AgentZeroEvent:
    if not isinstance(raw, dict):
        raise TransportFailure(f"malformed event (not an object): {raw!r}")
    try:
        return AgentZeroEvent(
            work_order_id=work_order_id,
            sequence=int(raw["sequence"]),
            event_type=_event_type_from_wire(str(raw["event_type"])),
            occurred_at=int(raw["occurred_at"]),
            payload={str(k): str(v) for k, v in dict(raw.get("payload", {})).items()},
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise TransportFailure(f"malformed event: {exc}") from exc


def _http_call(request: urllib.request.Request, timeout_s: int, base_url: str) -> object:
    """Shared request execution: distinguishes a bounded timeout (``TransportTimeout``) from
    every other reachability failure (``TransportFailure``), matching the exact split
    ``AgentZeroAdapter`` already maps to ``TIMED_OUT``/``UNAVAILABLE`` for any transport."""
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:  # noqa: S310
            return json.loads(response.read())
    except TimeoutError as exc:
        raise TransportTimeout(f"Agent Zero deployment at {base_url} timed out: {exc}") from exc
    except urllib.error.URLError as exc:
        raise TransportFailure(
            f"could not reach Agent Zero deployment at {base_url}: {exc}"
        ) from exc


def _work_order_payload(
    work_order: WorkOrder, *, ollama_base_url: str, model_tag: str
) -> dict[str, object]:
    """The submission payload sent to a real Agent Zero deployment.

    Includes the configured Ollama connection details so a real deployment can route its own
    model calls to the same local Devstral instance Builder uses -- Builder can pass this
    configuration along, but cannot force an external process's internal model selection; a real
    deployment must itself honor these connection details.
    """
    return {
        "work_order_id": work_order.work_order_id,
        "task_id": work_order.task_id,
        "workstream_id": work_order.workstream_id,
        "instructions": work_order.instructions,
        "granted_tools": sorted(work_order.granted_tools),
        "allowed_path_globs": list(work_order.allowed_path_globs),
        "timeout_s": work_order.timeout_s,
        "model_route_token": work_order.model_route_token,
        "model": {"provider": "ollama", "base_url": ollama_base_url, "tag": model_tag},
    }


@dataclass(frozen=True, slots=True)
class AgentZeroProcessClient:
    """Real ``AgentZeroTransport`` implementation: talks to an actual Agent Zero deployment over
    HTTP, per the documented contract above. Never fabricates events; never falls back silently.
    """

    base_url: str
    ollama_base_url: str
    model_tag: str
    timeout_s: int = _DEFAULT_TIMEOUT_S

    def probe(self) -> None:
        """Raise :class:`AgentZeroDeploymentUnavailable` if no deployment is reachable."""
        request = urllib.request.Request(  # noqa: S310
            f"{self.base_url.rstrip('/')}/health", method="GET"
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_s):  # noqa: S310
                return
        except (urllib.error.URLError, TimeoutError) as exc:
            raise AgentZeroDeploymentUnavailable(
                f"no Agent Zero deployment reachable at {self.base_url}: {exc}"
            ) from exc

    def submit(self, work_order: WorkOrder) -> str:
        payload = _work_order_payload(
            work_order, ollama_base_url=self.ollama_base_url, model_tag=self.model_tag
        )
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(  # noqa: S310
            f"{self.base_url.rstrip('/')}/work-orders",
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        raw = _http_call(request, self.timeout_s, self.base_url)
        try:
            return str(raw["run_id"])  # type: ignore[index]
        except (KeyError, TypeError) as exc:
            raise TransportFailure(f"malformed submit response: {raw!r}") from exc

    def poll_events(self, run_id: str, *, after_sequence: int) -> tuple[AgentZeroEvent, ...]:
        request = urllib.request.Request(  # noqa: S310
            f"{self.base_url.rstrip('/')}/work-orders/{run_id}/events?after={after_sequence}",
            method="GET",
        )
        raw = _http_call(request, self.timeout_s, self.base_url)
        try:
            events_raw = raw["events"]  # type: ignore[index]
        except (KeyError, TypeError) as exc:
            raise TransportFailure(f"malformed events response: {raw!r}") from exc
        return tuple(_parse_event(run_id, item) for item in events_raw)

    def cancel(self, run_id: str) -> bool:
        request = urllib.request.Request(  # noqa: S310
            f"{self.base_url.rstrip('/')}/work-orders/{run_id}/cancel", method="POST"
        )
        raw = _http_call(request, self.timeout_s, self.base_url)
        return bool(raw.get("cancelled", False)) if isinstance(raw, dict) else False
