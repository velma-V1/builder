"""PH-6 unit — independence-before-parallel admission gate (``01D §2/§3.4``)."""

from __future__ import annotations

import pytest

from factory.workstream import (
    AdmissionController,
    AdmissionOutcome,
    IndependenceKind,
    WorkstreamContract,
)
from factory.workstream.admission import _path_prefix_overlap


def test_path_prefix_overlap_all_arcs() -> None:
    assert _path_prefix_overlap("src/a", "src/a")  # equal
    assert _path_prefix_overlap("", "src/a")  # left root
    assert _path_prefix_overlap("src/a", "")  # right root
    assert _path_prefix_overlap("src/a", "src/a/b")  # containment
    assert not _path_prefix_overlap("src/a", "src/b")  # disjoint, both non-empty

pytestmark = pytest.mark.security

_BASE = "baseline-0"


def _ws(
    ws_id: str,
    scope: str,
    *,
    contracts: tuple[str, ...] = (),
    deps: tuple[str, ...] = (),
    baseline: str = _BASE,
) -> WorkstreamContract:
    return WorkstreamContract(
        workstream_id=ws_id,
        owner="o",
        scope_paths=(scope,),
        inputs=(),
        outputs=(),
        dependencies=deps,
        owned_contracts=contracts,
        completion_gate="g",
        baseline_commit=baseline,
    )


def test_independent_workstream_is_admitted() -> None:
    ctrl = AdmissionController()
    result = ctrl.admit(_ws("W2", "src/b/**"), [_ws("W1", "src/a/**")], _BASE, frozenset())
    assert result.admitted


def test_cap_is_enforced() -> None:
    ctrl = AdmissionController(max_active=3)
    active = [_ws("W1", "src/a/**"), _ws("W2", "src/b/**"), _ws("W3", "src/c/**")]
    result = ctrl.admit(_ws("W4", "src/d/**"), active, _BASE, frozenset())
    assert result.outcome is AdmissionOutcome.DENIED_CAP
    assert ctrl.max_active == 3


def test_scope_overlap_denies_independence() -> None:
    ctrl = AdmissionController()
    result = ctrl.admit(_ws("W2", "src/a/sub/**"), [_ws("W1", "src/a/**")], _BASE, frozenset())
    assert result.outcome is AdmissionOutcome.DENIED_NOT_INDEPENDENT
    assert any(f.kind is IndependenceKind.SCOPE_OVERLAP for f in result.findings)


def test_root_scope_overlaps_everything() -> None:
    ctrl = AdmissionController()
    # A "**" scope has an empty static prefix and must overlap any other scope, in either position.
    candidate_root = ctrl.admit(_ws("W2", "**"), [_ws("W1", "src/a/**")], _BASE, frozenset())
    assert any(f.kind is IndependenceKind.SCOPE_OVERLAP for f in candidate_root.findings)
    active_root = ctrl.admit(_ws("W2", "src/a/**"), [_ws("W1", "**")], _BASE, frozenset())
    assert any(f.kind is IndependenceKind.SCOPE_OVERLAP for f in active_root.findings)


def test_shared_contract_denies_independence() -> None:
    ctrl = AdmissionController()
    a = _ws("W1", "src/a/**", contracts=("CTR-X",))
    b = _ws("W2", "src/b/**", contracts=("CTR-X",))
    result = ctrl.admit(b, [a], _BASE, frozenset())
    assert any(f.kind is IndependenceKind.SHARED_CONTRACT for f in result.findings)


def test_baseline_mismatch_is_unstable() -> None:
    ctrl = AdmissionController()
    result = ctrl.admit(_ws("W2", "src/b/**", baseline="other"), [], _BASE, frozenset())
    assert result.outcome is AdmissionOutcome.DENIED_UNSTABLE
    assert any(f.kind is IndependenceKind.BASELINE_MISMATCH for f in result.findings)


def test_unresolved_dependency_is_unstable() -> None:
    ctrl = AdmissionController()
    dependent = _ws("W2", "src/b/**", deps=("W1",))
    denied = ctrl.admit(dependent, [], _BASE, frozenset())
    assert denied.outcome is AdmissionOutcome.DENIED_UNSTABLE
    admitted = ctrl.admit(dependent, [], _BASE, frozenset({"W1"}))  # dependency now complete
    assert admitted.admitted
