"""WorldMonitor MCP client — transport interface + fake only (discovery, no live connection).

Prepares discovery of the server card, OAuth metadata, tool list, scopes, and capability flags. It
performs NO OAuth registration, NO login, NO token acquisition, and NO live MCP connection. Tool
results (later) flow through the same IntelligenceRecord normalization pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class McpServerCard:
    name: str
    version: str
    tools: tuple[str, ...] = ()
    scopes: tuple[str, ...] = ()
    capability_flags: tuple[str, ...] = ()
    oauth_metadata_url: str = ""


@runtime_checkable
class McpTransport(Protocol):
    """Discovery-only MCP transport. A real one connects through the NetworkBroker (built later)."""

    def discover_card(self) -> McpServerCard: ...


class FakeMcpTransport:
    """Deterministic MCP discovery transport (offline). No connection, no OAuth, no token."""

    __slots__ = ("_card",)

    def __init__(self, card: McpServerCard) -> None:
        self._card = card

    def discover_card(self) -> McpServerCard:
        return self._card


def discovered_tools(transport: McpTransport) -> tuple[str, ...]:
    """Read-only tool discovery. Returns tool names only; never invokes them."""
    return transport.discover_card().tools
