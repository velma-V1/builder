"""Stage-3 unit — PH-4/5/6 live-gate acceptance matrices are well-formed."""

from __future__ import annotations

from factory.livegate.acceptance import (
    ALL_MATRICES,
    PH4_MATRIX,
    PH5_MATRIX,
    PH6_MATRIX,
    Phase,
    all_criteria,
)


def test_every_phase_has_criteria() -> None:
    assert len(PH4_MATRIX) == 6
    assert len(PH5_MATRIX) == 6
    assert len(PH6_MATRIX) == 6
    assert len(all_criteria()) == 18


def test_criterion_ids_unique_across_all_phases() -> None:
    ids = [c.criterion_id for c in all_criteria()]
    assert len(ids) == len(set(ids))


def test_every_criterion_is_mandatory_and_has_fake_parity() -> None:
    for c in all_criteria():
        assert c.mandatory, c.criterion_id
        assert c.fake_parity, c.criterion_id
        assert c.statement.strip()


def test_matrices_are_phase_consistent() -> None:
    for phase, matrix in ALL_MATRICES:
        assert all(c.phase is phase for c in matrix)
    assert {p for p, _ in ALL_MATRICES} == {Phase.PH4, Phase.PH5, Phase.PH6}
