"""Task 2.1 — exhaustive legal/illegal transition matrix (01L §3.1).

Proves the implementation encodes the authoritative transition table exactly:
every documented transition is legal, and every other (prev, new) pair — including
all same-state no-ops — is illegal. Completeness, not a sample.
"""

from __future__ import annotations

import itertools

import pytest

from factory.orchestrator.models import TERMINAL_STATES, TaskState
from factory.orchestrator.state.transitions import ALLOWED_TRANSITIONS, TransitionPolicy

# Verbatim transcription of the 01L §3.1 legal-transition table (one tuple per arrow-target).
LEGAL: frozenset[tuple[TaskState, TaskState]] = frozenset(
    {
        (TaskState.QUEUED, TaskState.PLANNING),
        (TaskState.PLANNING, TaskState.RUNNING),
        (TaskState.PLANNING, TaskState.AWAITING_APPROVAL),
        (TaskState.PLANNING, TaskState.BLOCKED),
        (TaskState.PLANNING, TaskState.FAILED),
        (TaskState.PLANNING, TaskState.STOPPING),
        (TaskState.RUNNING, TaskState.AWAITING_APPROVAL),
        (TaskState.RUNNING, TaskState.VERIFYING),
        (TaskState.RUNNING, TaskState.BLOCKED),
        (TaskState.RUNNING, TaskState.PAUSED),
        (TaskState.RUNNING, TaskState.FAILED),
        (TaskState.RUNNING, TaskState.QUARANTINED),
        (TaskState.RUNNING, TaskState.STOPPING),
        (TaskState.AWAITING_APPROVAL, TaskState.RUNNING),
        (TaskState.AWAITING_APPROVAL, TaskState.VERIFYING),
        (TaskState.AWAITING_APPROVAL, TaskState.BLOCKED),
        (TaskState.AWAITING_APPROVAL, TaskState.STOPPING),
        (TaskState.VERIFYING, TaskState.COMPLETE),
        (TaskState.VERIFYING, TaskState.RUNNING),
        (TaskState.VERIFYING, TaskState.AWAITING_APPROVAL),
        (TaskState.VERIFYING, TaskState.BLOCKED),
        (TaskState.VERIFYING, TaskState.FAILED),
        (TaskState.VERIFYING, TaskState.QUARANTINED),
        (TaskState.VERIFYING, TaskState.STOPPING),
        (TaskState.PAUSED, TaskState.RUNNING),
        (TaskState.PAUSED, TaskState.BLOCKED),
        (TaskState.PAUSED, TaskState.STOPPING),
        (TaskState.BLOCKED, TaskState.PLANNING),
        (TaskState.BLOCKED, TaskState.RUNNING),
        (TaskState.BLOCKED, TaskState.AWAITING_APPROVAL),
        (TaskState.BLOCKED, TaskState.FAILED),
        (TaskState.BLOCKED, TaskState.STOPPING),
        (TaskState.QUARANTINED, TaskState.BLOCKED),
        (TaskState.QUARANTINED, TaskState.FAILED),
        (TaskState.QUARANTINED, TaskState.STOPPING),
        (TaskState.STOPPING, TaskState.CANCELLED),
        (TaskState.COMPLETE, TaskState.ROLLED_BACK),
        (TaskState.FAILED, TaskState.ROLLED_BACK),
    }
)


@pytest.mark.parametrize("prev,new", sorted(LEGAL, key=str))
def test_every_documented_transition_is_legal(prev: TaskState, new: TaskState) -> None:
    assert TransitionPolicy().is_legal(prev, new)


def test_every_undocumented_transition_is_illegal() -> None:
    policy = TransitionPolicy()
    all_pairs = set(itertools.product(TaskState, TaskState))
    illegal = all_pairs - set(LEGAL) - {(s, s) for s in TaskState}
    for prev, new in sorted(illegal, key=str):
        assert not policy.is_legal(prev, new), f"{prev} -> {new} must be illegal"


def test_same_state_no_op_is_illegal() -> None:
    policy = TransitionPolicy()
    for state in TaskState:
        assert not policy.is_legal(state, state), f"{state} -> {state} (no-op) must be illegal"


def test_allowed_transitions_table_matches_documented_legal_set() -> None:
    # ALLOWED_TRANSITIONS, flattened, must equal LEGAL exactly (nothing added or missing).
    flattened = {(prev, new) for prev, targets in ALLOWED_TRANSITIONS.items() for new in targets}
    assert flattened == set(LEGAL)


def test_terminal_states_are_the_three_documented() -> None:
    assert (
        frozenset({TaskState.CANCELLED, TaskState.COMPLETE, TaskState.ROLLED_BACK})
        == TERMINAL_STATES
    )


def test_truly_terminal_states_have_no_outgoing_transitions() -> None:
    # CANCELLED and ROLLED_BACK are sinks; COMPLETE legally goes only to ROLLED_BACK.
    policy = TransitionPolicy()
    for sink in (TaskState.CANCELLED, TaskState.ROLLED_BACK):
        for new in TaskState:
            assert not policy.is_legal(sink, new)
