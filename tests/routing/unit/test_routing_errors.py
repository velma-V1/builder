"""PH-4 unit — RoutingError code/message surface."""

from __future__ import annotations

from factory.routing.errors import RoutingError


def test_routing_error_carries_code_and_message() -> None:
    err = RoutingError("MODEL_EXCLUDED", "glm not allowed")
    assert err.code == "MODEL_EXCLUDED"
    assert err.message == "glm not allowed"
    assert str(err) == "MODEL_EXCLUDED: glm not allowed"
    assert repr(err) == "RoutingError(code='MODEL_EXCLUDED', message='glm not allowed')"
