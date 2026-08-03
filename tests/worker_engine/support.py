"""Capability probes shared by Worker Engine integration tests."""

from __future__ import annotations

import socket


def loopback_unavailable_reason() -> str | None:
    """Return a skip reason only when creating/binding a loopback socket is proven unavailable."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind(("127.0.0.1", 0))
    except PermissionError as exc:
        return f"loopback socket creation denied by environment: {exc}"
    return None
