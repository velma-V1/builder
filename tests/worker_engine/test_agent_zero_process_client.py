"""Real HTTP-mechanics tests for ``AgentZeroProcessClient`` -- the real Agent Zero integration,
separately identifiable from ``BuilderWorkerTransport``.

Runs a genuine (if minimal) HTTP server in-process implementing the client's own documented
contract, so these tests exercise real socket I/O end to end rather than mocking
``urllib.request``. This stands in for "a real Agent Zero deployment" for determinism -- it does
not claim to be, or replace, an actual Agent Zero installation.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Callable, Mapping
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

import pytest

from factory.integrations.agent_zero.models import (
    AgentZeroEventType,
    ResourceEnvelope,
    WorkOrder,
)
from factory.integrations.agent_zero.task_mapping import build_work_order
from factory.integrations.agent_zero.transport import TransportFailure, TransportTimeout
from factory.worker_engine.agent_zero_process_client import (
    AgentZeroDeploymentUnavailable,
    AgentZeroProcessClient,
)

_RESOURCES = ResourceEnvelope(cpu_millis=1000, memory_mb=512, disk_mb=512, wall_clock_s=60)


def _work_order() -> WorkOrder:
    return build_work_order(
        work_order_id="wo-1", task_id="t-1", workstream_id="ws-1",
        branch_ref="factory/worker/t-1", instructions="do the thing",
        granted_tools=frozenset({"read_file"}), allowed_path_globs=("**",),
        resources=_RESOURCES, timeout_s=60,
    )


class _FakeAgentZeroServer:
    """A minimal, real HTTP server implementing AgentZeroProcessClient's documented contract."""

    def __init__(self, handler_factory: Callable[[], type[BaseHTTPRequestHandler]]) -> None:
        self._httpd = HTTPServer(("127.0.0.1", 0), handler_factory())
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)

    def __enter__(self) -> str:
        self._thread.start()
        port = self._httpd.server_address[1]
        return f"http://127.0.0.1:{port}"

    def __exit__(self, *exc: object) -> None:
        self._httpd.shutdown()
        self._thread.join(timeout=5)
        self._httpd.server_close()


def _make_handler(responses: Mapping[str, object]) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args: object) -> None:
            pass

        def _respond(self, key: str) -> None:
            body = json.dumps(responses[key]).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path == "/health":
                self._respond("health")
            elif path.endswith("/events"):
                self._respond("events")
            else:
                self.send_response(404)
                self.end_headers()

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", 0))
            self.rfile.read(length)
            if self.path == "/work-orders":
                self._respond("submit")
            elif self.path.endswith("/cancel"):
                self._respond("cancel")
            else:
                self.send_response(404)
                self.end_headers()

    return Handler


def test_probe_raises_when_no_deployment_is_listening() -> None:
    """The expected, correctly-reported outcome when Agent Zero is not installed/running."""
    client = AgentZeroProcessClient(
        base_url="http://127.0.0.1:1",  # nothing listens on a reserved low port in a test env
        ollama_base_url="http://127.0.0.1:11434",
        model_tag="devstral-small-2:24b",
        timeout_s=1,
    )
    with pytest.raises(AgentZeroDeploymentUnavailable):
        client.probe()


def test_submit_and_cancel_never_fabricate_a_response_and_never_silently_substitute() -> None:
    """When nothing is reachable, submit/cancel raise the real transport failure -- never a
    fabricated success, and never a silent fallback to a different transport."""
    client = AgentZeroProcessClient(
        base_url="http://127.0.0.1:1",
        ollama_base_url="http://127.0.0.1:11434",
        model_tag="devstral-small-2:24b",
        timeout_s=1,
    )
    with pytest.raises(TransportFailure):
        client.submit(_work_order())
    with pytest.raises(TransportFailure):
        client.poll_events("run-1", after_sequence=-1)
    with pytest.raises(TransportFailure):
        client.cancel("run-1")


def test_probe_succeeds_against_a_real_reachable_health_endpoint() -> None:
    responses = {"health": {"status": "ok"}}
    with _FakeAgentZeroServer(lambda: _make_handler(responses)) as base_url:
        client = AgentZeroProcessClient(
            base_url=base_url, ollama_base_url="http://127.0.0.1:11434",
            model_tag="devstral-small-2:24b", timeout_s=5,
        )
        client.probe()  # must not raise


def test_submit_parses_a_real_http_response_into_a_run_id() -> None:
    responses = {"submit": {"run_id": "az-run-123"}}
    with _FakeAgentZeroServer(lambda: _make_handler(responses)) as base_url:
        client = AgentZeroProcessClient(
            base_url=base_url, ollama_base_url="http://127.0.0.1:11434",
            model_tag="devstral-small-2:24b", timeout_s=5,
        )
        run_id = client.submit(_work_order())
        assert run_id == "az-run-123"


def test_submit_rejects_a_malformed_response() -> None:
    responses = {"submit": {"unexpected": "shape"}}
    with _FakeAgentZeroServer(lambda: _make_handler(responses)) as base_url:
        client = AgentZeroProcessClient(
            base_url=base_url, ollama_base_url="http://127.0.0.1:11434",
            model_tag="devstral-small-2:24b", timeout_s=5,
        )
        with pytest.raises(TransportFailure):
            client.submit(_work_order())


def test_poll_events_parses_real_events_and_maps_unrecognized_types_to_log() -> None:
    responses = {
        "events": {
            "events": [
                {"sequence": 0, "event_type": "STARTED", "occurred_at": 1000, "payload": {}},
                {
                    "sequence": 1, "event_type": "SOME_FUTURE_TYPE", "occurred_at": 1001,
                    "payload": {"detail": "unknown"},
                },
            ]
        }
    }
    with _FakeAgentZeroServer(lambda: _make_handler(responses)) as base_url:
        client = AgentZeroProcessClient(
            base_url=base_url, ollama_base_url="http://127.0.0.1:11434",
            model_tag="devstral-small-2:24b", timeout_s=5,
        )
        events = client.poll_events("run-1", after_sequence=-1)
        assert len(events) == 2
        assert events[0].event_type is AgentZeroEventType.STARTED
        assert events[1].event_type is AgentZeroEventType.LOG


def test_poll_events_rejects_a_malformed_event() -> None:
    responses = {"events": {"events": [{"sequence": "not-a-number"}]}}
    with _FakeAgentZeroServer(lambda: _make_handler(responses)) as base_url:
        client = AgentZeroProcessClient(
            base_url=base_url, ollama_base_url="http://127.0.0.1:11434",
            model_tag="devstral-small-2:24b", timeout_s=5,
        )
        with pytest.raises(TransportFailure):
            client.poll_events("run-1", after_sequence=-1)


def test_cancel_parses_a_real_http_response() -> None:
    responses = {"cancel": {"cancelled": True}}
    with _FakeAgentZeroServer(lambda: _make_handler(responses)) as base_url:
        client = AgentZeroProcessClient(
            base_url=base_url, ollama_base_url="http://127.0.0.1:11434",
            model_tag="devstral-small-2:24b", timeout_s=5,
        )
        assert client.cancel("run-1") is True


def test_timeout_is_distinguished_from_unreachable() -> None:
    """A request that connects but never responds within the bound must raise TransportTimeout,
    not TransportFailure -- callers (AgentZeroAdapter) map the two to different error codes."""

    class _HangingHandler(BaseHTTPRequestHandler):
        def log_message(self, *args: object) -> None:
            pass

        def do_GET(self) -> None:
            import time

            time.sleep(3)
            self.send_response(200)
            self.end_headers()

    with _FakeAgentZeroServer(lambda: _HangingHandler) as base_url:
        client = AgentZeroProcessClient(
            base_url=base_url, ollama_base_url="http://127.0.0.1:11434",
            model_tag="devstral-small-2:24b", timeout_s=1,
        )
        with pytest.raises(TransportTimeout):
            client.poll_events("run-1", after_sequence=-1)
