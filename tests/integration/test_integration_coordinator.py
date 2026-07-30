"""PH-6 unit — integration coordinator (never edits source, remediation to owning lanes)."""

from __future__ import annotations

import pytest

from factory.integration import (
    COORDINATOR_EDITS_SOURCE,
    IntegrationCoordinator,
    IntegrationError,
    IntegrationVerdict,
    WorkstreamResult,
)
from factory.workstream.conflict import ChangeManifest

pytestmark = pytest.mark.security

_BASE = "baseline-0"


def _result(
    ws: str, *, passed: bool = True, baseline: str = _BASE, files: frozenset[str] = frozenset()
) -> WorkstreamResult:
    return WorkstreamResult(ws, passed, baseline, f"approved-{ws}", ChangeManifest(ws, files=files))


def test_clean_integration_promotes_all() -> None:
    coord = IntegrationCoordinator()
    report = coord.integrate(
        [
            _result("W1", files=frozenset({"a.py"})),
            _result("W2", files=frozenset({"b.py"})),
        ]
    )
    assert report.integrated
    assert report.promoted == ("W1", "W2")


def test_local_gate_failure_blocks() -> None:
    coord = IntegrationCoordinator()
    report = coord.integrate([_result("W1"), _result("W2", passed=False)])
    assert report.verdict is IntegrationVerdict.BLOCKED_LOCAL_GATE
    assert report.promoted == ()


def test_divergent_baseline_blocks() -> None:
    coord = IntegrationCoordinator()
    report = coord.integrate([_result("W1"), _result("W2", baseline="other")])
    assert report.verdict is IntegrationVerdict.BLOCKED_BASELINE


def test_conflicts_block_and_assign_remediation_to_owning_lanes() -> None:
    coord = IntegrationCoordinator()
    report = coord.integrate(
        [
            _result("W1", files=frozenset({"shared.py"})),
            _result("W2", files=frozenset({"shared.py"})),
        ]
    )
    assert report.verdict is IntegrationVerdict.BLOCKED_CONFLICTS
    assert report.conflicts
    assert report.remediation
    # Remediation returns to a named owning lane; the gate never edits source itself.
    assert report.remediation[0].owning_workstream in {"W1", "W2"}
    assert COORDINATOR_EDITS_SOURCE is False


def test_integration_error_repr() -> None:
    err = IntegrationError("X", "y")
    assert "IntegrationError(code='X'" in repr(err)
    assert str(err) == "X: y"
