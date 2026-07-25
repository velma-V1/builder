"""Task 3.3 security — SEC-PH3-01: single-writer confinement (R1, threat T-01).

The authoritative `_OrchestratorStateWriter` must not be reachable through the public
`factory.workers` surface. Workers reach state only via StateIntegration, which is the sole holder
of the writer. This test fails loudly if a future change re-exports the writer from the package.
"""

from __future__ import annotations

import pytest

import factory.workers as workers_pkg
from factory.orchestrator.store.runtime_state import _OrchestratorStateWriter
from factory.workers.state_integration import StateIntegration

pytestmark = pytest.mark.security


def test_sec_ph3_01_writer_not_exported_from_workers_package() -> None:
    assert "_OrchestratorStateWriter" not in workers_pkg.__all__
    assert not hasattr(workers_pkg, "_OrchestratorStateWriter")


def test_sec_ph3_01_state_integration_is_sole_writer_holder() -> None:
    # StateIntegration is the only Worker-Engine type that takes a writer field.
    annotations = StateIntegration.__annotations__
    assert annotations["writer"] == "_OrchestratorStateWriter"
    # the writer type itself is only importable from the orchestrator store, not re-homed here.
    assert _OrchestratorStateWriter.__module__ == "factory.orchestrator.store.runtime_state"
