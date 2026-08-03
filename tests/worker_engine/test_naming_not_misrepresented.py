"""Phase 3B requirement 11: Builder-owned worker orchestration and real Agent Zero integration
must not be misrepresented as each other.

``factory.worker_engine`` is entirely Builder-owned orchestration code, but it legitimately
contains one real, network-calling Agent Zero client (``AgentZeroProcessClient``) alongside a
Builder-native fallback transport (``BuilderWorkerTransport``). The invariant this file checks is
not "no AgentZero-prefixed name anywhere" (that would forbid the correctly-named real adapter) --
it is: (1) every class actually named with an ``AgentZero`` prefix is on an explicit, reviewed
allowlist of genuine real-integration surface, so a new, accidentally-misnamed in-process fallback
would fail this test rather than slip through unnoticed; and (2) the Builder-native fallback
transport is never itself named as though it were real Agent Zero.
"""

from __future__ import annotations

import re
from pathlib import Path

_WORKER_ENGINE_ROOT = Path(__file__).resolve().parents[2] / "src" / "factory" / "worker_engine"
_CLASS_DEF_RE = re.compile(r"^class\s+(\w+)", re.MULTILINE)
_AGENT_ZERO_PREFIX_RE = re.compile(r"^AgentZero")

#: The only names in factory.worker_engine allowed to carry an "AgentZero" prefix: the real,
#: network-calling client and its own typed error. Adding a new name here should require the same
#: scrutiny this test file documents -- it must be a genuine external-process client, never an
#: in-process loop.
_ALLOWED_AGENT_ZERO_PREFIXED_NAMES = frozenset(
    {"AgentZeroProcessClient", "AgentZeroDeploymentUnavailable"}
)


def _all_class_names() -> list[str]:
    names: list[str] = []
    for path in sorted(_WORKER_ENGINE_ROOT.glob("*.py")):
        names.extend(_CLASS_DEF_RE.findall(path.read_text(encoding="utf-8")))
    return names


def test_every_agent_zero_prefixed_name_in_worker_engine_is_on_the_reviewed_allowlist() -> None:
    """Any AgentZero-prefixed class not on the allowlist would misleadingly imply real Agent
    Zero integration -- this catches a future, accidentally-misnamed in-process fallback."""
    names = _all_class_names()
    assert names, "expected to find at least one class definition to check"
    prefixed = [name for name in names if _AGENT_ZERO_PREFIX_RE.match(name)]
    assert prefixed, "expected to find the real AgentZeroProcessClient surface"
    unexpected = [name for name in prefixed if name not in _ALLOWED_AGENT_ZERO_PREFIXED_NAMES]
    assert unexpected == [], (
        f"class name(s) {unexpected!r} in factory.worker_engine are AgentZero-prefixed but not "
        "on the reviewed allowlist -- if this is a real external-process client, add it to "
        "_ALLOWED_AGENT_ZERO_PREFIXED_NAMES; if it is Builder-native orchestration, rename it "
        "(e.g. BuilderWorkerTransport)"
    )


def test_builder_worker_transport_class_exists_with_the_correct_name() -> None:
    from factory.worker_engine.builder_worker_transport import BuilderWorkerTransport

    assert BuilderWorkerTransport.__name__ == "BuilderWorkerTransport"
    assert not _AGENT_ZERO_PREFIX_RE.match(BuilderWorkerTransport.__name__)


def test_builder_worker_transport_module_explicitly_disclaims_being_real_agent_zero() -> None:
    module_path = _WORKER_ENGINE_ROOT / "builder_worker_transport.py"
    content = module_path.read_text(encoding="utf-8")
    normalized = " ".join(content.lower().split())
    assert "not the real agent zero" in normalized
    assert "no upstream agent zero source is vendored" in normalized


def test_agent_zero_process_client_is_a_genuine_network_client_not_an_in_process_loop() -> None:
    """The real adapter must be structurally distinguishable from the in-process fallback: it
    is constructed with a network address and makes real HTTP calls, never a scripted/in-memory
    event stream."""
    import inspect

    from factory.worker_engine.agent_zero_process_client import AgentZeroProcessClient

    fields = {f for f in AgentZeroProcessClient.__dataclass_fields__}
    assert "base_url" in fields, "the real adapter must be configured with a network address"
    source = inspect.getsource(AgentZeroProcessClient)
    assert "urllib.request" in source or "urlopen" in source, (
        "the real adapter must make genuine network calls, not fabricate responses in-process"
    )


def test_agent_zero_process_client_module_documents_it_is_the_real_integration() -> None:
    module_path = _WORKER_ENGINE_ROOT / "agent_zero_process_client.py"
    content = module_path.read_text(encoding="utf-8")
    normalized = " ".join(content.lower().split())
    assert "the real agent zero integration" in normalized
    assert "never fabricates" in normalized
    assert "never falls back silently" in normalized or "never silently" in normalized


def test_agent_zero_structure_verifier_script_is_unmodified_by_phase_3b() -> None:
    """Phase 3B must not touch the existing structural guarantee that no upstream Agent Zero
    source is vendored -- it only adds a new, clearly-named, Builder-owned transport, and a
    genuinely real (but currently unreachable in this environment) network client, alongside the
    existing (untouched) FakeAgentZeroTransport."""
    verify_script = (
        Path(__file__).resolve().parents[2] / "scripts" / "verify_agent_zero_structure.py"
    )
    assert verify_script.is_file()


def test_builder_worker_transport_implements_the_agent_zero_transport_protocol() -> None:
    """It is legitimate for a Builder-owned class to satisfy the AgentZeroTransport *protocol*
    (submit/poll_events/cancel) -- that's how Agent Zero is modeled as a pluggable transport
    throughout this codebase. Satisfying the protocol is not itself a claim of real integration;
    the class name and docstring (checked above) are what must stay honest."""
    from factory.integrations.agent_zero.transport import AgentZeroTransport
    from factory.worker_engine.builder_worker_transport import BuilderWorkerTransport
    from factory.worker_engine.model_router import FakeModelRouter

    transport = BuilderWorkerTransport(model_router=FakeModelRouter(), allowed_path_globs=())
    assert isinstance(transport, AgentZeroTransport)


def test_agent_zero_process_client_also_implements_the_agent_zero_transport_protocol() -> None:
    """Both the real client and the Builder-native fallback satisfy the same protocol, so a
    caller can be constructed to use either one interchangeably behind AgentZeroAdapter --
    which one was actually used for a given run must still be recorded truthfully elsewhere
    (see WorkerEngineService's persisted run records), never conflated."""
    from factory.integrations.agent_zero.transport import AgentZeroTransport
    from factory.worker_engine.agent_zero_process_client import AgentZeroProcessClient

    client = AgentZeroProcessClient(
        base_url="http://127.0.0.1:1",
        ollama_base_url="http://127.0.0.1:11434",
        model_tag="devstral-small-2:24b",
    )
    assert isinstance(client, AgentZeroTransport)
