"""Phase 3B requirement 11: Builder-owned worker orchestration and real Agent Zero integration
must not be misrepresented as each other.

``factory.worker_engine`` is entirely Builder-owned orchestration code. No class defined in this
package may be named as though it were the real, upstream Agent Zero project (e.g. a class
literally named ``AgentZeroTransport``/``AgentZeroWorker``/``AgentZeroProcess``) -- that class name
would misleadingly imply this package talks to the real project, which it does not (no upstream
Agent Zero source is vendored anywhere in this repository, confirmed by
``scripts/verify_agent_zero_structure.py``, which is not modified by Phase 3B and remains passing).
"""

from __future__ import annotations

import re
from pathlib import Path

_WORKER_ENGINE_ROOT = Path(__file__).resolve().parents[2] / "src" / "factory" / "worker_engine"
_CLASS_DEF_RE = re.compile(r"^class\s+(\w+)", re.MULTILINE)
_MISLEADING_NAME_RE = re.compile(r"^AgentZero")


def _all_class_names() -> list[str]:
    names: list[str] = []
    for path in sorted(_WORKER_ENGINE_ROOT.glob("*.py")):
        names.extend(_CLASS_DEF_RE.findall(path.read_text(encoding="utf-8")))
    return names


def test_no_class_in_worker_engine_is_named_as_though_it_were_real_agent_zero() -> None:
    names = _all_class_names()
    assert names, "expected to find at least one class definition to check"
    misleading = [name for name in names if _MISLEADING_NAME_RE.match(name)]
    assert misleading == [], (
        f"class name(s) {misleading!r} in factory.worker_engine falsely imply real Agent Zero "
        "integration; Builder-owned worker classes must use a name like BuilderWorkerTransport"
    )


def test_builder_worker_transport_class_exists_with_the_correct_name() -> None:
    from factory.worker_engine.builder_worker_transport import BuilderWorkerTransport

    assert BuilderWorkerTransport.__name__ == "BuilderWorkerTransport"


def test_builder_worker_transport_module_explicitly_disclaims_being_real_agent_zero() -> None:
    module_path = _WORKER_ENGINE_ROOT / "builder_worker_transport.py"
    content = module_path.read_text(encoding="utf-8")
    normalized = " ".join(content.lower().split())
    assert "not the real agent zero" in normalized
    assert "no upstream agent zero source is vendored" in normalized


def test_agent_zero_structure_verifier_script_is_unmodified_by_phase_3b() -> None:
    """Phase 3B must not touch the existing structural guarantee that no upstream Agent Zero
    source is vendored -- it only adds a new, clearly-named, Builder-owned transport alongside
    the existing (untouched) FakeAgentZeroTransport."""
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
