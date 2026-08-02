from __future__ import annotations

import errno

import pytest

from tests.worker_engine.support import loopback_unavailable_reason


class _DeniedSocket:
    def __enter__(self) -> _DeniedSocket:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def bind(self, address: tuple[str, int]) -> None:
        raise PermissionError(errno.EPERM, "Operation not permitted")


def test_loopback_probe_classifies_permission_denial(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("tests.worker_engine.support.socket.socket", lambda *args: _DeniedSocket())
    reason = loopback_unavailable_reason()
    assert reason is not None
    assert "loopback socket creation denied" in reason
