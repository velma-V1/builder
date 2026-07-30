"""Deterministic fake Ollama runtime adapter (preinstallation stand-in for Task 4.1).

Fully offline and reproducible. It models exactly the behaviours the router and scheduler must
handle before any real Ollama is installed: health/version reporting, exact-model discovery,
successful bounded calls, and every failure mode (runtime down, missing model, timeout, malformed
output, cancellation). The live Task 4.1 adapter under ``src/factory/models/ollama_adapter`` will
present this same :class:`ProviderAdapter` surface against a real daemon — that work is
LIVE_RUNTIME_PENDING.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from factory.routing.adapters.base import CallRequest, CallResult
from factory.routing.models import (
    CapabilityReport,
    ExecutionStatus,
    ModelFingerprint,
    Provider,
    RuntimeStatus,
)


def _fingerprint(model_id: str) -> ModelFingerprint:
    """Build a complete, deterministic fingerprint for a fake local model (``01J §3.1``)."""
    return ModelFingerprint(
        family=model_id.split(":", 1)[0],
        declared_name=model_id,
        artifact_digest=f"sha256-fake-{model_id}",
        quantization="Q4_K_M",
        fmt="gguf",
        ollama_version="0.0.0-fake",
        runtime_version="cpu-fake",
        context_window=8192,
        context_allocation=4096,
        sampling=(("temperature", "0.0"), ("top_p", "1.0")),
        system_prompt_version="sys-v1",
        tool_schema_version="tools-v1",
        adapter_version="ollama-fake-v1",
        routing_policy_version="route-v1",
        gpu_config="none",
    )


class FakeOllamaAdapter:
    """Configurable deterministic Ollama adapter for tests and the preinstallation router."""

    __slots__ = ("_behaviors", "_cancelled", "_installed", "_status", "_version")

    def __init__(
        self,
        installed_models: Sequence[str] = ("qwen3:8b", "qwen3:14b"),
        status: RuntimeStatus = RuntimeStatus.AVAILABLE,
        version: str = "0.0.0-fake",
        behaviors: Mapping[str, ExecutionStatus] | None = None,
    ) -> None:
        self._installed = tuple(installed_models)
        self._status = status
        self._version = version
        # Optional per-model forced outcome (timeout/malformed/etc.) for failure-path tests.
        self._behaviors: dict[str, ExecutionStatus] = dict(behaviors or {})
        self._cancelled: set[str] = set()

    @property
    def provider_name(self) -> str:
        return Provider.OLLAMA.value

    def set_status(self, status: RuntimeStatus) -> None:
        self._status = status

    def probe(self) -> CapabilityReport:
        if self._status is RuntimeStatus.UNAVAILABLE:
            return CapabilityReport(
                Provider.OLLAMA, RuntimeStatus.UNAVAILABLE, (), self._version, "daemon unreachable"
            )
        return CapabilityReport(
            Provider.OLLAMA, self._status, self._installed, self._version, "ok"
        )

    def supports(self, model_id: str) -> bool:
        return self._status is not RuntimeStatus.UNAVAILABLE and model_id in self._installed

    def call(self, request: CallRequest) -> CallResult:
        model_id = request.route_key.split(":", 1)[1]
        if request.task_id in self._cancelled:
            self._cancelled.discard(request.task_id)
            return CallResult(ExecutionStatus.CANCELLED, "", 0, None, "cancelled", "CANCELLED")
        if self._status is RuntimeStatus.UNAVAILABLE:
            return CallResult(
                ExecutionStatus.RUNTIME_UNAVAILABLE, "", 0, None, "runtime down",
                "RUNTIME_UNAVAILABLE",
            )
        if model_id not in self._installed:
            return CallResult(
                ExecutionStatus.RUNTIME_UNAVAILABLE, "", 0, None,
                f"model {model_id} not installed", "MODEL_MISSING",
            )
        forced = self._behaviors.get(model_id)
        if forced is ExecutionStatus.TIMED_OUT:
            return CallResult(ExecutionStatus.TIMED_OUT, "", 0, None, "timed out", "TIMEOUT")
        if forced is ExecutionStatus.FAILED:
            return CallResult(
                ExecutionStatus.FAILED, "malformed{", 0, _fingerprint(model_id),
                "malformed output", "MALFORMED_OUTPUT",
            )
        tokens = min(request.max_tokens, 32)
        return CallResult(
            ExecutionStatus.SUCCEEDED,
            f"[{model_id}] handled task {request.task_id}",
            tokens,
            _fingerprint(model_id),
            "ok",
        )

    def cancel(self, task_id: str) -> bool:
        self._cancelled.add(task_id)
        return True
