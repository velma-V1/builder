"""PH-6 unit — conflict detection beyond files + immutable baseline (``01D §3.3-3.4``)."""

from __future__ import annotations

import pytest

from factory.workstream import WorkstreamError
from factory.workstream.conflict import (
    BaselineTracker,
    ChangeManifest,
    ConflictDetector,
    ConflictKind,
)

pytestmark = pytest.mark.security


def test_no_conflict_between_disjoint_workstreams() -> None:
    detector = ConflictDetector()
    a = ChangeManifest("W1", files=frozenset({"src/a.py"}), modules=frozenset({"a"}))
    b = ChangeManifest("W2", files=frozenset({"src/b.py"}), modules=frozenset({"b"}))
    assert detector.detect([a, b]) == ()
    assert detector.is_independent([a, b])


def test_set_dimension_conflicts_detected() -> None:
    detector = ConflictDetector()
    a = ChangeManifest(
        "W1",
        files=frozenset({"s.py"}),
        symbols=frozenset({"foo"}),
        schemas=frozenset({"S"}),
        apis=frozenset({"A"}),
        generated=frozenset({"g"}),
        logical_invariants=frozenset({"inv"}),
    )
    b = ChangeManifest(
        "W2",
        files=frozenset({"s.py"}),
        symbols=frozenset({"foo"}),
        schemas=frozenset({"S"}),
        apis=frozenset({"A"}),
        generated=frozenset({"g"}),
        logical_invariants=frozenset({"inv"}),
    )
    kinds = {c.kind for c in detector.detect([a, b])}
    assert {
        ConflictKind.FILE,
        ConflictKind.SYMBOL,
        ConflictKind.SCHEMA,
        ConflictKind.API,
        ConflictKind.GENERATED,
        ConflictKind.LOGICAL,
    } <= kinds


def test_migration_id_and_order_conflicts() -> None:
    detector = ConflictDetector()
    dup_id = detector.detect(
        [
            ChangeManifest("W1", migrations=(("0001", 1),)),
            ChangeManifest("W2", migrations=(("0001", 2),)),
        ]
    )
    assert any(c.kind is ConflictKind.MIGRATION for c in dup_id)
    order = detector.detect(
        [
            ChangeManifest("W1", migrations=(("0001", 5),)),
            ChangeManifest("W2", migrations=(("0002", 5),)),
        ]
    )
    assert any(c.kind is ConflictKind.MIGRATION for c in order)


def test_config_and_dependency_version_conflicts() -> None:
    detector = ConflictDetector()
    cfg = detector.detect(
        [
            ChangeManifest("W1", config=(("KEY", "a"),)),
            ChangeManifest("W2", config=(("KEY", "b"),)),
        ]
    )
    assert any(c.kind is ConflictKind.CONFIG for c in cfg)
    # Same value is not a conflict.
    assert (
        detector.detect(
            [
                ChangeManifest("W1", config=(("KEY", "same"),)),
                ChangeManifest("W2", config=(("KEY", "same"),)),
            ]
        )
        == ()
    )
    dep = detector.detect(
        [
            ChangeManifest("W1", dependencies=(("lib", "1.0"),)),
            ChangeManifest("W2", dependencies=(("lib", "2.0"),)),
        ]
    )
    assert any(c.kind is ConflictKind.DEPENDENCY for c in dep)


def test_baseline_is_immutable_and_drift_detected() -> None:
    tracker = BaselineTracker()
    tracker.record("stage-1", "commit-a")
    assert tracker.baseline("stage-1") is not None
    assert tracker.record("stage-1", "commit-a").commit == "commit-a"  # idempotent
    with pytest.raises(WorkstreamError) as exc:
        tracker.record("stage-1", "commit-b")  # silent change denied
    assert exc.value.code == "BASELINE_IMMUTABLE"
    assert tracker.has_drifted("stage-1", "commit-b")
    assert not tracker.has_drifted("stage-1", "commit-a")
    assert not tracker.has_drifted("missing", "x")
    tracker.approved_update("stage-1", "commit-b")  # only legal way to move a baseline
    assert tracker.baseline("stage-1").commit == "commit-b"  # type: ignore[union-attr]
