"""PH-4 unit — deterministic fake adapters (Ollama runtime + Aider coding worker)."""

from __future__ import annotations

from pathlib import Path

from factory.models.ollama_adapter import FakeOllamaAdapter
from factory.routing import ExecutionStatus, Provider, RuntimeStatus
from factory.routing.adapters import CallRequest, ProviderAdapter
from factory.workers.aider_adapter import FakeAiderWorker, ProposedEdit


def _call(route_key: str, task_id: str = "t1") -> CallRequest:
    return CallRequest(task_id, "s1", route_key, prompt="hi", max_tokens=64, timeout=10)


def test_fake_ollama_satisfies_provider_adapter_protocol() -> None:
    assert isinstance(FakeOllamaAdapter(), ProviderAdapter)
    assert isinstance(FakeAiderWorker(), ProviderAdapter)


def test_ollama_probe_reports_installed_models() -> None:
    adapter = FakeOllamaAdapter()
    report = adapter.probe()
    assert report.provider is Provider.OLLAMA
    assert report.status is RuntimeStatus.AVAILABLE
    assert "qwen3:8b" in report.exact_models
    assert adapter.supports("qwen3:8b")
    assert not adapter.supports("qwen3:70b")


def test_ollama_probe_when_down() -> None:
    adapter = FakeOllamaAdapter(status=RuntimeStatus.UNAVAILABLE)
    assert adapter.probe().status is RuntimeStatus.UNAVAILABLE
    assert not adapter.supports("qwen3:8b")


def test_ollama_call_success_has_complete_fingerprint() -> None:
    result = FakeOllamaAdapter().call(_call("OLLAMA:qwen3:8b"))
    assert result.ok
    assert result.fingerprint is not None
    assert result.fingerprint.artifact_digest
    assert result.tokens > 0


def test_ollama_call_runtime_down_is_explicit_result() -> None:
    result = FakeOllamaAdapter(status=RuntimeStatus.UNAVAILABLE).call(_call("OLLAMA:qwen3:8b"))
    assert result.status is ExecutionStatus.RUNTIME_UNAVAILABLE
    assert not result.ok


def test_ollama_call_missing_model_is_explicit_result() -> None:
    result = FakeOllamaAdapter(installed_models=("qwen3:14b",)).call(_call("OLLAMA:qwen3:8b"))
    assert result.status is ExecutionStatus.RUNTIME_UNAVAILABLE
    assert result.error_code == "MODEL_MISSING"


def test_ollama_forced_timeout_and_malformed_behaviors() -> None:
    timed = FakeOllamaAdapter(behaviors={"qwen3:8b": ExecutionStatus.TIMED_OUT})
    assert timed.call(_call("OLLAMA:qwen3:8b")).status is ExecutionStatus.TIMED_OUT
    malformed = FakeOllamaAdapter(behaviors={"qwen3:8b": ExecutionStatus.FAILED})
    r = malformed.call(_call("OLLAMA:qwen3:8b"))
    assert r.status is ExecutionStatus.FAILED
    assert r.error_code == "MALFORMED_OUTPUT"


def test_ollama_cancellation() -> None:
    adapter = FakeOllamaAdapter()
    assert adapter.cancel("t1") is True
    assert adapter.call(_call("OLLAMA:qwen3:8b", task_id="t1")).status is ExecutionStatus.CANCELLED


def test_ollama_set_status_toggles_availability() -> None:
    adapter = FakeOllamaAdapter()
    adapter.set_status(RuntimeStatus.UNAVAILABLE)
    assert adapter.provider_name == Provider.OLLAMA.value
    assert adapter.call(_call("OLLAMA:qwen3:8b")).status is ExecutionStatus.RUNTIME_UNAVAILABLE


def test_aider_probe_and_call() -> None:
    aider = FakeAiderWorker()
    assert aider.provider_name == Provider.AIDER.value
    assert aider.probe().status is RuntimeStatus.AVAILABLE
    assert aider.supports("aider")
    assert aider.call(_call("AIDER:aider")).ok


def test_aider_offline() -> None:
    aider = FakeAiderWorker(available=False)
    assert aider.probe().status is RuntimeStatus.UNAVAILABLE
    assert not aider.supports("aider")
    assert aider.call(_call("AIDER:aider")).status is ExecutionStatus.RUNTIME_UNAVAILABLE
    assert aider.cancel("t1") is False


def test_aider_edits_within_owned_paths_only(tmp_path: Path) -> None:
    aider = FakeAiderWorker()
    edits = [ProposedEdit("src/app/main.py", 3), ProposedEdit("src/other/secret.py", 1)]
    packet = aider.submit_task("t1", tmp_path, owned_paths=["src/app/**"], requested_edits=edits)
    accepted = {e.path for e in packet.accepted_edits}
    assert accepted == {"src/app/main.py"}
    assert "src/other/secret.py" in packet.rejected_paths
    # collect_package never certifies its own work.
    assert aider.collect_package(packet).self_certified is False


def test_aider_rejects_path_traversal(tmp_path: Path) -> None:
    aider = FakeAiderWorker()
    edits = [ProposedEdit("../escape.py", 1)]
    packet = aider.submit_task("t1", tmp_path, owned_paths=["src/**"], requested_edits=edits)
    assert packet.accepted_edits == ()
    assert "../escape.py" in packet.rejected_paths
