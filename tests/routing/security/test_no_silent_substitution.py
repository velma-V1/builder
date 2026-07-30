"""PH-4 security — no silent substitution, disclosed fallback, bounded worker authority."""

from __future__ import annotations

from pathlib import Path

import pytest

from factory.models.ollama_adapter import FakeOllamaAdapter
from factory.routing import (
    ExecutionStatus,
    ModelRouter,
    RouteRequest,
    RuntimeStatus,
)
from factory.routing.errors import RoutingError
from factory.workers.aider_adapter import FakeAiderWorker, ProposedEdit

pytestmark = pytest.mark.security


def test_runtime_unavailable_never_silently_reroutes(
    router: ModelRouter, ollama: FakeOllamaAdapter, dispatch_request: RouteRequest
) -> None:
    ollama.set_status(RuntimeStatus.UNAVAILABLE)
    outcome = router.execute(dispatch_request)
    # The record shows the *selected* route failing explicitly — not a swap to another model.
    assert outcome.record is not None
    assert outcome.record.route_key == "OLLAMA:qwen3:8b"
    assert outcome.record.status is ExecutionStatus.RUNTIME_UNAVAILABLE
    assert router.snapshot().records[-1].status is ExecutionStatus.RUNTIME_UNAVAILABLE


def test_fallback_requires_an_approved_substitute(
    router: ModelRouter, ollama: FakeOllamaAdapter, dispatch_request: RouteRequest
) -> None:
    ollama.set_status(RuntimeStatus.UNAVAILABLE)
    failed = router.execute(dispatch_request).record
    assert failed is not None
    with pytest.raises(RoutingError) as exc:
        router.fallback(failed.record_id, dispatch_request, substitute_route_key="OLLAMA:ghost")
    assert exc.value.code == "FALLBACK_UNAPPROVED"


def test_fallback_rejects_privacy_violating_substitute(
    router: ModelRouter, ollama: FakeOllamaAdapter, dispatch_request: RouteRequest
) -> None:
    ollama.set_status(RuntimeStatus.UNAVAILABLE)
    failed = router.execute(dispatch_request).record
    assert failed is not None
    with pytest.raises(RoutingError) as exc:
        router.fallback(
            failed.record_id, dispatch_request, substitute_route_key="GROQ:qwen/qwen3.6-27b"
        )
    assert exc.value.code == "FALLBACK_PRIVACY"


def test_fallback_on_a_healthy_record_is_refused(
    router: ModelRouter, dispatch_request: RouteRequest
) -> None:
    succeeded = router.execute(dispatch_request).record
    assert succeeded is not None and succeeded.status is ExecutionStatus.SUCCEEDED
    with pytest.raises(RoutingError) as exc:
        router.fallback(
            succeeded.record_id, dispatch_request, substitute_route_key="OLLAMA:qwen3:14b"
        )
    assert exc.value.code == "FALLBACK_NOT_FAILED"


def test_worker_cannot_expand_scope(aider: FakeAiderWorker, tmp_path: Path) -> None:
    edits = [ProposedEdit("outside/thing.py", 5)]
    packet = aider.submit_task("t1", tmp_path, owned_paths=["src/**"], requested_edits=edits)
    assert packet.accepted_edits == ()  # scope expansion denied, not silently applied
