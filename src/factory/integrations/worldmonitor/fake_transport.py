"""Deterministic fixtures for WorldMonitor tests (REST via the provider fake transport + MCP fake).

No real endpoints, no real credentials. REST responses reuse the provider
:class:`~factory.providers.transport.FakeHttpTransport`; MCP uses :class:`FakeMcpTransport`.
"""

from __future__ import annotations

import json
from collections.abc import Mapping

from factory.integrations.worldmonitor.mcp_client import FakeMcpTransport, McpServerCard
from factory.providers.transport import (
    FakeExchange,
    FakeHttpTransport,
    HttpRequest,
    HttpResponse,
)


def rest_response(payload: Mapping[str, object], *, status: int = 200) -> HttpResponse:
    return HttpResponse(status, {"x-request-id": "wm-1"}, json.dumps(payload).encode("utf-8"))


def rest_transport_for(path_substr: str, response: HttpResponse) -> FakeHttpTransport:
    def _m(req: HttpRequest) -> bool:
        return path_substr in req.url
    return FakeHttpTransport((FakeExchange(_m, response),))


def records_payload(*records: Mapping[str, object]) -> dict[str, object]:
    return {"records": list(records)}


def sample_record(**over: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "u-1", "source_name": "ExampleWire",
        "source_url": "https://feeds.worldmonitor.example/item/1",
        "geography": "XX", "summary": "An external claim about a regional event.",
        "observed_at": 1000,
    }
    base.update(over)
    return base


def fake_mcp(*tools: str) -> FakeMcpTransport:
    return FakeMcpTransport(McpServerCard(
        name="worldmonitor-mcp", version="0.1", tools=tools,
        scopes=("read:intel",), capability_flags=("read_only",),
        oauth_metadata_url="https://mcp.worldmonitor.example/.well-known/oauth",
    ))
